from io import BytesIO

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.http import QueryDict
from django.test import TestCase, override_settings
from django.urls import reverse
from openpyxl import load_workbook
from rest_framework.test import APIClient

from shop.catalog_cache import catalog_cache_version
from shop.models import Brand, Group, Product
from shop.services.catalog_export import workbook_bytes_from_product_export
from shop.services.catalog_visibility import set_catalog_visibility
from shop.sitemaps import ProducerPagesSitemap, ProductPagesSitemap
from shop.views.products import build_popular_products_cache_key
from shop.views.search import build_search_cache_key


@override_settings(ALLOWED_HOSTS=['testserver'])
class CatalogVisibilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser('visibility-admin', password='test-password')
        cls.group = Group.objects.create(name='Insulation', slug='insulation')
        cls.brand = Brand.objects.create(name='Visiblemark', slug='visiblemark')
        cls.hidden_brand = Brand.objects.create(name='Secretmark', slug='secretmark', is_hidden=True)
        cls.product = Product.objects.create(name='Visible product', sku='101', price=10, currency='RUB', group=cls.group, brand=cls.brand)
        cls.hidden = Product.objects.create(name='Hidden product', sku='102', price=20, currency='RUB', group=cls.group, brand=cls.brand, is_hidden=True)
        cls.brand_product = Product.objects.create(name='Secretmark product', sku='103', price=30, currency='RUB', group=cls.group, brand=cls.hidden_brand)
        cls.unbranded = Product.objects.create(name='Unbranded product', sku='104', price=40, currency='RUB', group=cls.group)

    def setUp(self):
        self.api = APIClient()
        cache.clear()
        self.client.force_login(self.admin_user)

    def action(self, model, action, ids, **extra):
        return self.client.post(reverse(f'admin:shop_{model}_changelist'), {
            'action': action, '_selected_action': ids, 'index': 0, **extra,
        })

    def test_public_lists_and_facets_exclude_hidden_brand_products(self):
        expected = {self.product.pk, self.unbranded.pk}
        for route, payload in [('products-filter', {}), ('catalog-results', {})]:
            with self.subTest(route=route):
                response = self.api.post(reverse(route), payload, format='json')
                self.assertEqual(response.status_code, 200)
                self.assertEqual({item['id'] for item in response.json()['results']}, expected)
        response = self.api.get(reverse('products-list'))
        self.assertEqual({item['id'] for item in response.json()}, expected)
        response = self.api.get(reverse('groups-detail', args=[self.group.slug]))
        self.assertEqual({item['id'] for item in response.json()['products']}, expected)
        response = self.api.post(reverse('catalog-facets'), {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.hidden_brand.pk, [brand['id'] for brand in response.json()['brands']])
        self.assertEqual(response.json()['summary']['total_products'], 2)

    def test_brand_lists_details_and_sitemaps_respect_visibility(self):
        response = self.api.get(reverse('brands-list'))
        self.assertEqual([brand['id'] for brand in response.json()], [self.brand.pk])
        for identifier in (self.hidden_brand.pk, self.hidden_brand.slug):
            self.assertEqual(self.api.get(reverse('brands-detail', args=[identifier])).status_code, 404)
        self.assertEqual(list(ProducerPagesSitemap().items()), [self.brand])
        self.assertEqual(set(ProductPagesSitemap().items()), {self.product, self.unbranded})

    def test_hidden_products_detail_and_nested_resources_are_unavailable(self):
        for product in (self.hidden, self.brand_product):
            for identifier in (product.pk, product.slug):
                self.assertEqual(self.api.get(reverse('products-detail', args=[identifier])).status_code, 404)
            for route in ('product-media-list', 'product-certificate-list', 'product-attributes'):
                with self.subTest(product=product.pk, route=route):
                    self.assertEqual(self.api.get(reverse(route, args=[product.pk])).status_code, 404)

    def test_search_does_not_suggest_hidden_brand(self):
        for params in ({'q': 'Secretmark'}, {'q': 'Secretmark', 'debug': 'true'}):
            response = self.api.get(reverse('global-search'), params)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['results']['brands'], [])
            self.assertEqual(response.json()['results']['products'], [])
            self.assertIsNone(response.json()['navigation']['brand'])

    def test_product_bulk_action_logs_changes_and_only_changes_selected_rows(self):
        response = self.action('product', 'hide_selected', [self.product.pk, self.unbranded.pk])
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.objects.visible().exists())
        self.brand_product.refresh_from_db()
        self.assertFalse(self.brand_product.is_hidden)
        self.assertEqual(LogEntry.objects.filter(user=self.admin_user).count(), 2)
        self.action('product', 'show_selected', [self.product.pk, self.unbranded.pk])
        self.assertEqual(set(Product.objects.visible()), {self.product, self.unbranded})
        self.hidden.refresh_from_db()
        self.assertTrue(self.hidden.is_hidden)

    def test_bulk_brand_restore_preserves_individually_hidden_products(self):
        self.action('brand', 'hide_selected', [self.brand.pk])
        self.assertEqual(set(Product.objects.visible()), {self.unbranded})
        self.action('brand', 'show_selected', [self.brand.pk])
        self.assertEqual(set(Product.objects.visible()), {self.product, self.unbranded})
        self.assertEqual(Product.objects.count(), 4)
        self.assertEqual(Brand.objects.count(), 2)

    def test_select_all_action_respects_changelist_filter(self):
        url = reverse('admin:shop_product_changelist') + f'?brand__id__exact={self.brand.pk}'
        response = self.client.post(url, {'action': 'hide_selected', '_selected_action': [self.product.pk], 'select_across': '1', 'index': 0})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(set(Product.objects.visible()), {self.unbranded})

    def test_view_only_staff_cannot_change_visibility(self):
        viewer = get_user_model().objects.create_user('viewer', is_staff=True)
        viewer.user_permissions.add(Permission.objects.get(codename='view_product'))
        self.client.force_login(viewer)
        response = self.client.get(reverse('admin:shop_product_changelist'))
        self.assertNotContains(response, 'value="hide_selected"')
        self.action('product', 'hide_selected', [self.product.pk])
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_hidden)

    def test_brand_edit_form_can_hide_brand(self):
        response = self.client.post(reverse('admin:shop_brand_change', args=[self.brand.pk]), {
            'name': self.brand.name, 'slug': self.brand.slug, 'search_synonyms': '',
            'is_hidden': 'on', 'media': '', '_save': 'Save',
        })
        self.assertEqual(response.status_code, 302)
        self.brand.refresh_from_db()
        self.assertTrue(self.brand.is_hidden)
        self.assertNotIn(self.product, Product.objects.visible())

    def test_hide_and_restore_invalidate_existing_search_and_popular_caches(self):
        params = {'popular': 'true'}
        search_params = {'q': 'Visiblemark'}
        self.api.get(reverse('products-list'), params)
        self.api.get(reverse('global-search'), search_params)
        popular_key = build_popular_products_cache_key(QueryDict('popular=true'))
        search_key = build_search_cache_key('Visiblemark', None)
        self.assertIsNotNone(cache.get(popular_key))
        self.assertIsNotNone(cache.get(search_key))
        for hidden in (True, False):
            set_catalog_visibility(Brand.objects.filter(pk=self.brand.pk), hidden=hidden)
            # Old entries still exist: a shared DB version invalidates other workers too.
            self.assertNotEqual(popular_key, build_popular_products_cache_key(QueryDict('popular=true')))
            self.assertNotEqual(search_key, build_search_cache_key('Visiblemark', None))
            popular = self.api.get(reverse('products-list'), params).json()
            search = self.api.get(reverse('global-search'), search_params).json()
            self.assertEqual(self.product.pk in [p['id'] for p in popular], not hidden)
            self.assertEqual(self.product.pk in [p['id'] for p in search['results']['products']], not hidden)
        self.assertIsNotNone(cache.get(popular_key))

    def test_individual_save_also_invalidates_cache_and_noop_action_does_not(self):
        before = catalog_cache_version()
        self.product.is_hidden = True
        self.product.save(update_fields=['is_hidden'])
        self.assertNotEqual(before, catalog_cache_version())
        after = catalog_cache_version()
        self.assertEqual(set_catalog_visibility(Product.objects.filter(pk=self.product.pk), hidden=True), [])
        self.assertEqual(after, catalog_cache_version())

    def test_hidden_products_cannot_be_submitted_from_an_old_cart(self):
        for product in (self.hidden, self.brand_product):
            response = self.api.post(reverse('public-order-create'), {
                'name': 'Customer', 'phone': '+79999999999',
                'items': [{'product_id': product.pk, 'qty': 1}],
            }, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertIn('items', response.json())

    def test_export_keeps_hidden_records_and_brand_flag(self):
        workbook = load_workbook(BytesIO(workbook_bytes_from_product_export(Product.objects.all())))
        rows = list(workbook['Brands'].values)
        brands = [dict(zip(rows[0], row)) for row in rows[1:]]
        self.assertTrue(next(row for row in brands if row['id'] == self.hidden_brand.pk)['is_hidden'])
        self.assertEqual(len(brands), 2)
