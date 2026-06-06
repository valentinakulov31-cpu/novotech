from django.contrib import admin


ADMIN_SECTION_ORDER = [
    (
        "catalog",
        "Каталог",
        [
            "shop.Product",
            "shop.Group",
            "shop.Brand",
            "shop.Characteristic",
            "shop.ProductCharacteristic",
        ],
    ),
    (
        "media",
        "Медиа и файлы",
        [
            "shop.MediaLibrary",
            "shop.SharedProductGallery",
            "shop.ProductMedia",
            "shop.ProductGalleryItem",
            "shop.ProductCertificate",
            "shop.Sert",
            "shop.NewsAttachment",
        ],
    ),
    (
        "content",
        "Контент сайта",
        [
            "shop.Slider",
            "shop.News",
            "shop.HtmlContent",
            "shop.ContactInfo",
            "shop.Agent",
            "shop.City",
        ],
    ),
    (
        "orders",
        "Заявки и заказы",
        [
            "shop.Inquiry",
            "shop.PublicOrder",
        ],
    ),
    (
        "settings",
        "Настройки и доступ",
        [
            "shop.OrderEmailSettings",
            "shop.OrderEmailRecipient",
            "auth.User",
            "auth.Group",
        ],
    ),
]

ADMIN_MODEL_NAMES = {
    "shop.Product": "Товары",
    "shop.Group": "Категории",
    "shop.Brand": "Бренды",
    "shop.Characteristic": "Характеристики",
    "shop.ProductCharacteristic": "Значения характеристик",
    "shop.MediaLibrary": "Библиотека медиа",
    "shop.SharedProductGallery": "Общие галереи",
    "shop.ProductMedia": "Превью товаров",
    "shop.ProductGalleryItem": "Галерея товаров",
    "shop.ProductCertificate": "Сертификаты товаров",
    "shop.Sert": "Общие сертификаты",
    "shop.NewsAttachment": "Файлы новостей",
    "shop.Slider": "Слайды",
    "shop.News": "Новости",
    "shop.HtmlContent": "Реквизиты компании",
    "shop.ContactInfo": "Контактная информация",
    "shop.Agent": "Менеджеры",
    "shop.City": "SEO-города",
    "shop.Inquiry": "Заявки",
    "shop.PublicOrder": "Заказы",
    "shop.OrderEmailSettings": "Шаблоны писем",
    "shop.OrderEmailRecipient": "Получатели писем",
    "auth.User": "Пользователи",
    "auth.Group": "Группы прав",
}


def grouped_admin_app_list(request, app_label=None):
    app_dict = admin.site._build_app_dict(request, app_label)
    model_map = {}
    for current_app_label, app in app_dict.items():
        for model in app.get("models", []):
            key = f"{current_app_label}.{model['object_name']}"
            model = model.copy()
            model["name"] = ADMIN_MODEL_NAMES.get(key, model["name"])
            model_map[key] = model

    grouped_apps = []
    used_keys = set()
    for section_label, section_name, model_keys in ADMIN_SECTION_ORDER:
        models = [model_map[key] for key in model_keys if key in model_map]
        if not models:
            continue
        used_keys.update(key for key in model_keys if key in model_map)
        grouped_apps.append(
            {
                "name": section_name,
                "app_label": section_label,
                "app_url": "",
                "has_module_perms": True,
                "models": models,
            }
        )

    fallback_models = [model for key, model in sorted(model_map.items()) if key not in used_keys]
    if fallback_models:
        grouped_apps.append(
            {
                "name": "Прочее",
                "app_label": "other",
                "app_url": "",
                "has_module_perms": True,
                "models": fallback_models,
            }
        )

    return grouped_apps


def configure_admin_site():
    admin.site.site_header = "Новатех админка"
    admin.site.site_title = "Новатех админка"
    admin.site.index_title = "Управление сайтом"
    admin.site.get_app_list = grouped_admin_app_list
