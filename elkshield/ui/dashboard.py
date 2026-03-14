"""
Control UI Module — GUI unified.
Launch ELKShield desktop dashboard (PySide6). User: Run system → Start Monitoring.
"""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run_gui():
    """Launch the unified dashboard (run_simulation_app)."""
    # Import and run the main app window (single codebase at root)
    import run_simulation_app
    if hasattr(run_simulation_app, "HAS_QT") and run_simulation_app.HAS_QT:
        from PySide6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        win = run_simulation_app.SimulationAppQt()
        win.setWindowTitle("ELKShield Unified Security Platform")
        win.show()
        sys.exit(app.exec())
    else:
        print("Cần cài PySide6: pip install PySide6")
        sys.exit(1)
