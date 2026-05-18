from django.db import migrations, models


def seed_brand_transliterations(apps, schema_editor):
    Brand = apps.get_model("shop", "Brand")

    cyrillic_to_latin = {
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

    for brand in Brand.objects.all():
        synonyms = brand.search_synonyms or []
        if not isinstance(synonyms, list):
            synonyms = []
        transliterated = "".join(cyrillic_to_latin.get(char, char) for char in str(brand.name or "").lower())
        transliterated = " ".join(transliterated.replace("-", " ").split())
        if transliterated and transliterated != str(brand.name or "").strip().lower():
            synonyms.append(transliterated)
        normalized = []
        seen = set()
        for item in synonyms:
            text = str(item or "").strip()
            if not text or text.lower() in seen:
                continue
            seen.add(text.lower())
            normalized.append(text)
        brand.search_synonyms = normalized
        brand.save(update_fields=["search_synonyms"])


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0025_slider_slug_optional"),
    ]

    operations = [
        migrations.AlterField(
            model_name="brand",
            name="slug",
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="brand",
            name="search_synonyms",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="group",
            name="search_synonyms",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="orderemailsettings",
            name="body_html",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="characteristic",
            name="data_type",
            field=models.CharField(
                choices=[("text", "Text"), ("number", "Number"), ("boolean", "Boolean")],
                default="text",
                max_length=50,
            ),
        ),
        migrations.DeleteModel(
            name="ProductDocument",
        ),
        migrations.RunPython(seed_brand_transliterations, migrations.RunPython.noop),
    ]
