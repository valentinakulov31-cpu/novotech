from difflib import SequenceMatcher

from django.db.models import Case, FloatField, IntegerField, Q, Value, When
from django.db.models.functions import Cast

from shop.filtering_search_parsing import tokenize_query_groups
from shop.model_utils import normalize_search_token


SEARCH_FUZZY_THRESHOLD = 0.18
PYTHON_FUZZY_RATIO_THRESHOLD = 0.78


def _is_ignorable_variant(value):
    normalized = normalize_search_token(value)
    return len(normalized) < 2 and normalized.isalpha()


def any_field_matches(token, fields):
    if _is_ignorable_variant(token):
        return Q()
    token_query = Q()
    for field in fields:
        token_query |= Q(**{f"{field}__icontains": token})
    return token_query


def token_match_query(tokens, fields, require_all=True):
    if not tokens:
        return Q()
    queries = [any_field_matches(token, fields) for token in tokens]
    if require_all:
        query = Q()
        for token_query in queries:
            query &= token_query
        return query
    query = Q()
    for token_query in queries:
        query |= token_query
    return query


def token_group_match_query(token_groups, fields, require_all=True):
    if not token_groups:
        return Q()
    queries = []
    for variants in token_groups:
        group_query = Q()
        for token in variants:
            if _is_ignorable_variant(token):
                continue
            group_query |= any_field_matches(token, fields)
        if not group_query:
            continue
        queries.append(group_query)
    query = Q()
    for group_query in queries:
        if require_all:
            query &= group_query
        else:
            query |= group_query
    return query


def score_expression(tokens, fields):
    score = Value(0, output_field=IntegerField())
    for token in tokens:
        token_query = any_field_matches(token, fields)
        score += Case(
            When(token_query, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    return score


def score_group_expression(token_groups, fields):
    score = Value(0, output_field=IntegerField())
    for variants in token_groups:
        group_query = Q()
        for token in variants:
            if _is_ignorable_variant(token):
                continue
            group_query |= any_field_matches(token, fields)
        if not group_query:
            continue
        score += Case(
            When(group_query, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    return score


def _search_text_from_values(values):
    parts = []
    for value in values:
        if value in (None, ""):
            continue
        parts.append(str(value))
    return " ".join(parts)


def _tokenize_search_words(value):
    words = []
    seen = set()
    for raw_word in str(value or "").split():
        word = normalize_search_token(raw_word)
        if len(word) < 3 or word in seen:
            continue
        seen.add(word)
        words.append(word)
    return words


def _word_matches_variant(word, variant):
    if not word or not variant:
        return False
    if word == variant:
        return True
    if len(word) >= 4 and len(variant) >= 4:
        if word in variant or variant in word:
            return True
    if len(word) >= 5 and len(variant) >= 5:
        if word[0] != variant[0] or word[-1] != variant[-1]:
            return False
        return SequenceMatcher(None, word, variant).ratio() >= PYTHON_FUZZY_RATIO_THRESHOLD
    return False


def _fuzzy_group_score(candidate_words, variants):
    best_score = 0.0
    for variant in variants:
        if _is_ignorable_variant(variant):
            continue
        normalized_variant = normalize_search_token(variant)
        if not normalized_variant:
            continue
        for word in candidate_words:
            if not _word_matches_variant(word, normalized_variant):
                continue
            score = 1.0 if word == normalized_variant else SequenceMatcher(None, word, normalized_variant).ratio()
            if score > best_score:
                best_score = score
    return best_score


def _python_fuzzy_match_queryset(queryset, token_groups, fuzzy_fields, require_all_tokens):
    matches = []
    for row in queryset.values("id", *fuzzy_fields):
        candidate_text = _search_text_from_values(row.get(field_name) for field_name in fuzzy_fields)
        candidate_words = _tokenize_search_words(candidate_text)
        if not candidate_words:
            continue

        group_scores = []
        for variants in token_groups:
            score = _fuzzy_group_score(candidate_words, variants)
            if score <= 0:
                if require_all_tokens:
                    group_scores = []
                    break
                continue
            group_scores.append(score)

        if not group_scores:
            continue

        if require_all_tokens and len(group_scores) != len(token_groups):
            continue

        similarity = sum(group_scores) / len(group_scores)
        matches.append((row["id"], float(len(group_scores)), similarity))

    return matches


def apply_ranked_search(queryset, query, exact_fields, fuzzy_fields=None, require_all_tokens=True, threshold=SEARCH_FUZZY_THRESHOLD):
    query = (query or "").strip()
    token_groups = tokenize_query_groups(query)
    if not token_groups:
        return queryset

    queryset = queryset.annotate(
        search_exact_score=score_group_expression(token_groups, exact_fields),
        search_similarity=Value(0.0, output_field=FloatField()),
    ).annotate(
        search_rank=Cast("search_exact_score", FloatField())
    )
    exact_query = token_group_match_query(token_groups, exact_fields, require_all=require_all_tokens)
    exact_queryset = queryset.filter(exact_query).distinct()
    if exact_queryset.exists() or not fuzzy_fields:
        return exact_queryset

    fuzzy_matches = _python_fuzzy_match_queryset(queryset, token_groups, fuzzy_fields, require_all_tokens)
    if not fuzzy_matches:
        return exact_queryset

    rank_case = Case(
        *[When(id=item_id, then=Value(score)) for item_id, score, _ in fuzzy_matches],
        default=Value(0.0),
        output_field=FloatField(),
    )
    similarity_case = Case(
        *[When(id=item_id, then=Value(similarity)) for item_id, _, similarity in fuzzy_matches],
        default=Value(0.0),
        output_field=FloatField(),
    )

    fuzzy_ids = [item_id for item_id, _, _ in fuzzy_matches]
    return queryset.filter(id__in=fuzzy_ids).annotate(
        search_exact_score=Value(0, output_field=IntegerField()),
        search_rank=rank_case,
        search_similarity=similarity_case,
    ).distinct()
