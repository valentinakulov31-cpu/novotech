import shutil
import tempfile
from decimal import Decimal

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from shop.models import (
    Brand,
    Characteristic,
    Group,
    Product,
    ProductCertificate,
    ProductCharacteristic,
    ProductGalleryItem,
    ProductMedia,
)


class CatalogApiFixtureBase(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()
        self.client = APIClient()

        self.group = Group.objects.create(name="Р СћР ВµР С—Р В»Р С•Р С‘Р В·Р С•Р В»РЎРЏРЎвЂ Р С‘РЎРЏ", slug="teploizolyatsiya")
        self.other_group = Group.objects.create(name="Р С›Р С–Р Р…Р ВµР В·Р В°РЎвЂ°Р С‘РЎвЂљР В°", slug="ognezashita")
        self.brand = Brand.objects.create(name="ENERGOROLL", slug="energoroll")
        self.other_brand = Brand.objects.create(name="OBM", slug="obm")

        self.char_thickness = Characteristic.objects.create(
            group=self.group,
            name="Р СћР С•Р В»РЎвЂ°Р С‘Р Р…Р В° Р С•РЎвЂљ, Р СР С",
            slug="tolschina-ot-mm",
            data_type="number",
            is_filterable=True,
        )
        self.char_cover = Characteristic.objects.create(
            group=self.group,
            name="Р СџР С•Р С”РЎР‚РЎвЂ№РЎвЂљР С‘Р Вµ",
            slug="pokrytie",
            data_type="text",
            is_filterable=True,
        )

        self.product = Product.objects.create(
            sku="ER-0001",
            name="Р В¦Р С‘Р В»Р С‘Р Р…Р Т‘РЎР‚РЎвЂ№ ENERGOROLL RK",
            price=Decimal("100.00"),
            currency="RUB",
            description="Р СћР ВµР С—Р В»Р С•Р С‘Р В·Р С•Р В»РЎРЏРЎвЂ Р С‘РЎРЏ Р С‘Р В· Р СР С‘Р Р…Р ВµРЎР‚Р В°Р В»РЎРЉР Р…Р С•Р в„– Р Р†Р В°РЎвЂљРЎвЂ№",
            assortment_html="<p><strong>Р С’РЎРѓРЎРѓР С•РЎР‚РЎвЂљР С‘Р СР ВµР Р…РЎвЂљ:</strong> РЎвЂ Р С‘Р В»Р С‘Р Р…Р Т‘РЎР‚РЎвЂ№, Р СР В°РЎвЂљРЎвЂ№</p>",
            group=self.group,
            brand=self.brand,
            available=True,
        )
        self.product.characteristics_html = "<div><h3>Р ТђР В°РЎР‚Р В°Р С”РЎвЂљР ВµРЎР‚Р С‘РЎРѓРЎвЂљР С‘Р С”Р С‘</h3><p>Р СћР С•Р В»РЎвЂ°Р С‘Р Р…Р В°, Р С—Р С•Р С”РЎР‚РЎвЂ№РЎвЂљР С‘Р Вµ</p></div>"
        self.product.save(update_fields=["characteristics_html"])

        self.other_product = Product.objects.create(
            sku="OB-0001",
            name="Р С›Р С–Р Р…Р ВµР В·Р В°РЎвЂ°Р С‘РЎвЂљР Р…РЎвЂ№Р в„– Р СР В°РЎвЂљР ВµРЎР‚Р С‘Р В°Р В» Р С›Р вЂР Сљ",
            price=Decimal("250.00"),
            currency="RUB",
            description="Р С›Р С–Р Р…Р ВµР В·Р В°РЎвЂ°Р С‘РЎвЂљР Р…РЎвЂ№Р в„– Р В±Р В°Р В·Р В°Р В»РЎРЉРЎвЂљР С•Р Р†РЎвЂ№Р в„– Р СР В°РЎвЂљР ВµРЎР‚Р С‘Р В°Р В»",
            group=self.other_group,
            brand=self.other_brand,
            available=True,
        )

        ProductCharacteristic.objects.create(product=self.product, characteristic=self.char_thickness, value="20")
        ProductCharacteristic.objects.create(product=self.product, characteristic=self.char_cover, value="Р В¤Р С•Р В»РЎРЉР С–Р В°")

        ProductMedia.objects.create(
            product=self.product,
            storage_path="media/a.jpg",
            url="/static/a.jpg",
            mime_type="image/jpeg",
            media_kind="image",
            size_bytes=10,
            is_primary=False,
            sort_order=2,
        )
        ProductMedia.objects.create(
            product=self.product,
            storage_path="media/b.jpg",
            url="/static/b.jpg",
            mime_type="image/jpeg",
            media_kind="image",
            size_bytes=10,
            is_primary=True,
            sort_order=5,
        )
        ProductGalleryItem.objects.create(
            product=self.product,
            title="Р вЂ™Р С‘Р Т‘Р ВµР С• Р С•Р В±Р В·Р С•РЎР‚",
            storage_path="media/video.mp4",
            url="/static/video.mp4",
            mime_type="video/mp4",
            file_kind="video",
            size_bytes=200,
            sort_order=1,
        )
        ProductGalleryItem.objects.create(
            product=self.product,
            title="Р В¤Р С•РЎвЂљР С• Р Р† Р С‘Р Р…РЎвЂљР ВµРЎР‚РЎРЉР ВµРЎР‚Р Вµ",
            storage_path="media/gallery.jpg",
            url="/static/gallery.jpg",
            mime_type="image/jpeg",
            file_kind="image",
            size_bytes=50,
            sort_order=2,
        )
        ProductCertificate.objects.create(
            product=self.product,
            title="Р РЋР ВµРЎР‚РЎвЂљР С‘РЎвЂћР С‘Р С”Р В°РЎвЂљ РЎРѓР С•Р С•РЎвЂљР Р†Р ВµРЎвЂљРЎРѓРЎвЂљР Р†Р С‘РЎРЏ",
            storage_path="media/certificate.pdf",
            url="/static/certificate.pdf",
            mime_type="application/pdf",
            size_bytes=95,
            sort_order=1,
        )

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)
