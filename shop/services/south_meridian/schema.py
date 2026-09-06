from dataclasses import dataclass, field
from hashlib import sha256

from shop.model_slug_utils import transliterate_slug


BASE_URL = "https://south-meridian.ru/"
CATEGORIES = {
    "chugunnie-trubi": "Трубы из высокопрочного чугуна",
    "fitingi": "Фитинги для чугунных труб",
    "nasosi": "Насосы",
    "zaporno-regulirujuschaja-armatura": "Запорно-регулирующая арматура",
    "oborudovanie": "Прочее оборудование",
}


@dataclass
class Asset:
    url: str
    kind: str
    title: str = ""


@dataclass
class SourceProduct:
    source_url: str
    source_key: str
    name: str
    category: str
    description: str
    characteristics_html: str
    characteristics: dict[str, str] = field(default_factory=dict)
    assets: list[Asset] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def sku(self):
        # Stable numeric identifiers make repeated imports update, not duplicate, rows.
        digest = sha256(f"{self.source_url}#{self.source_key}".encode()).hexdigest()
        return str(100_000_000_000 + int(digest[:16], 16) % 900_000_000_000)

    @property
    def slug(self):
        return f"{transliterate_slug(self.name)[:210]}-{self.sku}"


@dataclass
class Catalogue:
    products: list[SourceProduct] = field(default_factory=list)
    pages: list[dict] = field(default_factory=list)
    categories: list[dict] = field(default_factory=list)
    documents: list[dict] = field(default_factory=list)
    media_checks: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)

    def validate(self):
        if not self.products:
            raise ValueError("Источник не вернул ни одного товара")
        seen = set()
        for product in self.products:
            if product.sku in seen:
                raise ValueError(f"Повтор идентификатора: {product.source_url} / {product.source_key}")
            seen.add(product.sku)
            if not product.name or len(product.name) > 255:
                raise ValueError(f"Некорректное название товара: {product.source_url}")
        missing = set(CATEGORIES.values()) - {p.category for p in self.products}
        if missing:
            raise ValueError(f"Не собраны категории: {', '.join(sorted(missing))}")
