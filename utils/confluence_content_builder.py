# utils/confluence_content_builder.py

from bs4 import BeautifulSoup
from typing import List, Dict, Tuple, Any
from pathlib import Path

def load_template(template_path: str) -> str:
    """Loads template from file (utility)."""
    path = Path(template_path)
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    with open(path, "r", encoding="utf-8") as file:
        return file.read()

def get_table_from_page(confluence, page_id: str, namespace: str) -> list[Any] | None:
    """Extracts table rows from a Confluence page (utility)."""
    page = confluence.get_page_by_id(page_id, expand='body.storage')
    html_content = page['body']['storage']['value']
    soup = BeautifulSoup(html_content, 'html.parser')
    tables = soup.find_all('table')
    if not tables:
        print("No tables found on page")
        return None
    table = tables[0]
    rows = []
    for row in table.find_all('tr')[1:]:
        tds = row.find_all('td')
        if not tds:
            continue
        first_cell_text = tds[0].text.upper()
        if namespace.upper() not in first_cell_text:
            continue
        cells = [cell for cell in tds[1:]]
        rows.append(cells)
    return rows

def create_xml_table(rows: List) -> str:
    """Builds XML table string (utility)."""
    res = "<table><colgroup> <col/> <col/> <col/> <col/> <col/> <col/> </colgroup><tbody>"
    headers = ['Pod', 'Distribution version', 'Install date', 'Status', 'Resources', 'Java Opts']
    res += "<tr>" + "".join(f"<th><p>{header}</p></th>" for header in headers) + "</tr>"
    for row in rows:
        res += "<tr>" + "".join(str(v) for v in row) + "</tr>"
    res += '</tbody></table>'
    return res

def create_panel_content(sorted_graphics: List[Tuple[str, str]]) -> str:
    """Builds HTML for panels (utility)."""
    panels_html = []
    for panel_name, screenshot_path in sorted_graphics:
        panels_html.append(f"<h3>{panel_name}</h3>")
        filename = Path(screenshot_path).name
        image_macro = f'<br /><ac:image ac:height="400"><ri:attachment ri:filename="{filename}" /></ac:image><br /><br />'
        panels_html.append(image_macro)
    return "".join(panels_html)

def create_service_expand(service_name: str, graphics: Dict[str, str], sorter) -> str:
    """Builds UI expand for a service (utility, depends on sorter util)."""
    sorted_graphics = sorter(graphics)  # Updated to pass sorter as callable if needed
    panels_content = create_panel_content(sorted_graphics)
    return (
        '<ac:structured-macro ac:name="ui-expand" ac:schema-version="1">'
        f'<ac:parameter ac:name="title">{service_name}</ac:parameter>'
        f'<ac:rich-text-body><p>{panels_content}</p></ac:rich-text-body>'
        '</ac:structured-macro>'
    )

def create_metrics_category_macro(category_name: str, services_graphics: Dict[str, Dict[str, str]], sorter) -> str:
    """Builds macro for metrics category (utility)."""
    sorted_services = sorted(services_graphics.items())
    service_expands_html = []
    for service_name, graphics in sorted_services:
        service_macro = create_service_expand(service_name, graphics, sorter)
        service_expands_html.append(service_macro)
    services_content = "".join(service_expands_html)
    return (
        '<ac:structured-macro ac:name="ui-expand" ac:schema-version="1">'
        f'<ac:parameter ac:name="title">{category_name}</ac:parameter>'
        f'<ac:rich-text-body><p>{services_content}</p></ac:rich-text-body>'
        '</ac:structured-macro>'
    )