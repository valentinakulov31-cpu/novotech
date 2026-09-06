from collections import deque
from urllib.parse import urlsplit
from xml.etree import ElementTree

from bs4 import BeautifulSoup

from .client import source_url
from .extraction import collect_assets, content_root, normalize_text, semantic_html
from .parser import parse_page
from .schema import BASE_URL, CATEGORIES, Catalogue


MAX_SOURCE_PAGES = 250


def product_links(html, base):
    urls = set()
    for tag in BeautifulSoup(html, "html.parser").select("a[href]"):
        try:
            url = source_url(tag["href"], base)
        except ValueError:
            continue
        if urlsplit(url).path.startswith("/product/"):
            urls.add(url.rstrip("/") + "/")
    return urls


def sitemap_products(client, sitemaps):
    pending = deque(sitemaps)
    seen = set()
    urls = set()
    while pending:
        url = source_url(pending.popleft())
        if url in seen:
            continue
        seen.add(url)
        if len(seen) > 20:
            raise ValueError("Превышен лимит вложенных sitemap")
        root = ElementTree.fromstring(client.text(url))
        kind = root.tag.rsplit("}", 1)[-1]
        if kind not in {"sitemapindex", "urlset"}:
            raise ValueError(f"Неожиданный формат sitemap: {url}")
        for loc in root.findall(".//{*}loc"):
            target = source_url(loc.text or "", url)
            if kind == "sitemapindex":
                pending.append(target)
            elif urlsplit(target).path.startswith("/product/"):
                urls.add(target.rstrip("/") + "/")
    return urls


def document_references(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one(".realfactory-page-wrapper")
    if root is None:
        raise ValueError("Не найдена страница документации")
    refs = {}
    for a in root.select("a[href]"):
        url = a["href"]
        parts = urlsplit(url)
        if parts.scheme == "https" and parts.netloc == "disk.yandex.ru":
            title = normalize_text(a.get_text(" ", strip=True))
            refs.setdefault(url, {"title": "", "url": url, "source_url": page_url,
                                  "note": "Общая папка поставщика; соответствие конкретным товарам не установлено"})
            if title:
                refs[url]["title"] = title
    return list(refs.values())


def crawl_catalogue(client, *, check_media=True, progress=lambda message: None):
    result = Catalogue()
    try:
        seeds = sitemap_products(client, client.load_robots())
        seeds.add(source_url("product/"))
        pending = deque(sorted(seeds))
        visited = set()
        while pending:
            url = pending.popleft()
            if url in visited:
                continue
            visited.add(url)
            if len(visited) > MAX_SOURCE_PAGES:
                raise ValueError("Превышен лимит страниц каталога")
            progress(f"Страница {len(visited)}: {url}")
            try:
                html = client.text(url)
                pending.extend(sorted(product_links(html, url) - visited))
                parts = urlsplit(url).path.strip("/").split("/")
                products = [] if parts == ["product"] else parse_page(html, url)
                result.products.extend(products)
                result.pages.append({"url": url, "status": "parsed" if products else "category",
                                     "products": len(products)})
                if len(parts) == 2 and parts[1] in CATEGORIES:
                    root = content_root(html)
                    images = [asset.url for asset in collect_assets(root, url) if asset.kind == "image"]
                    result.categories.append({"name": CATEGORIES[parts[1]], "source_url": url,
                                              "media_url": images[0] if images else "",
                                              "source_content_html": semantic_html(root)})
            except Exception as exc:
                result.errors.append({"url": url, "error": str(exc)})
                result.pages.append({"url": url, "status": "error", "products": 0})
        docs_url = source_url("documenti/")
        result.documents = document_references(client.text(docs_url), docs_url)
        result.validate()
        if check_media:
            assets = {asset.url: asset for product in result.products for asset in product.assets}
            for index, asset in enumerate(assets.values(), 1):
                progress(f"Проверка файла {index}/{len(assets)}: {asset.url}")
                try:
                    result.media_checks.append(client.check_asset(asset.url, asset.kind))
                except Exception as exc:
                    issue = {"url": asset.url, "error": str(exc)}
                    result.media_checks.append({**issue, "status": "error"})
                    result.errors.append(issue)
    except Exception as exc:
        result.errors.append({"url": BASE_URL, "error": str(exc)})
    return result
