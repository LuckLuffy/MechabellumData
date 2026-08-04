#!/usr/bin/env python3
"""Mechabellum 本地服务器 — 前端 + 平衡性监控 API。

用法：
  python server.py            # 启动，端口 8800，启动时自动检查一次
  python server.py 8900       # 指定端口
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ROOT_DIR, SERVER_PORT
from steam_fetcher import find_new_posts
from balance_monitor import run_check

FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
INDEX_PATH = os.path.join(FRONTEND_DIR, "index.html")
DATA_PATH = os.path.join(FRONTEND_DIR, "unit_data.json")
CHANGELOG_PATH = os.path.join(ROOT_DIR, "cache", "change_log.json")

_server = None


def _read_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # 静默日志

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self):
        with open(INDEX_PATH, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            self._send_html()
        elif path == "/api/status":
            status = _read_json(os.path.join(ROOT_DIR, "cache", "last_check.json"), {})
            try:
                posts = find_new_posts()
                has_new = len(posts) > 0
            except Exception:
                has_new = False
            status["has_new"] = has_new
            self._send_json(status)
        elif path == "/api/data":
            self._send_json(_read_json(DATA_PATH, []))
        elif path == "/api/changelog":
            self._send_json(_read_json(CHANGELOG_PATH, []))
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/check":
            try:
                result = run_check()
                self._send_json({"ok": True, **result})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
        else:
            self._send_json({"error": "not found"}, 404)


def start(port=None):
    """启动服务器（可测试用指定端口）。返回已启动的 server 对象。"""
    global _server
    port = port or SERVER_PORT
    _server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=_server.serve_forever, daemon=True)
    thread.start()

    # 启动时自动检查一次（后台线程，不阻塞）
    def _startup_check():
        try:
            result = run_check()
            print(f"[启动检查] {result['message']}")
        except Exception as e:
            print(f"[启动检查] 失败: {e}")

    threading.Thread(target=_startup_check, daemon=True).start()
    return _server


def stop():
    """停止服务器（测试用）。"""
    global _server
    if _server:
        _server.shutdown()
        _server.server_close()
        _server = None


if __name__ == "__main__":
    port = SERVER_PORT
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    print(f"Mechabellum 服务器: http://localhost:{port}")
    print("按 Ctrl+C 停止")
    start(port=port)
    try:
        while True:
            import time
            time.sleep(3600)
    except KeyboardInterrupt:
        stop()
