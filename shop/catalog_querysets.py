from django.db import models


class BrandQuerySet(models.QuerySet):
    def visible(self):
        return self.filter(is_hidden=False)


class ProductQuerySet(models.QuerySet):
    def visible(self):
        return self.filter(is_hidden=False).exclude(brand__is_hidden=True)
