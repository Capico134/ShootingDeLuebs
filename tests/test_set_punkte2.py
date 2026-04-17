# Datei: tests/test_set_punkte2.py

import unittest
import time
#from HardwareDeLuebs_v1_9_5 import set_punkte
#import LoadModule
#HD = LoadModule.import_latest_module('HardwareDeLuebs')
import HardwareDeLuebs as HD

class DummyPlayer:
    def __init__(self):
        self.treffer = [None] * 3
        self.restzeit_zyklus = [0.0] * 3
        self.punkte_zyklus = 0
        self.speedpunkte_zyklus = 0.0

class TestSetPunkte(unittest.TestCase):

    def setUp(self):
        self.player = DummyPlayer()
        self.feuer = 5
        self.key = 42
        self.welcherSchuss = 0
        self.referenzzeit = time.monotonic()  # aktuelle Zeit

    def test_standardwert(self):
        HD.set_punkte(self.player, self.welcherSchuss, self.feuer, self.referenzzeit, self.key)
        self.assertEqual(self.player.treffer[self.welcherSchuss], self.key)
        self.assertAlmostEqual(self.player.restzeit_zyklus[self.welcherSchuss], self.feuer, delta=0.05)
        self.assertEqual(self.player.punkte_zyklus, 1)
        self.assertGreaterEqual(self.player.speedpunkte_zyklus, 0.0)

    def test_mit_multiplier(self):
        HD.set_punkte(self.player, 1, self.feuer, self.referenzzeit, 99, multiplier=3)
        self.assertEqual(self.player.punkte_zyklus, 3)
        self.assertEqual(self.player.treffer[1], 99)

    def test_negative_restzeit(self):
        alte_zeit = self.referenzzeit - 10  # simuliert stark verzögerten Schuss
        HD.set_punkte(self.player, 2, self.feuer, alte_zeit, 77)
        self.assertEqual(self.player.treffer[2], 77)
        self.assertLessEqual(self.player.restzeit_zyklus[2], 0)
        self.assertEqual(self.player.punkte_zyklus, 1)
        self.assertEqual(self.player.speedpunkte_zyklus, 0.0)

if __name__ == '__main__':
    unittest.main()
