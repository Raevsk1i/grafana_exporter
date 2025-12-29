# utils/confluence_graphics_sorter.py

from typing import List, Dict, Tuple

ALL_METRICS_ORDER = [
    'cpu-usage-percent', 'cpu-usage-limit-(millicores)', 'cpu-throttled-(millicores)',
    'ram-usage-percent', 'ram-usage-limit-(bytes)', 'disk-total-avail-used-(bytes)',
    'disk-read-write-(bytes)', 'disk-read-write-(ops)', 'traffic-in-out-(bytes)',
    'heap-(bytes)', 'heap-per-pool-(bytes)', 'nonHeap-per-pool-(bytes)',
    'metaspace-(bytes)', 'gc-collection-count-time', 'threads-count'
]

def sort_graphics_by_order(graphics: Dict[str, str]) -> List[Tuple[str, str]]:
    """Sorts graphics by predefined order (utility)."""
    sorted_graphics = []
    remaining_graphics = list(graphics.items())
    for metric_name in ALL_METRICS_ORDER:
        matched_graphics = [(panel_name, path) for panel_name, path in remaining_graphics if metric_name in panel_name.lower()]
        sorted_graphics.extend(matched_graphics)
        for graphic in matched_graphics:
            if graphic in remaining_graphics:
                remaining_graphics.remove(graphic)
    remaining_graphics.sort(key=lambda x: x[0].lower())
    sorted_graphics.extend(remaining_graphics)
    return sorted_graphics

def categorize_graphics(graphics: Dict[str, Dict[str, str]]) -> Tuple[Dict, Dict]:
    """Categorizes graphics into system and software metrics (utility)."""
    system_metrics = {}
    software_metrics = {}
    software_keywords = ['heap', 'metaspace', 'gc', 'jvm', 'thread', 'class', 'compilation']
    for container, container_graphics in graphics.items():
        system_metrics[container] = {}
        software_metrics[container] = {}
        for panel_name, screenshot_path in container_graphics.items():
            if any(keyword in panel_name.lower() for keyword in software_keywords):
                software_metrics[container][panel_name] = screenshot_path
            else:
                system_metrics[container][panel_name] = screenshot_path
    return system_metrics, software_metrics