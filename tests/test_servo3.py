import os
import re
import importlib.util


import unittest
import time
from robot_hat_mock import Servo

class TestServo(unittest.TestCase):
    def test_servo_angle(self):
        s = Servo("P6")
        s.angle(90)
        self.assertEqual(s.index, "P6")
        #self.assertEqual(s.on_angle_change, 90)

if __name__ == '__main__':
    unittest.main()