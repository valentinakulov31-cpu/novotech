import time
from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from .schema import BASE_URL


USER_AGENT = "NovatehCatalogParser/1.0"
MAX_PAGE_BYTES = 10 * 1024 * 1024


def source_url(value, base=BASE_URL):
    parts = urlsplit(urljoin(base, value))
    if (parts.scheme != "https" or parts.netloc != "south-meridian.ru"
            or parts.username or parts.password):
        raise ValueError(f"URL вне разрешенного источника: {value}")
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", "", ""))


class SourceRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        source_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class SourceClient:
    def __init__(self, cache_dir, *, delay=0.25, timeout=20, refresh=False):
        if delay < 0 or timeout <= 0:
            raise ValueError("delay должен быть >= 0, timeout > 0")
        self.cache_dir = Path(cache_dir)
        self.delay = delay
        self.timeout = timeout
        self.refresh = refresh
        self.opener = build_opener(SourceRedirectHandler())
        self.robots = None
        self.last_request = 0
        self.cookie = False

    def _request(self, url, method="GET"):
        url = source_url(url)
        if self.robots and not self.robots.can_fetch(USER_AGENT, url):
            raise ValueError(f"robots.txt запрещает загрузку: {url}")
        for attempt in range(3):
            time.sleep(max(0, self.delay - (time.monotonic() - self.last_request)))
            headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
            if self.cookie:
                headers["Cookie"] = "beget=begetok"
            self.last_request = time.monotonic()
            try:
                with self.opener.open(Request(url, headers=headers, method=method), timeout=self.timeout) as response:
                    body = b"" if method == "HEAD" else response.read(MAX_PAGE_BYTES + 1)
                    if len(body) > MAX_PAGE_BYTES:
                        raise ValueError(f"Страница превышает лимит {MAX_PAGE_BYTES} байт: {url}")
                    return body, response.headers
            except HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                    raise
            except (URLError, TimeoutError):
                if attempt == 2:
                    raise
            time.sleep(2 ** attempt)

    def text(self, url):
        url = source_url(url)
        if self.robots and not self.robots.can_fetch(USER_AGENT, url):
            raise ValueError(f"robots.txt запрещает загрузку: {url}")
        cache = self.cache_dir / f"{sha256(url.encode()).hexdigest()}.txt"
        if cache.exists() and not self.refresh:
            return cache.read_text(encoding="utf-8")
        body, headers = self._request(url)
        # The source's documented-by-response technical cookie, not arbitrary JS execution.
        if b"document.cookie='beget=begetok'" in body and len(body) < 4096:
            self.cookie = True
            body, headers = self._request(url)
        if b"document.cookie='beget=begetok'" in body or not body.strip():
            raise ValueError(f"Вместо страницы получена проверка браузера или пустой ответ: {url}")
        mime = headers.get_content_type()
        if mime not in {"text/html", "text/plain", "text/xml", "application/xml"}:
            raise ValueError(f"Неожиданный Content-Type {mime}: {url}")
        text = body.decode(headers.get_content_charset() or "utf-8-sig")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(text, encoding="utf-8")
        return text

    def load_robots(self):
        url = urljoin(BASE_URL, "robots.txt")
        # Always recheck policy, including when the HTML cache is reused.
        refresh = self.refresh
        self.refresh = True
        try:
            text = self.text(url)
        finally:
            self.refresh = refresh
        self.robots = RobotFileParser(url)
        self.robots.parse(text.splitlines())
        self.delay = max(self.delay, self.robots.crawl_delay(USER_AGENT) or 0)
        return self.robots.site_maps() or [urljoin(BASE_URL, "sitemap_index.xml")]

    def check_asset(self, url, kind):
        _, headers = self._request(url, "HEAD")
        mime = headers.get_content_type()
        size = int(headers.get("Content-Length", "0"))
        expected = "application/pdf" if kind == "document" else f"{kind}/"
        if not mime.startswith(expected):
            raise ValueError(f"Вместо файла {kind} получен {mime}")
        if not 0 < size <= 100 * 1024 * 1024:
            raise ValueError(f"Размер файла {size} байт не подходит импорту (лимит 100 МБ)")
        return {"url": url, "kind": kind, "mime_type": mime, "size_bytes": size, "status": "ok"}
