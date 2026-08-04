import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest import mock

import balance_monitor


class TestRunCheck(unittest.TestCase):
    @mock.patch("balance_monitor.find_new_posts", return_value=[])
    def test_no_new_posts(self, _mock):
        result = balance_monitor.run_check()
        self.assertEqual(result["new_posts"], 0)
        self.assertEqual(result["applied"], 0)
        self.assertIn("无新公告", result["message"])


if __name__ == "__main__":
    unittest.main()
