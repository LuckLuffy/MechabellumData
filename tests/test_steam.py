"""测试 steam_fetcher 水位线逻辑，重点防止"首次运行回放历史公告导致数据回退"。"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFindNewPosts(unittest.TestCase):

    @mock.patch("steam_fetcher.fetch_rss")
    @mock.patch("steam_fetcher.get_last_guid", return_value="")
    @mock.patch("steam_fetcher.update_last_guid")
    def test_empty_watermark_initializes_and_does_not_replay(
            self, mock_update, mock_guid, mock_fetch):
        """水位线为空（首次运行）：把水位线设到最新公告，返回 []，绝不回放历史。"""
        from steam_fetcher import find_new_posts
        mock_fetch.return_value = [
            {"guid": "g3", "title": "Update 1.11.1.1a", "pub_date": "d3"},
            {"guid": "g2", "title": "Update 1.11.1", "pub_date": "d2"},
            {"guid": "g1", "title": "Update 1.11.0", "pub_date": "d1"},
        ]
        posts = find_new_posts()
        self.assertEqual(posts, [], "空水位线不应回放任何历史公告")
        mock_update.assert_called_once_with("g3", "Update 1.11.1.1a", "d3")

    @mock.patch("steam_fetcher.fetch_rss")
    @mock.patch("steam_fetcher.get_last_guid", return_value="g2")
    def test_watermark_respects_existing_cursor(self, mock_guid, mock_fetch):
        """水位线已存在：只返回比水位线更新的公告。"""
        from steam_fetcher import find_new_posts
        mock_fetch.return_value = [
            {"guid": "g3", "title": "Update 1.11.1.1a", "pub_date": "d3"},
            {"guid": "g2", "title": "Update 1.11.1", "pub_date": "d2"},
            {"guid": "g1", "title": "Update 1.11.0", "pub_date": "d1"},
        ]
        posts = find_new_posts()
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["guid"], "g3", "只应返回比水位线新的 g3")


if __name__ == "__main__":
    unittest.main()
