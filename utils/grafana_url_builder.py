# utils/grafana_url_builder.py

import urllib.parse
from parse_utils import parse_date
from config import config  # Inject config for dynamic params

def build_grafana_url(namespace: str, panel_id: int, container: str, start_time: str, end_time: str, base_url: str) -> str:
    """Builds Grafana URL (utility)."""
    parsed_url = urllib.parse.urlparse(base_url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    updated_params = {
        **query_params,
        'orgId': config.get_value('Grafana_org_id', '1'),
        'refresh': config.get_value('Grafana_refresh', '5s'),
        'from': parse_date(start_time),
        'to': parse_date(end_time),
        'var-namespace': namespace,
        'var-instance': container,
        'panelId': str(panel_id),
        'width': config.get_value('Grafana_panel_width', '1200'),
        'height': config.get_value('Grafana_panel_height', '600'),
        'var-time_interval': config.get_value('Grafana_time_interval', 'default'),
    }
    new_query = urllib.parse.urlencode(updated_params, doseq=True)
    return parsed_url._replace(query=new_query).geturl()