from email.message import Message
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.test import SimpleTestCase

from shop.services.south_meridian.client import SourceClient, SourceRedirectHandler, source_url
from shop.services.south_meridian.crawler import crawl_catalogue, sitemap_products
from shop.services.south_meridian.schema import BASE_URL


def response(body, mime='text/html; charset=utf-8', size=None):
    result = MagicMock()
    result.__enter__.return_value = result
    result.read.return_value = body
    result.headers = Message()
    result.headers['Content-Type'] = mime
    result.headers['Content-Length'] = str(size or len(body))
    return result


class SouthMeridianHTTPTests(SimpleTestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.client = SourceClient(temporary.name, delay=0)
        self.client.opener = MagicMock()

    def test_utf8_cookie_challenge_then_cached_page(self):
        self.client.opener.open.side_effect = [
            response(b"<script>document.cookie='beget=begetok';location.reload()</script>"),
            response('<h3>Трубы</h3>'.encode('utf-8')),
        ]
        self.assertEqual(self.client.text(BASE_URL), '<h3>Трубы</h3>')
        request = self.client.opener.open.call_args.args[0]
        self.assertEqual(request.get_header('Cookie'), 'beget=begetok')
        self.assertEqual(self.client.text(BASE_URL), '<h3>Трубы</h3>')
        self.assertEqual(self.client.opener.open.call_count, 2)

    def test_repeated_challenge_is_not_cached_as_catalogue(self):
        self.client.opener.open.return_value = response(b"<script>document.cookie='beget=begetok'</script>")
        with self.assertRaises(ValueError):
            self.client.text(BASE_URL)
        self.assertFalse(list(self.client.cache_dir.iterdir()))

    def test_cross_origin_links_and_redirects_are_rejected_before_loading(self):
        for url in ['https://south-meridian.ru.evil.invalid/', 'http://south-meridian.ru/',
                    'https://user:pass@south-meridian.ru/', '//localhost/private']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                source_url(url)
        with self.assertRaises(ValueError):
            SourceRedirectHandler().redirect_request(None, None, 302, '', {}, 'http://127.0.0.1/')

    def test_robots_disallow_prevents_network_request(self):
        self.client.opener.open.return_value = response(b'User-agent: *\nDisallow: /product/\n', 'text/plain')
        self.client.load_robots()
        with self.assertRaisesRegex(ValueError, 'robots.txt'):
            self.client.text(BASE_URL + 'product/nasosi/')
        self.assertEqual(self.client.opener.open.call_count, 1)

    @patch('shop.services.south_meridian.client.time.sleep')
    def test_retries_transient_errors_but_not_404(self, sleep):
        self.client.opener.open.side_effect = [
            HTTPError(BASE_URL, 503, 'busy', {}, None), response(b'<html>OK</html>')]
        self.assertEqual(self.client.text(BASE_URL), '<html>OK</html>')
        self.client.opener.open.reset_mock()
        self.client.opener.open.side_effect = HTTPError(BASE_URL, 404, 'missing', {}, None)
        with self.assertRaises(HTTPError):
            self.client.text(BASE_URL + 'missing/')
        self.assertEqual(self.client.opener.open.call_count, 1)

    def test_wrong_mime_and_oversized_asset_are_not_successes(self):
        for mime, size in [('text/html', 500), ('image/jpeg', 101 * 1024 * 1024)]:
            self.client.opener.open.return_value = response(b'', mime, size)
            with self.subTest(mime=mime), self.assertRaises(ValueError):
                self.client.check_asset(BASE_URL + 'wp-content/uploads/a.jpg', 'image')

    def test_empty_page_is_not_success(self):
        self.client.opener.open.return_value = response(b'')
        with self.assertRaises(ValueError):
            self.client.text(BASE_URL)

    def test_sitemap_follows_nested_maps_and_ignores_non_products(self):
        self.client.text = MagicMock(side_effect=[
            f'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>{BASE_URL}page-sitemap.xml</loc></sitemap></sitemapindex>',
            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{BASE_URL}product/nasosi/</loc></url><url><loc>{BASE_URL}contact/</loc></url></urlset>',
        ])
        self.assertEqual(sitemap_products(self.client, [BASE_URL + 'sitemap_index.xml']), {BASE_URL + 'product/nasosi/'})

    def test_discovery_failure_is_reported_not_an_empty_success(self):
        self.client.load_robots = MagicMock(side_effect=ValueError('HTTP challenge'))
        catalogue = crawl_catalogue(self.client)
        self.assertTrue(catalogue.errors)
        self.assertEqual(catalogue.products, [])
