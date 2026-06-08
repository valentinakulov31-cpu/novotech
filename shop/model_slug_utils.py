import re
import uuid


CYRILLIC_TO_LATIN = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def transliterate_slug(value: str) -> str:
    normalized = str(value or "").strip().lower()
    transliterated = "".join(CYRILLIC_TO_LATIN.get(char, char) for char in normalized)
    transliterated = transliterated.replace("&", " and ")
    transliterated = re.sub(r"[^a-z0-9]+", "-", transliterated)
    transliterated = re.sub(r"-{2,}", "-", transliterated).strip("-")
    return transliterated or f"item-{uuid.uuid4().hex[:8]}"


def unique_product_slug(instance, base_value: str) -> str:
    base_slug = transliterate_slug(base_value)[:220].strip("-") or f"product-{uuid.uuid4().hex[:8]}"
    slug = base_slug
    index = 2
    queryset = instance.__class__.objects.filter(slug=slug)
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)
    while queryset.exists():
        suffix = f"-{index}"
        slug = f"{base_slug[:255 - len(suffix)]}{suffix}"
        queryset = instance.__class__.objects.filter(slug=slug)
        if instance.pk:
            queryset = queryset.exclude(pk=instance.pk)
        index += 1
    return slug
