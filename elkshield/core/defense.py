"""
Defense Engine — Rule suggestion, auto response (SOAR direction).
IF brute force → suggest block IP; defense_recommendations.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def get_recommendations(attack_type="unknown", severity="high"):
    """Get defense recommendations for attack type (rule suggestion)."""
    try:
        from scripts.defense_recommendations import get_recommendations as _get
        return _get(attack_type, severity)
    except ImportError:
        from defense_recommendations import get_recommendations as _get
        return _get(attack_type, severity)


def add_recommendations_to_dataframe(df):
    """Add defense_recommendations column to DataFrame."""
    try:
        from scripts.defense_recommendations import add_recommendations_to_dataframe as _add
        return _add(df)
    except ImportError:
        from defense_recommendations import add_recommendations_to_dataframe as _add
        return _add(df)


def format_recommendations_text(attack_type="unknown", severity="high"):
    """Format recommendations as text (for UI)."""
    try:
        from scripts.defense_recommendations import format_recommendations_text as _fmt
        return _fmt(attack_type, severity)
    except ImportError:
        from defense_recommendations import format_recommendations_text as _fmt
        return _fmt(attack_type, severity)
