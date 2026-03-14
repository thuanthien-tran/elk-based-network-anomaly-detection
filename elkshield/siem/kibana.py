"""
SIEM Integration — Kibana: open dashboard, discover (alerts), management.
"""
import webbrowser

KIBANA_BASE = "http://localhost:5601"


def open_kibana():
    """Open Kibana home."""
    webbrowser.open(KIBANA_BASE)


def open_discover_alerts(index_pattern="ml-alerts"):
    """Open Kibana Discover with alert index."""
    webbrowser.open("%s/app/discover#/?_a=(index:%s)" % (KIBANA_BASE, index_pattern))


def open_management():
    """Open Kibana Stack Management → Index Management."""
    webbrowser.open("%s/app/management/data/index_management/indices" % KIBANA_BASE)
