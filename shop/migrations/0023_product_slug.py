from django.db import migrations, models
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


def transliterate_slug(value):
    normalized = str(value or "").strip().lower()
    transliterated = "".join(CYRILLIC_TO_LATIN.get(char, char) for char in normalized)
    transliterated = transliterated.replace("&", " and ")
    transliterated = re.sub(r"[^a-z0-9]+", "-", transliterated)
    transliterated = re.sub(r"-{2,}", "-", transliterated).strip("-")
    return transliterated or f"item-{uuid.uuid4().hex[:8]}"


def populate_product_slugs(apps, schema_editor):
    Product = apps.get_model("shop", "Product")
    used_slugs = set()
    for product in Product.objects.order_by("id"):
        base_slug = transliterate_slug(product.name or product.sku)[:220].strip("-")
        slug = base_slug or f"product-{product.pk}"
        index = 2
        while slug in used_slugs or Product.objects.filter(slug=slug).exclude(pk=product.pk).exists():
            suffix = f"-{index}"
            slug = f"{base_slug[:255 - len(suffix)]}{suffix}" if base_slug else f"product-{product.pk}-{index}"
            index += 1
        product.slug = slug
        product.save(update_fields=["slug"])
        used_slugs.add(slug)


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0022_agent'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='slug',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.RunPython(populate_product_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='product',
            name='slug',
            field=models.CharField(blank=True, max_length=255, unique=True),
        ),
    ]
