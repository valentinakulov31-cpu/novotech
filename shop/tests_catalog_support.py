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

        self.group = Group.objects.create(name="Теплоизоляция", slug="teploizolyatsiya")
        self.other_group = Group.objects.create(name="Огнезащита", slug="ognezashita")
        self.brand = Brand.objects.create(name="ENERGOROLL", slug="energoroll")
        self.other_brand = Brand.objects.create(name="OBM", slug="obm")

        self.char_thickness = Characteristic.objects.create(
            group=self.group,
            name="Толщина от, мм",
            slug="tolschina-ot-mm",
            data_type="number",
            is_filterable=True,
        )
        self.char_cover = Characteristic.objects.create(
            group=self.group,
            name="Покрытие",
            slug="pokrytie",
            data_type="text",
            is_filterable=True,
        )

        self.product = Product.objects.create(
            sku="ER-0001",
            name="Цилиндры ENERGOROLL RK",
            price=Decimal("100.00"),
            currency="RUB",
            description="Теплоизоляция из минеральной ваты",
            assortment_html="<p><strong>Ассортимент:</strong> цилиндры, маты</p>",
            group=self.group,
            brand=self.brand,
            available=True,
        )
        self.product.characteristics_html = "<div><h3>Характеристики</h3><p>Толщина, покрытие</p></div>"
        self.product.save(update_fields=["characteristics_html"])

        self.other_product = Product.objects.create(
            sku="OB-0001",
            name="Огнезащитный материал ОБМ",
            price=Decimal("250.00"),
            currency="RUB",
            description="Огнезащитный базальтовый материал",
            group=self.other_group,
            brand=self.other_brand,
            available=True,
        )

        ProductCharacteristic.objects.create(product=self.product, characteristic=self.char_thickness, value="20")
        ProductCharacteristic.objects.create(product=self.product, characteristic=self.char_cover, value="Фольга")

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
            title="Видео обзор",
            storage_path="media/video.mp4",
            url="/static/video.mp4",
            mime_type="video/mp4",
            file_kind="video",
            size_bytes=200,
            sort_order=1,
        )
        ProductGalleryItem.objects.create(
            product=self.product,
            title="Фото в интерьере",
            storage_path="media/gallery.jpg",
            url="/static/gallery.jpg",
            mime_type="image/jpeg",
            file_kind="image",
            size_bytes=50,
            sort_order=2,
        )
        ProductCertificate.objects.create(
            product=self.product,
            title="Сертификат соответствия",
            storage_path="media/certificate.pdf",
            url="/static/certificate.pdf",
            mime_type="application/pdf",
            size_bytes=95,
            sort_order=1,
        )

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)
