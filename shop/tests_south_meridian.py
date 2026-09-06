from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bs4 import BeautifulSoup
from django.test import SimpleTestCase, TestCase
from openpyxl import load_workbook

from shop.models import Brand, Group, Product, ProductCertificate, ProductCharacteristic, ProductGalleryItem, ProductMedia
from shop.services.catalog_import import import_products_from_workbook
from shop.services.south_meridian.crawler import document_references, product_links
from shop.services.south_meridian.extraction import collect_assets, collect_characteristics, semantic_html
from shop.services.south_meridian.parser import parse_page
from shop.services.south_meridian.schema import Asset, BASE_URL, CATEGORIES, Catalogue, SourceProduct
from shop.services.south_meridian.workbook import product_row, write_workbook


def heading(name):
    return f'<div><h3 class="gdlr-core-title-item-title">{name}</h3></div>'


def photo(name):
    return f'<img src="{BASE_URL}wp-content/uploads/{name}.jpg">'


def page(body):
    return f'<div class="gdlr-core-pbf-sidebar-content-inner">{body}</div><aside>Контакты +79991234567</aside>'


def sample_catalogue():
    return Catalogue(products=[SourceProduct(
        source_url=f'{BASE_URL}product/{key}/', source_key='sample', name=f'Изделие {index}',
        category=category, description='Описание', characteristics_html='<p>PN 16</p>',
        characteristics={'Диаметр': '80 мм'}, assets=[Asset(f'{BASE_URL}wp-content/uploads/{index}.jpg', 'image')],
    ) for index, (key, category) in enumerate(CATEGORIES.items())])


class SouthMeridianParsingTests(SimpleTestCase):
    def test_fittings_include_inactive_tabs_and_match_ids_not_order(self):
        html = page('''<div class="gdlr-core-text-box-item-content"><p>Чугунные фитинги</p></div>
            <div class="gdlr-core-tab-item">
            <div class="gdlr-core-tab-item-title" data-tab-id="1">Отвод</div>
            <div class="gdlr-core-tab-item-title" data-tab-id="2">Тройник</div>
            <div class="gdlr-core-tab-item-content" data-tab-id="2">''' + photo('tee') + '''</div>
            <div class="gdlr-core-tab-item-content" data-tab-id="1">''' + photo('elbow') + '</div></div>')
        products = parse_page(html, BASE_URL + 'product/fitingi/')
        self.assertEqual([p.name for p in products], ['Отвод', 'Тройник'])
        self.assertTrue(products[0].assets[0].url.endswith('/elbow.jpg'))
        self.assertTrue(products[1].assets[0].url.endswith('/tee.jpg'))
        self.assertEqual(products[0].description, 'Чугунные фитинги')
        self.assertNotIn('+7999', products[0].description)
        self.assertNotEqual(products[0].sku, products[1].sku)

    def test_unmatched_fitting_tabs_fail_instead_of_losing_positions(self):
        html = page('<div class="gdlr-core-tab-item"><div class="gdlr-core-tab-item-title" data-tab-id="1">A</div></div>')
        with self.assertRaises(ValueError):
            parse_page(html, BASE_URL + 'product/fitingi/')

    def test_pipe_series_is_one_product_including_hidden_connection_details(self):
        html = page(photo('pipe') + heading('Труба ZINOC') + '<div><p>Покрытие цинк</p></div>'
                    + heading('Раструбное соединение') + '<div><h4>подробнее</h4><p>Скрытые параметры</p></div>')
        products = parse_page(html, BASE_URL + 'product/chugunnie-trubi/zinoc/')
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].description, 'Покрытие цинк')
        self.assertIn('Скрытые параметры', products[0].characteristics_html)
        self.assertNotIn('подробнее', products[0].characteristics_html)

    def test_pipe_parent_is_not_a_fake_product(self):
        self.assertEqual(parse_page(page(heading('Трубы')), BASE_URL + 'product/chugunnie-trubi/'), [])

    def test_equipment_images_do_not_leak_between_products(self):
        html = page(photo('hydrant') + heading('Гидрант') + '<div><p>Подземный</p></div>'
                    + heading('Крышка') + photo('cover') + '<div><ul><li>Чугунная</li></ul></div>')
        first, second = parse_page(html, BASE_URL + 'product/oborudovanie/')
        self.assertEqual(len(first.assets), 1)
        self.assertTrue(first.assets[0].url.endswith('/hydrant.jpg'))
        self.assertTrue(second.assets[0].url.endswith('/cover.jpg'))
        self.assertEqual(second.description, 'Чугунная')

    def test_valve_family_variants_and_bad_source_description(self):
        html = page(heading(CATEGORIES['zaporno-regulirujuschaja-armatura']) + photo('intro')
            + heading('Обратные клапаны')
            + '<div class="gdlr-core-column-24">' + photo('wrong') + '</div>'
            + '<div class="gdlr-core-column-36"><p><strong>Игольчатые клапаны —</strong> Ошибка</p></div>'
            + '<div class="gdlr-core-column-24">' + photo('swing') + '</div>'
            + '<div class="gdlr-core-column-36"><p><strong>Обратные клапаны поворотного типа –</strong> PN16</p></div>')
        first, second = parse_page(html, BASE_URL + 'product/zaporno-regulirujuschaja-armatura/')
        self.assertEqual(first.name, 'Обратные клапаны')
        self.assertTrue(first.warnings)
        self.assertTrue(product_row(first, brand='SMS', publish=True)['is_hidden'])
        self.assertFalse(product_row(second, brand='SMS', publish=True)['is_hidden'])
        self.assertEqual(len(first.assets), 1)
        self.assertNotEqual(first.sku, second.sku)

    def test_unknown_category_and_changed_markup_fail(self):
        for url in ['product/new-category/', 'product/nasosi/']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                parse_page('<html>Challenge</html>', BASE_URL + url)

    def test_media_use_originals_dedupe_thumbnails_and_video_cache_busters(self):
        url = BASE_URL + 'wp-content/uploads/a.jpg'
        root = BeautifulSoup(f'<a href="{url}"><img src="{url.replace("a.jpg", "a-300x200.jpg")}"></a>'
            + f'<img src="{url.replace("a.jpg", "a-300x200.jpg")}">'
            + '<video><source src="/wp-content/uploads/demo.mp4?_=1"></video>'
            + '<a href="/wp-content/uploads/demo.mp4">Video</a>'
            + '<a href="/wp-content/uploads/cert.pdf">Сертификат</a>'
            + '<img src="https://external.invalid/track.jpg">', 'html.parser')
        assets = collect_assets(root, BASE_URL)
        self.assertEqual([a.kind for a in assets], ['image', 'video', 'document'])
        self.assertEqual(assets[0].url, url)
        self.assertNotIn('?', assets[1].url)

    def test_srcset_uses_largest_available_not_guessed_filename(self):
        root = BeautifulSoup('<img src="/wp-content/uploads/s.jpg" srcset="/wp-content/uploads/m.jpg 300w, /wp-content/uploads/l.jpg 900w">', 'html.parser')
        self.assertTrue(collect_assets(root, BASE_URL)[0].url.endswith('/l.jpg'))

    def test_html_is_safe_and_table_values_are_not_lost(self):
        root = BeautifulSoup('<script>alert(1)</script><p onclick="bad()">DN <strong>80</strong></p>'
            + '<table><tr><td>Расширение</td><td>Класс S-1</td><td>±1% L</td></tr></table>', 'html.parser')
        clean = semantic_html(root)
        self.assertNotIn('script', clean)
        self.assertNotIn('onclick', clean)
        self.assertIn('<strong>80</strong>', clean)
        self.assertEqual(collect_characteristics(clean)['Расширение'], 'Класс S-1 | ±1% L')

    def test_pump_characteristics_include_label_with_next_paragraph_values(self):
        values = collect_characteristics('<p>• Скорость:</p><p>3000 об/мин</p><p>1500 об/мин</p><p>Преимущества</p>')
        self.assertEqual(values['Скорость'], '3000 об/мин; 1500 об/мин')

    def test_crawl_links_skip_external_contacts_and_dedupe(self):
        urls = product_links('<a href="/product/nasosi/?ref=1">A</a><a href="/product/nasosi/#foo">B</a>'
                            '<a href="/contact/">C</a><a href="https://evil.invalid/product/a/">D</a>', BASE_URL)
        self.assertEqual(urls, {BASE_URL + 'product/nasosi/'})

    def test_yandex_folders_are_references_not_product_certificates(self):
        refs = document_references('<div class="realfactory-page-wrapper"><a href="https://disk.yandex.ru/d/a"></a>'
                                   '<a href="https://disk.yandex.ru/d/a">Сертификаты</a></div>', BASE_URL)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]['title'], 'Сертификаты')


class SouthMeridianWorkbookTests(SimpleTestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'products.xlsx'
        self.catalogue = sample_catalogue()

    def test_stable_numeric_skus_and_unique_slugs(self):
        first = [p.sku for p in self.catalogue.products]
        self.assertEqual(first, [p.sku for p in sample_catalogue().products])
        self.assertEqual(len(set(first)), 5)
        self.assertTrue(all(sku.isdigit() and len(sku) == 12 for sku in first))

    def test_default_workbook_is_hidden_without_invented_stock_and_formulas(self):
        self.catalogue.products[0].description = '=HYPERLINK("https://evil.invalid")'
        write_workbook(self.catalogue, self.path)
        workbook = load_workbook(self.path)
        self.addCleanup(workbook.close)
        sheet = workbook.active
        self.assertEqual(sheet.title, 'Products')
        headers = [c.value for c in sheet[1]]
        row = dict(zip(headers, [c.value for c in sheet[2]]))
        self.assertEqual(row['price'], 0)
        self.assertFalse(row['available'])
        self.assertTrue(row['is_hidden'])
        self.assertEqual(sheet.cell(2, headers.index('description') + 1).data_type, 's')
        self.assertIn('char_Диаметр', headers)
        self.assertIn('Документы источника', workbook.sheetnames)

    def test_incomplete_or_duplicate_catalogue_cannot_be_exported(self):
        for modify in [lambda c: c.products.pop(), lambda c: c.products.append(c.products[0]),
                       lambda c: c.errors.append({'error': 'HTTP 500'})]:
            catalogue = sample_catalogue()
            modify(catalogue)
            with self.subTest(modify=modify), self.assertRaises(ValueError):
                write_workbook(catalogue, self.path)
        self.assertFalse(self.path.exists())

    def test_excel_limits_fail_instead_of_silent_truncation(self):
        self.catalogue.products[0].description = 'x' * 32768
        with self.assertRaisesRegex(ValueError, 'не помещается'):
            write_workbook(self.catalogue, self.path)
        self.assertFalse(self.path.exists())


class SouthMeridianImportTests(TestCase):
    def test_workbook_roundtrip_real_importer_and_idempotent_updates(self):
        catalogue = sample_catalogue()
        catalogue.products[0].assets.extend([
            Asset(BASE_URL + 'wp-content/uploads/movie.mp4', 'video', 'Видео, Пример'),
            Asset(BASE_URL + 'wp-content/uploads/tech.pdf', 'document', 'Инструкция'),
            Asset(BASE_URL + 'wp-content/uploads/cert.pdf', 'document', 'Сертификат'),
        ])
        def resolve(url, folder):
            mime = 'video/mp4' if url.endswith('.mp4') else 'application/pdf' if url.endswith('.pdf') else 'image/jpeg'
            return {'storage_path': '/tmp/parser-fixture', 'url': f'/static/admin_uploads/{Path(url).name}',
                    'mime_type': mime, 'size_bytes': 10, 'title': 'File'}, None
        with TemporaryDirectory() as directory, patch('shop.services.catalog_import.resolve_import_file_reference', side_effect=resolve):
            path = Path(directory) / 'products.xlsx'
            write_workbook(catalogue, path)
            counters, issues = import_products_from_workbook(BytesIO(path.read_bytes()))
            self.assertEqual(issues, [])
            self.assertEqual(counters['products_created'], 5)
            self.assertEqual(Product.objects.count(), 5)
            self.assertEqual(Group.objects.count(), 5)
            self.assertEqual(Brand.objects.count(), 1)
            self.assertEqual(ProductMedia.objects.count(), 5)
            self.assertEqual(ProductGalleryItem.objects.count(), 2)
            self.assertEqual(ProductCertificate.objects.count(), 1)
            self.assertEqual(ProductCharacteristic.objects.count(), 5)
            self.assertFalse(Product.objects.filter(is_hidden=False).exists())
            first = Product.objects.get(sku=catalogue.products[0].sku)
            catalogue.products[0].description = 'Обновлено'
            write_workbook(catalogue, path)
            counters, issues = import_products_from_workbook(BytesIO(path.read_bytes()))
            first.refresh_from_db()
            self.assertEqual(first.description, 'Обновлено')
            self.assertEqual(counters['products_updated'], 5)
            self.assertEqual(Product.objects.count(), 5)
            self.assertEqual(ProductMedia.objects.count(), 5)
            self.assertEqual(issues, [])
