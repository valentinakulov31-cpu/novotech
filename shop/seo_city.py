from __future__ import annotations

from shop.models import City


def resolve_city(city_slug: str | None = None, city_id: int | None = None) -> City | None:
    queryset = City.objects.filter(is_active=True)
    if city_id:
        city = queryset.filter(id=city_id).first()
        if city:
            return city
    if city_slug:
        return queryset.filter(slug=city_slug).first()
    return None
