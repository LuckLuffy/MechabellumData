import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import balance_monitor
from config import BASELINE_XLSX


class TestRunCheck(unittest.TestCase):
    @mock.patch("balance_monitor.find_new_posts", return_value=[])
    def test_no_new_posts(self, _mock):
        result = balance_monitor.run_check()
        self.assertEqual(result["new_posts"], 0)
        self.assertEqual(result["applied"], 0)
        self.assertIn("无新公告", result["message"])


class TestRunCheckLock(unittest.TestCase):
    def test_lock_is_threading_lock(self):
        # threading.Lock 是工厂函数而非类型，用 type(threading.Lock()) 取锁的类型
        self.assertIsInstance(balance_monitor._run_lock, type(threading.Lock()))

    def test_lock_serializes_run_check(self):
        # 持有锁时 run_check 必须阻塞，释放后才执行 _run_check_locked
        entered = threading.Event()

        def fake_impl():
            entered.set()

        with mock.patch.object(balance_monitor, "_run_check_locked", fake_impl):
            lock = balance_monitor._run_lock
            lock.acquire()
            try:
                t = threading.Thread(target=balance_monitor.run_check)
                t.start()
                time.sleep(0.1)
                self.assertFalse(
                    entered.is_set(),
                    "_run_check_locked 不应在锁仍被持有时执行",
                )
            finally:
                lock.release()
            t.join(timeout=5)
            self.assertTrue(entered.is_set(), "释放锁后 _run_check_locked 应执行")
            self.assertFalse(t.is_alive())


class TestRunCheckExport(unittest.TestCase):
    """应用变更后应重新导出 frontend/unit_data.json，让 /api/data 反映新版本。"""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        # 输出目录与导出目标都重定向到临时目录，避免污染真实 outputs/ 与 frontend/
        self._out_patcher = mock.patch("sheet_updater.OUTPUT_DIR", self._tmp)
        self._out_patcher.start()
        self._json_path = os.path.join(self._tmp, "unit_data.json")
        self._json_patcher = mock.patch("convert_to_json.OUTPUT_PATH", self._json_path)
        self._json_patcher.start()
        self.addCleanup(self._json_patcher.stop)
        self.addCleanup(self._out_patcher.stop)
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        # 模拟 --init：复制基准表作为初始版本
        shutil.copy2(BASELINE_XLSX, os.path.join(self._tmp, "unit_data_vbaseline.xlsx"))

    def test_applied_changes_reach_json(self):
        post = {
            "title": "Update 1.12 Balance",
            "description": "<p>Crawler HP increased to 300</p>",
            "guid": "g-bal",
            "news_id": "bal",
            "pub_date": "2026-08-04",
        }
        changes = [{"unit": "爬虫", "field": "单体血量", "new": "300"}]
        with mock.patch("balance_monitor.find_new_posts", return_value=[post]), \
             mock.patch("balance_monitor.is_balance_update", return_value=True), \
             mock.patch("balance_monitor.parse_changes", return_value=changes), \
             mock.patch("balance_monitor.get_latest_version", return_value="1.12"), \
             mock.patch("balance_monitor.update_last_guid"), \
             mock.patch("balance_monitor.log_changes"):
            result = balance_monitor.run_check()

        self.assertEqual(result["applied"], 1)
        self.assertTrue(os.path.exists(self._json_path), "run_check 应导出 JSON")
        with open(self._json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        crawler = next(u for u in data if u["name"] == "爬虫")
        self.assertEqual(crawler["单体血量"], 300)

    def test_parse_failure_does_not_advance_cache(self):
        # 平衡帖解析失败（None）：不应用、不导出、不推进 last_guid，以便下次重试
        post = {
            "title": "Update 1.12 Balance",
            "description": "<p>Crawler HP changed</p>",
            "guid": "g-fail",
            "news_id": "fail",
            "pub_date": "2026-08-04",
        }
        with mock.patch("balance_monitor.find_new_posts", return_value=[post]), \
             mock.patch("balance_monitor.is_balance_update", return_value=True), \
             mock.patch("balance_monitor.parse_changes", return_value=None), \
             mock.patch("balance_monitor.get_latest_version", return_value="1.12"), \
             mock.patch("balance_monitor.update_last_guid") as mock_update:
            result = balance_monitor.run_check()

        self.assertEqual(result["applied"], 0)
        mock_update.assert_not_called()
        self.assertFalse(os.path.exists(self._json_path))


if __name__ == "__main__":
    unittest.main()
