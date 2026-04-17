import os
import re
import importlib.util

import unittest
import time

# Dynamisch die neueste Version laden
import HardwareDeLuebs as module
set_punkte = module.set_punkte
Player = module.Player

class TestSetPunkteReal(unittest.TestCase):

    def setUp(self):
        self.player = Player()
        self.welcherSchuss = 0
        self.feuer = 5
        self.key = 42
        self.referenzzeit = time.monotonic()

    def test_standard(self):
        set_punkte(self.player, self.welcherSchuss, self.feuer, self.referenzzeit, self.key)
        self.assertEqual(self.player.treffer[self.welcherSchuss], self.key)
        self.assertAlmostEqual(self.player.restzeit_zyklus[self.welcherSchuss], self.feuer, delta=0.05)
        self.assertEqual(self.player.punkte_zyklus, 1)
        self.assertGreaterEqual(self.player.speedpunkte_zyklus, 0.0)

    def test_mit_multiplier(self):
        self.player.punkte_zyklus = 1
        set_punkte(self.player, 1, self.feuer, self.referenzzeit, 99, multiplier=3)
        self.assertEqual(self.player.punkte_zyklus, 4)  # 1 von vorher + 3 jetzt
        self.assertEqual(self.player.treffer[1], 99)

if __name__ == '__main__':
    unittest.main()
    