from django.contrib.sitemaps import Sitemap

from shop.models import Brand, Group, News, Product, PUBLISH_STATUS_PUBLISHED


class StaticPagesSitemap(Sitemap):
    protocol = "https"
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return (
            {"location": "/", "priority": 1.0, "changefreq": "daily"},
            {"location": "/catalog", "priority": 0.9, "changefreq": "daily"},
            {"location": "/about", "priority": 0.6, "changefreq": "monthly"},
            {"location": "/news", "priority": 0.7, "changefreq": "daily"},
            {"location": "/contacts", "priority": 0.8, "changefreq": "monthly"},
            {"location": "/certificates", "priority": 0.6, "changefreq": "weekly"},
            {"location": "/personal-data", "priority": 0.3, "changefreq": "yearly"},
            {"location": "/privacy-policy", "priority": 0.3, "changefreq": "yearly"},
        )

    def location(self, item):
        return item["location"]

    def priority(self, item):
        return item["priority"]

    def changefreq(self, item):
        return item["changefreq"]


class GroupPagesSitemap(Sitemap):
    protocol = "https"
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Group.objects.order_by("name", "id")

    def location(self, obj):
        return f"/group/{obj.slug}"


class ProducerPagesSitemap(Sitemap):
    protocol = "https"
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Brand.objects.order_by("name", "id")

    def location(self, obj):
        return f"/producer/{obj.slug}"


class ProductPagesSitemap(Sitemap):
    protocol = "https"
    changefreq = "weekly"
    priority = 0.8
    limit = 2000

    def items(self):
        return Product.objects.filter(available=True).order_by("name", "id")

    def location(self, obj):
        return f"/product/{obj.slug}"


class NewsPagesSitemap(Sitemap):
    protocol = "https"
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return News.objects.filter(status=PUBLISH_STATUS_PUBLISHED).order_by("-published_at", "-updated_at", "-id")

    def location(self, obj):
        return f"/news/{obj.slug}"

    def lastmod(self, obj):
        return obj.updated_at or obj.published_at


SITEMAPS = {
    "static": StaticPagesSitemap,
    "groups": GroupPagesSitemap,
    "producers": ProducerPagesSitemap,
    "products": ProductPagesSitemap,
    "news": NewsPagesSitemap,
}
