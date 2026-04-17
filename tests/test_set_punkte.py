import os
import sys
import unittest

# 1. Den übergeordneten Ordner (wo deine HardwareDeLuebs.py liegt) zum Pfad hinzufügen
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# 2. Ganz sauberer, statischer Import
import HardwareDeLuebs as module

# 3. Zuweisung der Funktion für deine Tests
set_punkte = module.set_punkte
