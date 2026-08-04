import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    @mock.patch("change_parser.DEEPSEEK_API_KEY", "")
    def test_no_key_returns_empty_and_saves(self):
        # 不设 key 时走离线模式：返回 [] 且写文件（写入临时目录，测试后清理）
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        post = {"news_id": "test123", "title": "t", "pub_date": "d",
                "guid": "g", "description": "<p>text</p>"}
        with mock.patch("change_parser.PARSED_DIR", tmp):
            result = parse_changes(post)
            self.assertEqual(result, [])
            self.assertTrue(os.path.exists(os.path.join(tmp, "test123.txt")))


class TestParseApi(unittest.TestCase):
    """DEEPSEEK_API_KEY 配置时的解析行为：成功返回 list，失败返回 None。"""

    POST = {"news_id": "test123", "title": "t", "pub_date": "d",
            "guid": "g", "description": "<p>Crawler HP to 300</p>"}

    def _patch_client(self, content_text=None, side_effect=None):
        """构造 mock 的 anthropic.Anthropic，返回 patch 上下文管理器。"""
        import anthropic
        fake_client = mock.MagicMock()
        if content_text is not None:
            fake_client.messages.create.return_value = mock.MagicMock(
                content=[mock.MagicMock(text=content_text)])
        if side_effect is not None:
            fake_client.messages.create.side_effect = side_effect
        return mock.patch.object(anthropic, "Anthropic", return_value=fake_client)

    @mock.patch("change_parser.DEEPSEEK_API_KEY", "sk-test")
    def test_api_returns_list(self):
        with self._patch_client(content_text='[{"unit":"爬虫","field":"单体血量","new":"300"}]'):
            result = parse_changes(self.POST)
        self.assertEqual(result, [{"unit": "爬虫", "field": "单体血量", "new": "300"}])

    @mock.patch("change_parser.DEEPSEEK_API_KEY", "sk-test")
    def test_api_empty_array_is_not_failure(self):
        # 公告确实无数值变动：API 成功返回 []，不算失败
        with self._patch_client(content_text="[]"):
            result = parse_changes(self.POST)
        self.assertEqual(result, [])

    @mock.patch("change_parser.DEEPSEEK_API_KEY", "sk-test")
    def test_api_non_json_returns_none(self):
        with self._patch_client(content_text="not json at all"):
            self.assertIsNone(parse_changes(self.POST))

    @mock.patch("change_parser.DEEPSEEK_API_KEY", "sk-test")
    def test_api_non_list_json_returns_none(self):
        with self._patch_client(content_text='{"a": 1}'):
            self.assertIsNone(parse_changes(self.POST))

    @mock.patch("change_parser.DEEPSEEK_API_KEY", "sk-test")
    def test_api_exception_returns_none(self):
        with self._patch_client(side_effect=RuntimeError("boom")):
            self.assertIsNone(parse_changes(self.POST))


if __name__ == "__main__":
    unittest.main()
