import re
from collections import OrderedDict

from bs4 import BeautifulSoup
from django.utils.html import escape

_TABLE_TOKEN_RE = re.compile(r"<table\b[^>]*>|</table\s*>", flags=re.IGNORECASE)


def parse_style_declarations(style_text: str | None) -> OrderedDict[str, str]:
    declarations: OrderedDict[str, str] = OrderedDict()
    if not style_text:
        return declarations
    for chunk in style_text.split(";"):
        if ":" not in chunk:
            continue
        key, value = chunk.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key and value:
            declarations[key] = value
    return declarations


def serialize_style_declarations(declarations: OrderedDict[str, str]) -> str:
    return "; ".join(f"{key}: {value}" for key, value in declarations.items() if value)


def merge_style_declarations(existing: str | None, enforced: dict[str, str]) -> str:
    merged = parse_style_declarations(existing)
    merged.update(enforced)
    return serialize_style_declarations(merged)


def strip_style_declarations(existing: str | None, removable: dict[str, str]) -> str:
    declarations = parse_style_declarations(existing)
    for key, value in removable.items():
        if declarations.get(key) == value:
            declarations.pop(key, None)
    return serialize_style_declarations(declarations)


def sanitize_catalog_tables(html: str | None) -> str | None:
    if not html:
        return html

    spans = _find_top_level_table_spans(html)
    if not spans:
        return html

    result: list[str] = []
    cursor = 0
    for start, end in spans:
        result.append(html[cursor:start])
        result.append(_normalize_table_block(html[start:end]))
        cursor = end
    result.append(html[cursor:])
    return "".join(result)


def _find_top_level_table_spans(html: str) -> list[tuple[int, int]]:
    """Балансный поиск <table>...</table>, устойчивый к вложенным таблицам."""
    spans: list[tuple[int, int]] = []
    depth = 0
    start = 0
    for token in _TABLE_TOKEN_RE.finditer(html):
        if not token.group(0).startswith("</"):
            if depth == 0:
                start = token.start()
            depth += 1
        elif depth:
            depth -= 1
            if depth == 0:
                spans.append((start, token.end()))
    return spans


def _normalize_table_block(block: str) -> str:
    soup = BeautifulSoup(block, "html.parser")
    changed = [_normalize_table_tag(table) for table in soup.find_all("table")]
    if not any(changed):
        # Нераспознанные таблицы возвращаем исходной подстрокой —
        # без пересериализации, байт в байт.
        return block
    return soup.decode(formatter="html")


def _normalize_table_tag(table) -> bool:
    styles = parse_style_declarations(table.get("style"))
    border_style = styles.get("border-style")
    is_catalog = border_style == "var(--catalog-table-border-style)"
    is_regular_border = (
        bool(border_style and table.get("border") == "1")
        or table.get("data-catalog-table") == "1"
    )

    if not is_catalog and not is_regular_border:
        return False

    for attribute in ("border", "cellpadding", "cellspacing"):
        del table[attribute]

    if is_catalog:
        table["data-catalog-table"] = "1"
        table["style"] = merge_style_declarations(
            table.get("style"),
            {
                "width": "100%",
                "background-color": "white",
                "border-collapse": "collapse",
                "font-size": "14px",
            },
        )
        mode, cell_border_style = "catalog", "solid"
    else:
        del table["data-catalog-table"]
        table["style"] = strip_style_declarations(
            table.get("style"),
            {
                "background-color": "white",
                "font-size": "14px",
                "margin": "16px 0",
            },
        )
        table["style"] = merge_style_declarations(
            table.get("style"),
            {"border-width": styles.get("border-width") or "1px"},
        )
        mode, cell_border_style = "regular", border_style

    for row in table.find_all("tr"):
        # Строки вложенных таблиц нормализуются своей таблицей, не внешней.
        if row.find_parent("table") is not table:
            continue
        cell_index = 0
        for cell in row.find_all(("td", "th"), recursive=False):
            cell_index += 1
            _normalize_cell(cell, mode=mode, border_style=cell_border_style, cell_index=cell_index)

    return True


def _normalize_cell(cell, *, mode: str, border_style: str | None, cell_index: int) -> None:
    styles = parse_style_declarations(cell.get("style"))

    if mode == "catalog":
        enforced: OrderedDict[str, str] = OrderedDict()
        if "width" in styles:
            enforced["width"] = styles["width"].replace("100.033%", "100%")
        enforced["padding"] = "12px"
        enforced["border"] = "1px solid #e1e1e1"
        enforced["text-align"] = "left" if cell_index == 1 else "center"
        cell["style"] = serialize_style_declarations(enforced)
    else:
        cleaned: OrderedDict[str, str] = OrderedDict()
        if "width" in styles:
            cleaned["width"] = styles["width"].replace("100.033%", "100%")
        cleaned["border"] = f"1px {border_style} currentColor"
        cell["style"] = serialize_style_declarations(cleaned)


def render_multiline_text(value):
    text = escape(str(value or ""))
    return text.replace("\n", "<br>")
