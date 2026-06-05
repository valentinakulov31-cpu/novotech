from __future__ import annotations

from shop.models import City


class SeoTemplateContext(dict):
    def __missing__(self, key):
        return ""


def first_non_empty(*values):
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def truncate(text: str, limit: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "вЂ¦"


def split_synonyms(value: str | None) -> list[str]:
    if not value:
        return []
    normalized = str(value).replace(";", ",").replace("\n", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def city_prepositional_phrase(city: City | None) -> str | None:
    if not city:
        return None
    city_name = first_non_empty(city.name_in_prepositional, city.name)
    if not city_name:
        return None
    return f"РІ {city_name}"


def dedupe_keywords(values):
    seen = set()
    result = []
    for raw in values:
        value = str(raw or "").strip()
        if not value:
            continue
        lowered = value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(value)
    return result


def render_template(value: str | None, context: dict | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    normalized_context = SeoTemplateContext(
        {key: "" if raw is None else str(raw) for key, raw in (context or {}).items()}
    )
    rendered = text.format_map(normalized_context)
    return " ".join(rendered.split()).strip()
