from __future__ import annotations

from itertools import chain

from shop.models import City, Group, Product


class _SeoTemplateContext(dict):
    def __missing__(self, key):
        return ""


def _first_non_empty(*values):
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _truncate(text: str, limit: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _split_synonyms(value: str | None) -> list[str]:
    if not value:
        return []
    normalized = str(value).replace(";", ",").replace("\n", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def resolve_city(city_slug: str | None = None, city_id: int | None = None) -> City | None:
    queryset = City.objects.filter(is_active=True)
    if city_id:
        city = queryset.filter(id=city_id).first()
        if city:
            return city
    if city_slug:
        return queryset.filter(slug=city_slug).first()
    return None


def city_prepositional_phrase(city: City | None) -> str | None:
    if not city:
        return None
    city_name = _first_non_empty(city.name_in_prepositional, city.name)
    if not city_name:
        return None
    return f"в {city_name}"


def _dedupe_keywords(values):
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


def _render_template(value: str | None, context: dict | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    normalized_context = _SeoTemplateContext(
        {key: "" if raw is None else str(raw) for key, raw in (context or {}).items()}
    )
    rendered = text.format_map(normalized_context)
    return " ".join(rendered.split()).strip()


def _product_default_title(product: Product, city: City | None = None) -> str:
    bits = [product.name]
    city_phrase = city_prepositional_phrase(city)
    if city_phrase:
        bits.append(f"купить {city_phrase}")
    if product.brand:
        bits.append(product.brand.name)
    if product.group:
        bits.append(product.group.name)
    return _truncate(" | ".join(_dedupe_keywords(bits)), 255)


def _group_default_title(group: Group, city: City | None = None) -> str:
    city_phrase = city_prepositional_phrase(city)
    bits = [group.name]
    if city_phrase:
        bits.append(f"купить {city_phrase}")
    bits.append("каталог")
    if group.parent:
        bits.append(group.parent.name)
    return _truncate(" | ".join(_dedupe_keywords(bits)), 255)


def _product_default_description(product: Product, city: City | None = None) -> str:
    city_phrase = city_prepositional_phrase(city)
    source = _first_non_empty(
        product.seo_description,
        product.description,
        (
            f"{product.name} {city_phrase}. Технические характеристики, фото, документы и сертификаты товара."
            if city_phrase
            else f"{product.name}. Технические характеристики, фото, документы и сертификаты товара."
        ),
    )
    return _truncate(source, 320)


def _group_default_description(group: Group, city: City | None = None) -> str:
    city_phrase = city_prepositional_phrase(city)
    source = _first_non_empty(
        group.seo_description,
        group.description,
        (
            f"Категория {group.name} {city_phrase}. Товары, характеристики, документы и доступные бренды."
            if city_phrase
            else f"Категория {group.name}. Товары, характеристики, документы и доступные бренды."
        ),
    )
    return _truncate(source, 320)


def _product_default_keywords(product: Product) -> str:
    values = _dedupe_keywords(
        chain(
            [product.name, product.sku],
            [product.brand.name] if product.brand else [],
            [product.group.name] if product.group else [],
            _split_synonyms(product.search_tsv),
        )
    )
    return ", ".join(values[:20])


def _group_default_keywords(group: Group, city: City | None = None) -> str:
    values = _dedupe_keywords(
        chain(
            [group.name, group.slug],
            [city.name] if city else [],
            [group.parent.name] if group.parent else [],
        )
    )
    return ", ".join(values[:20])


def _product_og_image(product: Product) -> str | None:
    if isinstance(product.media, list):
        first = next((item for item in product.media if isinstance(item, str) and item.strip()), None)
        if first:
            return first
    primary = next((item for item in product.media_files.all() if item.url), None)
    if primary:
        return primary.url
    return None


def _group_context(group: Group, city: City | None = None) -> dict:
    return {
        "name": group.name,
        "slug": group.slug,
        "parent": group.parent.name if group.parent else "",
        "city": city.name if city else "",
        "city_slug": city.slug if city else "",
        "city_prep": city_prepositional_phrase(city) or "",
    }


def _product_context(product: Product, city: City | None = None) -> dict:
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
    context = _group_context(group, city)
    title = _first_non_empty(_render_template(group.seo_title, context), _group_default_title(group, city))
    description = _first_non_empty(
        _render_template(group.seo_description, context),
        _group_default_description(group, city),
    )
    h1 = _first_non_empty(
        _render_template(group.seo_h1, context),
        f"{group.name} {city_phrase}" if city_phrase else group.name,
    )
    keywords = _first_non_empty(_render_template(group.seo_keywords, context), _group_default_keywords(group, city))
    default_canonical = f"/groups/{group.slug}"
    canonical_url = _first_non_empty(_render_template(group.seo_canonical_url, context), default_canonical)
    robots = _first_non_empty(_render_template(group.seo_robots, context), "index,follow")
    og_image = _first_non_empty(group.media)
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
    context = _product_context(product, city)
    title = _first_non_empty(_render_template(product.seo_title, context), _product_default_title(product, city))
    description = _first_non_empty(
        _render_template(product.seo_description, context),
        _product_default_description(product, city),
    )
    h1 = _first_non_empty(
        _render_template(product.seo_h1, context),
        f"{product.name} {city_phrase}" if city_phrase else product.name,
    )
    keywords = _first_non_empty(_render_template(product.seo_keywords, context), _product_default_keywords(product))
    default_canonical = f"/products/{product.slug or product.id}"
    canonical_url = _first_non_empty(_render_template(product.seo_canonical_url, context), default_canonical)
    robots = _first_non_empty(_render_template(product.seo_robots, context), "index,follow")
    og_image = _product_og_image(product)
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
