import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os as _os
        import json as _json
        # 保存原始缓存字节，测试结束后恢复，避免污染真实缓存
        cls._cache_path = _os.path.join(
            _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
            "cache", "last_check.json",
        )
        cls._orig_cache = None
        if _os.path.exists(cls._cache_path):
            with open(cls._cache_path, "rb") as _f:
                cls._orig_cache = _f.read()
        # 预置已知缓存，让 last_title 确定性
        _os.makedirs(_os.path.dirname(cls._cache_path), exist_ok=True)
        with open(cls._cache_path, "w", encoding="utf-8") as _f:
            _json.dump({"last_guid": "g", "last_title": "TEST", "last_date": "d"}, _f)
        # 阻断 Steam RSS 网络调用，让 has_new 确定性
        cls._patch = mock.patch("server.find_new_posts", return_value=[])
        cls._patch.start()
        # 用测试端口，避免占用 8800
        server.start(port=8900)

    @classmethod
    def tearDownClass(cls):
        cls._patch.stop()
        server.stop()
        # 恢复原始缓存；若原本不存在则删除测试桩
        if cls._orig_cache is not None:
            with open(cls._cache_path, "wb") as _f:
                _f.write(cls._orig_cache)
        elif os.path.exists(cls._cache_path):
            os.remove(cls._cache_path)

    def test_home(self):
        with urllib.request.urlopen("http://127.0.0.1:8900/") as r:
            body = r.read().decode("utf-8")
            self.assertIn("<html", body)

    def test_api_data(self):
        with urllib.request.urlopen("http://127.0.0.1:8900/api/data") as r:
            data = json.loads(r.read())
            self.assertGreaterEqual(len(data), 30)
            self.assertIn("name", data[0])

    def test_api_status(self):
        with urllib.request.urlopen("http://127.0.0.1:8900/api/status") as r:
            status = json.loads(r.read())
            self.assertEqual(status["last_title"], "TEST")
            self.assertIs(status["has_new"], False)

    def test_api_changelog(self):
        with urllib.request.urlopen("http://127.0.0.1:8900/api/changelog") as r:
            log = json.loads(r.read())
            self.assertIsInstance(log, list)

    def test_api_check(self):
        with mock.patch(
            "server.run_check",
            return_value={"ok": True, "applied": 0, "message": "x", "version": None,
                          "changes": [], "new_posts": 0, "balance_posts": 0},
        ):
            req = urllib.request.Request("http://127.0.0.1:8900/api/check", method="POST")
            with urllib.request.urlopen(req) as r:
                self.assertEqual(r.status, 200)
                body = json.loads(r.read())
                self.assertTrue(body["ok"])

    def test_404(self):
        try:
            urllib.request.urlopen("http://127.0.0.1:8900/api/nope")
            self.fail("expected 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)


if __name__ == "__main__":
    unittest.main()
