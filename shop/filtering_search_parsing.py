from decimal import Decimal, InvalidOperation

from shop.model_utils import normalize_search_token, transliterate_slug


def parse_bool(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y", "РґР°"}:
        return True
    if normalized in {"false", "0", "no", "n", "РЅРµС‚"}:
        return False
    return None


def parse_decimal(value):
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).strip().replace(" ", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def tokenize_query(query):
    tokens = []
    seen = set()
    for variants in tokenize_query_groups(query):
        for variant in variants:
            key = variant.lower()
            if key in seen:
                continue
            seen.add(key)
            tokens.append(variant)
    return tokens


def tokenize_query_groups(query):
    tokens = []
    for token in str(query or "").split():
        token = token.strip()
        if not token:
            continue
        variants = [token]
        transliterated = transliterate_slug(token).replace("-", " ").strip()
        if transliterated:
            variants.extend(part for part in transliterated.split() if part)
        normalized_token = normalize_search_token(token)
        if normalized_token:
            variants.append(normalized_token)
        group = []
        seen = set()
        for variant in variants:
            key = variant.lower()
            if key in seen:
                continue
            seen.add(key)
            group.append(variant)
        if group:
            tokens.append(group)
    return tokens
