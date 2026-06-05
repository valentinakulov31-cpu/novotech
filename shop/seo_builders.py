from __future__ import annotations

from itertools import chain

from shop.models import City, Group, Product
from shop.seo_common import (
    city_prepositional_phrase,
    dedupe_keywords,
    first_non_empty,
    render_template,
    split_synonyms,
    truncate,
)


def product_default_title(product: Product, city: City | None = None) -> str:
    bits = [product.name]
    city_phrase = city_prepositional_phrase(city)
    if city_phrase:
        bits.append(f"РєСѓРїРёС‚СЊ {city_phrase}")
    if product.brand:
        bits.append(product.brand.name)
    if product.group:
        bits.append(product.group.name)
    return truncate(" | ".join(dedupe_keywords(bits)), 255)


def group_default_title(group: Group, city: City | None = None) -> str:
    city_phrase = city_prepositional_phrase(city)
    bits = [group.name]
    if city_phrase:
        bits.append(f"РєСѓРїРёС‚СЊ {city_phrase}")
    bits.append("РєР°С‚Р°Р»РѕРі")
    if group.parent:
        bits.append(group.parent.name)
    return truncate(" | ".join(dedupe_keywords(bits)), 255)


def product_default_description(product: Product, city: City | None = None) -> str:
    city_phrase = city_prepositional_phrase(city)
    source = first_non_empty(
        product.seo_description,
        product.description,
        (
            f"{product.name} {city_phrase}. РўРµС…РЅРёС‡РµСЃРєРёРµ С…Р°СЂР°РєС‚РµСЂРёСЃС‚РёРєРё, С„РѕС‚Рѕ, РґРѕРєСѓРјРµРЅС‚С‹ Рё СЃРµСЂС‚РёС„РёРєР°С‚С‹ С‚РѕРІР°СЂР°."
            if city_phrase
            else f"{product.name}. РўРµС…РЅРёС‡РµСЃРєРёРµ С…Р°СЂР°РєС‚РµСЂРёСЃС‚РёРєРё, С„РѕС‚Рѕ, РґРѕРєСѓРјРµРЅС‚С‹ Рё СЃРµСЂС‚РёС„РёРєР°С‚С‹ С‚РѕРІР°СЂР°."
        ),
    )
    return truncate(source, 320)


def group_default_description(group: Group, city: City | None = None) -> str:
    city_phrase = city_prepositional_phrase(city)
    source = first_non_empty(
        group.seo_description,
        group.description,
        (
            f"РљР°С‚РµРіРѕСЂРёСЏ {group.name} {city_phrase}. РўРѕРІР°СЂС‹, С…Р°СЂР°РєС‚РµСЂРёСЃС‚РёРєРё, РґРѕРєСѓРјРµРЅС‚С‹ Рё РґРѕСЃС‚СѓРїРЅС‹Рµ Р±СЂРµРЅРґС‹."
            if city_phrase
            else f"РљР°С‚РµРіРѕСЂРёСЏ {group.name}. РўРѕРІР°СЂС‹, С…Р°СЂР°РєС‚РµСЂРёСЃС‚РёРєРё, РґРѕРєСѓРјРµРЅС‚С‹ Рё РґРѕСЃС‚СѓРїРЅС‹Рµ Р±СЂРµРЅРґС‹."
        ),
    )
    return truncate(source, 320)


def product_default_keywords(product: Product) -> str:
    values = dedupe_keywords(
        chain(
            [product.name, product.sku],
            [product.brand.name] if product.brand else [],
            [product.group.name] if product.group else [],
            split_synonyms(product.search_tsv),
        )
    )
    return ", ".join(values[:20])


def group_default_keywords(group: Group, city: City | None = None) -> str:
    values = dedupe_keywords(
        chain(
            [group.name, group.slug],
            [city.name] if city else [],
            [group.parent.name] if group.parent else [],
        )
    )
    return ", ".join(values[:20])


def product_og_image(product: Product) -> str | None:
    if isinstance(product.media, list):
        first = next((item for item in product.media if isinstance(item, str) and item.strip()), None)
        if first:
            return first
    primary = next((item for item in product.media_files.all() if item.url), None)
    if primary:
        return primary.url
    return None


def group_context(group: Group, city: City | None = None) -> dict:
    return {
        "name": group.name,
        "slug": group.slug,
        "parent": group.parent.name if group.parent else "",
        "city": city.name if city else "",
        "city_slug": city.slug if city else "",
        "city_prep": city_prepositional_phrase(city) or "",
    }


def product_context(product: Product, city: City | None = None) -> dict:
    return {
        "id": product.id,
        "slug": product.slug,
        "name": product.name,
        "sku": product.sku,
        "brand": product.brand.name if product.brand else "",
        "brand_slug": product.brand.slug if product.brand else "",
        "group": product.group.name if product.group else "",
        "group_slug": product.group.slug if product.group else "",
        "city": city.name if city else "",
        "city_slug": city.slug if city else "",
        "city_prep": city_prepositional_phrase(city) or "",
    }


def build_group_seo(group: Group, city: City | None = None) -> dict:
    city_phrase = city_prepositional_phrase(city)
    context = group_context(group, city)
    title = first_non_empty(render_template(group.seo_title, context), group_default_title(group, city))
    description = first_non_empty(
        render_template(group.seo_description, context),
        group_default_description(group, city),
    )
    h1 = first_non_empty(
        render_template(group.seo_h1, context),
        f"{group.name} {city_phrase}" if city_phrase else group.name,
    )
    keywords = first_non_empty(render_template(group.seo_keywords, context), group_default_keywords(group, city))
    default_canonical = f"/groups/{group.slug}"
    canonical_url = first_non_empty(render_template(group.seo_canonical_url, context), default_canonical)
    robots = first_non_empty(render_template(group.seo_robots, context), "index,follow")
    og_image = first_non_empty(group.media)
    return {
        "title": title,
        "h1": h1,
        "description": description,
        "keywords": keywords,
        "canonical_url": canonical_url,
        "robots": robots,
        "og_title": title,
        "og_description": description,
        "og_image": og_image or None,
        "city": city.slug if city else None,
    }


def build_product_seo(product: Product, city: City | None = None) -> dict:
    city_phrase = city_prepositional_phrase(city)
    context = product_context(product, city)
    title = first_non_empty(render_template(product.seo_title, context), product_default_title(product, city))
    description = first_non_empty(
        render_template(product.seo_description, context),
        product_default_description(product, city),
    )
    h1 = first_non_empty(
        render_template(product.seo_h1, context),
        f"{product.name} {city_phrase}" if city_phrase else product.name,
    )
    keywords = first_non_empty(render_template(product.seo_keywords, context), product_default_keywords(product))
    default_canonical = f"/products/{product.slug or product.id}"
    canonical_url = first_non_empty(render_template(product.seo_canonical_url, context), default_canonical)
    robots = first_non_empty(render_template(product.seo_robots, context), "index,follow")
    og_image = product_og_image(product)
    return {
        "title": title,
        "h1": h1,
        "description": description,
        "keywords": keywords,
        "canonical_url": canonical_url,
        "robots": robots,
        "og_title": title,
        "og_description": description,
        "og_image": og_image,
        "city": city.slug if city else None,
    }
