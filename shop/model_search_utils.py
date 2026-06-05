import re

from shop.model_slug_utils import transliterate_slug


SEARCH_WORD_RE = re.compile(r"[0-9A-Za-z\u0400-\u04ff]+")
SEARCH_TYPO_TRANSLATION = str.maketrans(
    {
        "\u0451": "\u0435",
        "\u043e": "\u0430",
        "\u044b": "\u0438",
        "\u044d": "\u0435",
        "\u0439": "\u0438",
    }
)


def normalize_search_token(value: str) -> str:
    token = str(value or "").strip().lower()
    token = re.sub(r"[^0-9a-z\u0400-\u04ff]+", "", token)
    return token.translate(SEARCH_TYPO_TRANSLATION)


def normalize_synonyms(value):
    if not value:
        return []
    if isinstance(value, str):
        value = [value]
    result = []
    seen = set()
    for item in value:
        text = str(item or "").strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(text)
    return result


def search_text_parts(*values):
    parts = []
    for value in values:
        if value in (None, ""):
            continue
        if isinstance(value, (list, tuple, set)):
            parts.extend(search_text_parts(*value))
            continue
        text = str(value).strip()
        if not text:
            continue
        parts.append(text)
        transliterated = transliterate_slug(text).replace("-", " ").strip()
        if transliterated and transliterated.lower() != text.lower():
            parts.append(transliterated)
        for word in SEARCH_WORD_RE.findall(text):
            if len(word) < 5:
                continue
            normalized_word = normalize_search_token(word)
            if normalized_word and normalized_word != word.lower():
                parts.append(normalized_word)
    return parts


def build_search_index(*values):
    parts = search_text_parts(*values)
    seen = set()
    result = []
    for part in parts:
        normalized = " ".join(str(part).lower().split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return " ".join(result)
