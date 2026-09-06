import re
from pathlib import PurePosixPath
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Comment

from .schema import Asset, SourceProduct


ALLOWED_TAGS = {
    "p", "br", "strong", "b", "em", "i", "ul", "ol", "li", "h2", "h3", "h4",
    "table", "thead", "tbody", "tr", "th", "td", "sup", "sub",
}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_SUFFIXES = {".mp4", ".webm"}


def normalize_text(value):
    return re.sub(r"\s+", " ", str(value)).strip()


def content_root(html):
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one(".gdlr-core-pbf-sidebar-content-inner")
    if root is None:
        raise ValueError("Не найден товарный блок: разметка источника изменилась")
    for unwanted in root.select("script, style, iframe, form, .realfactory-widget, .gdlr-core-button-item"):
        unwanted.decompose()
    return root


def fragment(nodes):
    return BeautifulSoup("".join(str(node) for node in nodes), "html.parser")


def semantic_html(root):
    soup = BeautifulSoup(str(root), "html.parser")
    for tag in soup.select("script, style, iframe, form, video, audio, img, source, button"):
        tag.decompose()
    for tag in soup.select("h4"):
        if normalize_text(tag.get_text()).lower().startswith("подробнее"):
            tag.decompose()
    for node in soup.find_all(string=lambda text: isinstance(text, Comment)):
        node.extract()
    for tag in list(soup.find_all(True)):
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()
            continue
        tag.attrs = {key: value for key, value in tag.attrs.items()
                     if tag.name in {"td", "th"} and key in {"colspan", "rowspan"}
                     and str(value).isdigit()}
    for tag in reversed(soup.find_all(True)):
        if not tag.get_text(strip=True) and tag.name != "br":
            tag.decompose()
    return re.sub(r">\s+<", "><", str(soup)).strip()


def collect_assets(root, page_url):
    found = {}

    def add(raw_url, title="", expected=None):
        url = urljoin(page_url, raw_url or "")
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.netloc != "south-meridian.ru":
            return
        if not parts.path.startswith("/wp-content/uploads/"):
            return
        suffix = PurePosixPath(parts.path).suffix.lower()
        kind = ("image" if suffix in IMAGE_SUFFIXES else "video" if suffix in VIDEO_SUFFIXES
                else "document" if suffix == ".pdf" else None)
        if not kind or (expected and kind != expected):
            return
        # Our import separates URLs on comma/semicolon/newline.
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        url = url.replace(",", "%2C").replace(";", "%3B")
        title = normalize_text(title)
        if not title or title.startswith(("http://", "https://")):
            title = unquote(PurePosixPath(parts.path).name)
        found.setdefault(url, Asset(url, kind, title))

    for img in root.select("img"):
        parent = img.find_parent("a", href=True)
        full = parent.get("href", "") if parent else ""
        if PurePosixPath(urlsplit(full).path).suffix.lower() not in IMAGE_SUFFIXES:
            candidates = []
            for part in img.get("srcset", "").split(","):
                match = re.match(r"\s*(\S+)\s+(\d+)w\s*$", part)
                if match:
                    candidates.append((int(match[2]), match[1]))
            full = max(candidates)[1] if candidates else img.get("data-src") or img.get("src")
        add(full, img.get("alt") or img.get("title"), "image")
    for tag in root.select("a[href], video[src], source[src]"):
        url = tag.get("href") or tag.get("src")
        if tag.name == "a" and tag.select_one("img"):
            continue
        add(url, tag.get("title") or tag.get_text(" ", strip=True))
    # WordPress also renders duplicate thumbnail navigation below some galleries.
    return [asset for asset in found.values()
            if not (asset.kind == "image" and
                    re.sub(r"-\d+x\d+(?=\.[^.]+$)", "", asset.url) in found and
                    re.search(r"-\d+x\d+(?=\.[^.]+$)", asset.url))]


def collect_characteristics(html):
    soup = BeautifulSoup(html, "html.parser")
    values = {}

    def add(key, value):
        key = normalize_text(key).strip(" •:-")
        value = normalize_text(value).strip(" •")
        if 1 < len(key) <= 180 and value:
            previous = values.get(key)
            values[key] = f"{previous}; {value}" if previous and previous != value else value

    for row in soup.select("tr"):
        cells = row.find_all(["td", "th"], recursive=False)
        if 2 <= len(cells) <= 3 and not all(cell.name == "th" for cell in cells):
            add(cells[0].get_text(" ", strip=True), " | ".join(c.get_text(" ", strip=True) for c in cells[1:]))
    for tag in soup.select("li, p"):
        if tag.find_parent(["li", "td", "th"]) or tag.find(["li", "p"]):
            continue
        text = tag.get_text(" ", strip=True)
        match = re.match(r"^[\s•]*([^:]{2,80}):\s*(.{1,500})$", text)
        if match:
            add(match[1], match[2])
        label = re.match(r"^[\s•]*([^:]{2,80}):\s*$", text)
        if label:
            following = []
            for sibling in tag.find_next_siblings():
                value = normalize_text(sibling.get_text(" ", strip=True))
                if sibling.name != "p" or not re.match(r"^\d", value):
                    break
                following.append(value)
            if following:
                add(label[1], "; ".join(following))
        flow = re.search(r"Скорость потока\s+(\d[^•]+)", text)
        if flow:
            add("Скорость потока", flow[1])
    text = soup.get_text(" ", strip=True)
    standards = list(dict.fromkeys(re.findall(r"\b(?:EN(?:\s+ISO)?|ISO)\s+\d+(?:-\d+)?\b", text)))
    if standards:
        add("Стандарты", "; ".join(standards))
    pressures = list(dict.fromkeys(re.findall(r"\bPN\s*(\d+(?:\s*[-/]\s*\d+)*)", text)))
    if pressures:
        add("Номинальное давление (PN)", "; ".join(pressures))
    return values


def make_product(url, key, name, category, root, *, description=None):
    html = semantic_html(root)
    soup = BeautifulSoup(html, "html.parser")
    first_heading = soup.find(["h2", "h3"])
    if first_heading and normalize_text(first_heading.get_text()) == name:
        first_heading.decompose()
    if description is None:
        intro = []
        for tag in soup.find_all(recursive=False):
            if tag.name in {"h2", "h3"}:
                break
            if tag.name == "p":
                value = normalize_text(tag.get_text(" ", strip=True))
                if value and not value.endswith(":"):
                    intro.append(value)
        description = "\n\n".join(intro) or "\n".join(
            normalize_text(li.get_text(" ", strip=True)) for li in soup.select("li")
        ) or name
    product = SourceProduct(
        source_url=url, source_key=key, name=name, category=category,
        description=description, characteristics_html=str(soup).strip(),
        characteristics=collect_characteristics(html), assets=collect_assets(root, url),
    )
    if not any(asset.kind == "image" for asset in product.assets):
        product.warnings.append("На странице позиции не найдено изображение")
    return product
