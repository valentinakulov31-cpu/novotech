from django.apps import AppConfig


class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shop'

    def ready(self):
        from django.db.models.signals import post_delete, post_save
        from shop.catalog_cache import catalog_changed
        from shop.models import Brand, Product

        for model in (Brand, Product):
            for name, event in (("save", post_save), ("delete", post_delete)):
                event.connect(catalog_changed, sender=model, dispatch_uid=f"catalog-cache-{model.__name__}-{name}")
