from django.contrib import admin


ADMIN_SECTION_ORDER = [
    (
        "catalog",
        "РљР°С‚Р°Р»РѕРі",
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
        "РњРµРґРёР° Рё С„Р°Р№Р»С‹",
        [
            "shop.MediaLibrary",
            "shop.ProductMedia",
            "shop.ProductGalleryItem",
            "shop.ProductCertificate",
            "shop.Sert",
            "shop.NewsAttachment",
        ],
    ),
    (
        "content",
        "РљРѕРЅС‚РµРЅС‚ СЃР°Р№С‚Р°",
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
        "Р—Р°СЏРІРєРё Рё Р·Р°РєР°Р·С‹",
        [
            "shop.Inquiry",
            "shop.PublicOrder",
        ],
    ),
    (
        "settings",
        "РќР°СЃС‚СЂРѕР№РєРё Рё РґРѕСЃС‚СѓРї",
        [
            "shop.OrderEmailSettings",
            "shop.OrderEmailRecipient",
            "auth.User",
            "auth.Group",
        ],
    ),
]

ADMIN_MODEL_NAMES = {
    "shop.Product": "РўРѕРІР°СЂС‹",
    "shop.Group": "РљР°С‚РµРіРѕСЂРёРё",
    "shop.Brand": "Р‘СЂРµРЅРґС‹",
    "shop.Characteristic": "РҐР°СЂР°РєС‚РµСЂРёСЃС‚РёРєРё",
    "shop.ProductCharacteristic": "Р—РЅР°С‡РµРЅРёСЏ С…Р°СЂР°РєС‚РµСЂРёСЃС‚РёРє",
    "shop.MediaLibrary": "Р‘РёР±Р»РёРѕС‚РµРєР° РјРµРґРёР°",
    "shop.ProductMedia": "РџСЂРµРІСЊСЋ С‚РѕРІР°СЂРѕРІ",
    "shop.ProductGalleryItem": "Р“Р°Р»РµСЂРµСЏ С‚РѕРІР°СЂРѕРІ",
    "shop.ProductCertificate": "РЎРµСЂС‚РёС„РёРєР°С‚С‹ С‚РѕРІР°СЂРѕРІ",
    "shop.Sert": "РћР±С‰РёРµ СЃРµСЂС‚РёС„РёРєР°С‚С‹",
    "shop.NewsAttachment": "Р¤Р°Р№Р»С‹ РЅРѕРІРѕСЃС‚РµР№",
    "shop.Slider": "РЎР»Р°Р№РґРµСЂ",
    "shop.News": "РќРѕРІРѕСЃС‚Рё",
    "shop.HtmlContent": "HTML-Р±Р»РѕРєРё",
    "shop.ContactInfo": "РљРѕРЅС‚Р°РєС‚С‹ РєРѕРјРїР°РЅРёРё",
    "shop.Agent": "РњРµРЅРµРґР¶РµСЂС‹",
    "shop.City": "Р“РѕСЂРѕРґР° РґР»СЏ SEO",
    "shop.Inquiry": "Р—Р°СЏРІРєРё",
    "shop.PublicOrder": "Р—Р°РєР°Р·С‹",
    "shop.OrderEmailSettings": "РЁР°Р±Р»РѕРЅ РїРёСЃСЊРјР°",
    "shop.OrderEmailRecipient": "РџРѕР»СѓС‡Р°С‚РµР»Рё РїРёСЃРµРј",
    "auth.User": "РџРѕР»СЊР·РѕРІР°С‚РµР»Рё",
    "auth.Group": "Р“СЂСѓРїРїС‹ РїСЂР°РІ",
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
                "name": "РџСЂРѕС‡РµРµ",
                "app_label": "other",
                "app_url": "",
                "has_module_perms": True,
                "models": fallback_models,
            }
        )

    return grouped_apps


def configure_admin_site():
    admin.site.site_header = "Novotech admin"
    admin.site.site_title = "Novotech admin"
    admin.site.index_title = "РЈРїСЂР°РІР»РµРЅРёРµ СЃР°Р№С‚РѕРј"
    admin.site.get_app_list = grouped_admin_app_list
