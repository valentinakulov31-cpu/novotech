import re
from collections import OrderedDict

from django.utils.html import escape


_FULL_TABLE_RE = re.compile(r"<table(?P<attrs>[^>]*)>(?P<body>.*?)</table>", flags=re.IGNORECASE | re.DOTALL)


def parse_html_attrs(attrs_text: str) -> dict[str, str]:
    return {match.group("name").lower(): match.group("value") for match in re.finditer(r'(?P<name>[\w:-]+)\s*=\s*"(?P<value>[^"]*)"', attrs_text)}


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


def serialize_html_attrs(attrs: dict[str, str]) -> str:
    return "".join(f' {key}="{escape(value)}"' for key, value in attrs.items())


def sanitize_catalog_tables(html: str | None) -> str | None:
    if not html:
        return html

    def normalize_table(match: re.Match) -> str:
        attrs = parse_html_attrs(match.group("attrs"))
        body = match.group("body")
        styles = parse_style_declarations(attrs.get("style"))
        border_style = styles.get("border-style")
        is_catalog = border_style == "var(--catalog-table-border-style)"
        is_regular_border = bool(border_style and attrs.get("border") == "1") or attrs.get("data-catalog-table") == "1"

        if not is_catalog and not is_regular_border:
            return match.group(0)

        attrs.pop("border", None)
        attrs.pop("cellpadding", None)
        attrs.pop("cellspacing", None)

        if is_catalog:
            attrs["data-catalog-table"] = "1"
            attrs["style"] = merge_style_declarations(
                attrs.get("style"),
                {
                    "width": "100%",
                    "background-color": "white",
                    "border-collapse": "collapse",
                    "font-size": "14px",
                },
            )
            body_html = _rewrite_table_cells(body, mode="catalog", border_style="solid")
        else:
            attrs.pop("data-catalog-table", None)
            attrs["style"] = strip_style_declarations(
                attrs.get("style"),
                {
                    "background-color": "white",
                    "font-size": "14px",
                    "margin": "16px 0",
                },
            )
            attrs["style"] = merge_style_declarations(
                attrs.get("style"),
                {"border-width": styles.get("border-width") or "1px"},
            )
            body_html = _rewrite_table_cells(body, mode="regular", border_style=border_style)

        return f"<table{serialize_html_attrs(attrs)}>{body_html}</table>"

    return _FULL_TABLE_RE.sub(normalize_table, html)


def _rewrite_table_cells(body_html: str, *, mode: str, border_style: str) -> str:
    def replace_row(row_match: re.Match) -> str:
        row_open = row_match.group("open")
        row_inner = row_match.group("inner")
        cell_index = 0

        def replace_cell(cell_match: re.Match) -> str:
            nonlocal cell_index
            cell_index += 1
            tag_name = cell_match.group("tag")
            attrs = parse_html_attrs(cell_match.group("attrs"))
            content = cell_match.group("content")
            styles = parse_style_declarations(attrs.get("style"))

            if mode == "catalog":
                enforced = OrderedDict()
                if "width" in styles:
                    enforced["width"] = styles["width"].replace("100.033%", "100%")
                enforced["padding"] = "12px"
                enforced["border"] = "1px solid #e1e1e1"
                enforced["text-align"] = "left" if cell_index == 1 else "center"
                attrs["style"] = serialize_style_declarations(enforced)
            else:
                cleaned = OrderedDict()
                if "width" in styles:
                    cleaned["width"] = styles["width"].replace("100.033%", "100%")
                cleaned["border"] = f"1px {border_style} currentColor"
                attrs["style"] = serialize_style_declarations(cleaned)

            return f"<{tag_name}{serialize_html_attrs(attrs)}>{content}</{tag_name}>"

        new_inner = re.sub(
            r"<(?P<tag>t[dh])(?P<attrs>[^>]*)>(?P<content>.*?)</(?P=tag)>",
            replace_cell,
            row_inner,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return f"<tr{row_open}>{new_inner}</tr>"

    return re.sub(
        r"<tr(?P<open>[^>]*)>(?P<inner>.*?)</tr>",
        replace_row,
        body_html,
        flags=re.IGNORECASE | re.DOTALL,
    )


def render_multiline_text(value):
    text = escape(str(value or ""))
    return text.replace("\n", "<br>")
