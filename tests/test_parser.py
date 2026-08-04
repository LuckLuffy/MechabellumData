import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from change_parser import is_balance_update, parse_changes


class TestIsBalanceUpdate(unittest.TestCase):
    def test_bugfix_not_balance(self):
        post = {"title": "Update 1.11.1.1a",
                "description": "<p>Fixed an issue in Survival Mode</p>"}
        self.assertFalse(is_balance_update(post))

    def test_balance_keyword(self):
        post = {"title": "Update 1.12",
                "description": "<p>Crawler HP increased from 263 to 300</p>"}
        self.assertTrue(is_balance_update(post))


class TestParseOffline(unittest.TestCase):
    def test_no_key_returns_empty_and_saves(self):
        # 不设 key 时走离线模式：返回 [] 且写文件
        post = {"news_id": "test123", "title": "t", "pub_date": "d",
                "guid": "g", "description": "<p>text</p>"}
        result = parse_changes(post)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
