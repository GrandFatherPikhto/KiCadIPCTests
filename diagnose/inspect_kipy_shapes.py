# inspect_kipy.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import kipy.board_types as bt
import kipy.board as b

print("=== Доступные классы в kipy.board_types ===")
for name in dir(bt):
    if not name.startswith('_'):
        print(f"  {name}")

print("\n=== Доступные методы у Board ===")
for name in dir(b.Board):
    if not name.startswith('_'):
        print(f"  {name}")