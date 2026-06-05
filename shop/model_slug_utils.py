import re
import uuid


CYRILLIC_TO_LATIN = {
    "Р В°": "a",
    "Р В±": "b",
    "Р Р†": "v",
    "Р С–": "g",
    "Р Т‘": "d",
    "Р Вµ": "e",
    "РЎвЂ": "e",
    "Р В¶": "zh",
    "Р В·": "z",
    "Р С‘": "i",
    "Р в„–": "y",
    "Р С”": "k",
    "Р В»": "l",
    "Р С": "m",
    "Р Р…": "n",
    "Р С•": "o",
    "Р С—": "p",
    "РЎР‚": "r",
    "РЎРѓ": "s",
    "РЎвЂљ": "t",
    "РЎС“": "u",
    "РЎвЂћ": "f",
    "РЎвЂ¦": "h",
    "РЎвЂ ": "ts",
    "РЎвЂЎ": "ch",
    "РЎв‚¬": "sh",
    "РЎвЂ°": "sch",
    "РЎР‰": "",
    "РЎвЂ№": "y",
    "РЎРЉ": "",
    "РЎРЊ": "e",
    "РЎР‹": "yu",
    "РЎРЏ": "ya",
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
