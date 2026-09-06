from urllib.parse import urlsplit

from .extraction import content_root, fragment, make_product, normalize_text
from .schema import CATEGORIES


def heading_sections(root):
    """Split on outer builder headings, not nested accordion captions."""
    sections = []
    prefix = []
    current = None
    for node in root.find_all(recursive=False):
        heading = node.select_one("h3.gdlr-core-title-item-title")
        if heading:
            current = [normalize_text(heading.get_text()), [node]]
            sections.append(current)
        elif current is None:
            prefix.append(node)
        else:
            current[1].append(node)
    if sections:
        sections[0][1][0:0] = prefix
    return sections


def parse_fittings(root, url, category):
    tabs = root.select(".gdlr-core-tab-item")
    if len(tabs) != 1:
        raise ValueError("Ожидался один блок вкладок фитингов; требуется проверка разметки")
    tabs = tabs[0]
    titles = tabs.select(".gdlr-core-tab-item-title[data-tab-id]")
    contents = {node["data-tab-id"]: node for node in tabs.select(".gdlr-core-tab-item-content[data-tab-id]")}
    if not titles or len(titles) != len(contents):
        raise ValueError("Не совпадают названия и содержимое вкладок фитингов")
    intro = root.select_one(".gdlr-core-text-box-item-content")
    description = normalize_text(intro.get_text(" ", strip=True)) if intro else ""
    products = []
    for title in titles:
        tab_id = title["data-tab-id"]
        if tab_id not in contents:
            raise ValueError(f"Не найдено содержимое вкладки {tab_id}")
        name = normalize_text(title.get_text())
        product = make_product(url, f"tab-{tab_id}", name, category, contents[tab_id], description=description or name)
        product.characteristics["Тип изделия"] = name
        products.append(product)
    return products


def parse_valves(root, url, category):
    sections = heading_sections(root)
    if not sections or sections[0][0] != category:
        raise ValueError("Не найден заголовок категории арматуры")
    products = []
    for heading, nodes in sections[1:]:
        # Two families list each variant as an image column followed by a text column.
        if heading not in {"Задвижки чугунные", "Обратные клапаны"}:
            products.append(make_product(url, heading, heading, category, fragment(nodes)))
            continue
        pairs = []
        pending = None
        for node in nodes[1:]:
            classes = node.get("class", [])
            if "gdlr-core-column-24" in classes and node.select_one("img"):
                if pending is not None:
                    raise ValueError(f"У фотографии нет описания: {heading}")
                pending = node
            elif "gdlr-core-column-36" in classes and normalize_text(node.get_text()):
                if pending is None:
                    raise ValueError(f"У описания нет фотографии: {heading}")
                pairs.append((pending, node))
                pending = None
        if pending is not None or not pairs:
            raise ValueError(f"Не удалось разобрать все варианты: {heading}")
        for image, text in pairs:
            title = text.select_one("strong")
            if not title:
                raise ValueError(f"Нет названия варианта: {heading}")
            name = normalize_text(title.get_text()).rstrip(" -–—:")
            # The source currently copied a needle-valve description into this family.
            mismatch = heading == "Обратные клапаны" and name.startswith("Игольчатые")
            if mismatch:
                name = heading
            key = f"{heading}:{image.select_one('img').get('src')}"
            product = make_product(url, key, name, category, fragment([image, text]))
            if mismatch:
                product.warnings.append("Ошибка источника: у обратного клапана описание игольчатого. Проверить вручную; позиция скрыта.")
            products.append(product)
    if not products:
        raise ValueError("Категория арматуры не содержит распознанных товаров")
    return products


def parse_page(html, url):
    parts = urlsplit(url).path.strip("/").split("/")
    if len(parts) < 2 or parts[0] != "product" or parts[1] not in CATEGORIES:
        raise ValueError(f"Неизвестная товарная категория: {url}")
    category = CATEGORIES[parts[1]]
    root = content_root(html)
    if parts[1] == "fitingi" and len(parts) == 2:
        return parse_fittings(root, url, category)
    if parts[1] == "zaporno-regulirujuschaja-armatura" and len(parts) == 2:
        return parse_valves(root, url, category)
    if parts[1] == "oborudovanie" and len(parts) == 2:
        sections = heading_sections(root)
        if not sections:
            raise ValueError("Не найдены позиции оборудования")
        return [make_product(url, name, name, category, fragment(nodes)) for name, nodes in sections]
    if parts[1] == "chugunnie-trubi" and len(parts) == 2:
        return []
    title = root.select_one("h3.gdlr-core-title-item-title")
    if not title:
        raise ValueError(f"Не найдено название товарной серии: {url}")
    name = normalize_text(title.get_text())
    return [make_product(url, "page", name, category, root)]
