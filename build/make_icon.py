"""assets/app.ico'yu amblemden uretir (ui.app_icon)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import ui  # noqa: E402

os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
ui.app_icon(256).save(os.path.join(ROOT, "assets", "app.ico"),
                      sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (256, 256)])
print("assets/app.ico")
