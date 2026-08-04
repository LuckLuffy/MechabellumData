import json
import os
import sys
import threading
import unittest
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 用测试端口，避免占用 8800
        server.start(port=8900)

    @classmethod
    def tearDownClass(cls):
        server.stop()

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
            self.assertIn("last_title", status)

    def test_api_changelog(self):
        with urllib.request.urlopen("http://127.0.0.1:8900/api/changelog") as r:
            log = json.loads(r.read())
            self.assertIsInstance(log, list)


if __name__ == "__main__":
    unittest.main()
