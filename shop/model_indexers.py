from shop.model_search_utils import build_search_index, normalize_synonyms
from shop.model_slug_utils import transliterate_slug


def prepare_brand_search_fields(brand):
    synonyms = normalize_synonyms(brand.search_synonyms)
    transliterated = transliterate_slug(brand.name).replace("-", " ")
    if transliterated and transliterated.lower() != str(brand.name or "").strip().lower():
        synonyms = normalize_synonyms([*synonyms, transliterated, *transliterated.split()])
    search_index = build_search_index(brand.name, brand.slug, synonyms)
    return synonyms, search_index


def prepare_group_search_fields(group):
    synonyms = normalize_synonyms(group.search_synonyms)
    search_index = build_search_index(group.name, group.slug, group.description, synonyms)
    return synonyms, search_index


def collect_product_characteristic_search_values(product):
    if not product.pk:
        return []
    return list(
        product.characteristics.select_related("characteristic").values_list(
            "value",
            "characteristic__name",
            "characteristic__slug",
        )
    )


def prepare_product_search_index(product):
    characteristic_values = collect_product_characteristic_search_values(product)
    return build_search_index(
        product.sku,
        product.slug,
        product.name,
        product.description,
        product.characteristics_html,
        product.search_tsv,
        product.brand.name if product.brand else "",
        product.brand.slug if product.brand else "",
        product.brand.search_synonyms if product.brand else [],
        product.group.name if product.group else "",
        product.group.slug if product.group else "",
        product.group.search_synonyms if product.group else [],
        characteristic_values,
    )


def refresh_product_search_index(product):
    product.save(update_fields=["search_index"])


def prepare_characteristic_search_index(characteristic):
    return build_search_index(
        characteristic.name,
        characteristic.slug,
        characteristic.unit,
        characteristic.group.name if characteristic.group else "",
        characteristic.group.slug if characteristic.group else "",
    )
