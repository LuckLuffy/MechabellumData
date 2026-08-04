# 前后端连接与平衡性监控 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 Python 标准库启动本地服务器（端口 8800），前端加「检查更新」按钮 + 状态条，后端启动时自动检查，平衡性更新自动应用并刷新前端。

**Architecture:** 复用现有 `balance_monitor.py` 检查管线，抽成 `run_check()` 返回结构化结果；`server.py` 用 `http.server.ThreadingHTTPServer` 提供前端静态页 + 5 个 JSON API；变更解析从 Anthropic 切换到 Deepseek 的 Anthropic 兼容端点。

**Tech Stack:** Python 3.12 标准库（`http.server`、`json`、`threading`、`unittest`）、openpyxl（已有）、anthropic SDK（已有，改为指向 Deepseek）、纯 ES5 前端。

## Global Constraints

- 服务器端口固定 `8800`（`config.py` 可配，默认 8800）
- Deepseek base_url 固定 `https://api.deepseek.com/anthropic`，模型固定 `deepseek-v4-flash`
- API key 只存 `.env`（已在 .gitignore），不得硬编码或提交
- 零新增 Python 依赖（不引入 Flask / python-dotenv）
- 前端数据源：优先 `fetch('/api/data')`，失败降级回内嵌 `RAW` 数据（离线双击仍可用）
- 当前阶段只实现「后端启动检查 + 前端手动按钮」；30 天定时器仅预留，不实现
- 测试用 stdlib `unittest`（项目无 pytest），运行 `python -m unittest discover tests`
- 每次任务结束必须提交

---

### Task 1: config.py — 加 .env 加载器与服务器/Deepseek 配置

**Files:**
- Modify: `config.py`

**Interfaces:**
- Produces: `SERVER_PORT: int`, `DEEPSEEK_API_KEY: str`, `DEEPSEEK_BASE_URL: str`, `DEEPSEEK_MODEL: str`；`config._load_env()` 在 import 时已执行，保证后续模块能读到 `.env` 值

- [ ] **Step 1: 写测试**

创建 `tests/test_config.py`：
```python
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest


class TestConfig(unittest.TestCase):
    def test_server_port_default(self):
        import config
        self.assertEqual(config.SERVER_PORT, 8800)

    def test_deepseek_config_exists(self):
        import config
        self.assertTrue(config.DEEPSEEK_BASE_URL.endswith("/anthropic"))
        self.assertEqual(config.DEEPSEEK_MODEL, "deepseek-v4-flash")
        # key 从 .env 读取，能取到即可（不校验内容）
        self.assertIsInstance(config.DEEPSEEK_API_KEY, str)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行确认失败**

Run: `/d/wyq/miniconda3/python.exe -m unittest tests/test_config.py -v`
Expected: FAIL，`AttributeError: module 'config' has no attribute 'SERVER_PORT'`

- [ ] **Step 3: 实现**

在 `config.py` 顶部（`ROOT_DIR` 定义之后、其他配置之前）加入：
```python
def _load_env():
    """从项目根 .env 加载 KEY=VALUE（零依赖）。已存在的环境变量优先。"""
    env_path = os.path.join(ROOT_DIR, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)


_load_env()

# 本地服务器
SERVER_PORT = int(os.environ.get("SERVER_PORT", "8800"))

# Deepseek API（Anthropic 兼容端点）
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/anthropic")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
```

- [ ] **Step 4: 运行确认通过**

Run: `/d/wyq/miniconda3/python.exe -m unittest tests/test_config.py -v`
Expected: PASS（2 个测试）

- [ ] **Step 5: 提交**

```bash
git add config.py tests/test_config.py
git commit -m "feat: add .env loader + server/deepseek config"
```

---

### Task 2: .env — 填入 Deepseek 凭据

**Files:**
- Modify: `.env`（已在 .gitignore，不提交）

- [ ] **Step 1: 追加 Deepseek 配置**

在 `.env` 末尾追加（保留现有 GITHUB_TOKEN 行）：
```
# Deepseek API (Anthropic compatible) — 用真实 key 替换下方占位符
DEEPSEEK_API_KEY=sk-REPLACE_WITH_REAL_KEY
DEEPSEEK_BASE_URL=https://api.deepseek.com/anthropic
DEEPSEEK_MODEL=deepseek-v4-flash
```

- [ ] **Step 2: 验证读取**

Run: `/d/wyq/miniconda3/python.exe -c "import config; print(config.DEEPSEEK_API_KEY[:8]+'...'); print(config.DEEPSEEK_MODEL)"`
Expected: `sk-0d29...` 和 `deepseek-v4-flash`

- [ ] **Step 3: 确认未被 git 跟踪**

Run: `git status --short .env`
Expected: 无输出（已被 .gitignore 排除）

---

### Task 3: change_parser.py — 切换到 Deepseek 解析

**Files:**
- Modify: `change_parser.py`

**Interfaces:**
- Produces: `parse_changes(post: dict) -> list[dict]`；保留别名 `parse_with_claude = parse_changes`（旧调用兼容）。`_resolve_field(field: str) -> str|None` 保留在 balance_monitor 内。

- [ ] **Step 1: 写测试**

创建 `tests/test_parser.py`：
```python
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
```

- [ ] **Step 2: 运行确认失败**

Run: `/d/wyq/miniconda3/python.exe -m unittest tests/test_parser.py -v`
Expected: FAIL，`ImportError: cannot import name 'parse_changes'`

- [ ] **Step 3: 实现**

把 `change_parser.py` 顶部的 Anthropic 配置替换为从 config 读 Deepseek：
```python
from config import COLUMN_MAP, CACHE_DIR, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
```
把 `parse_with_claude` 函数改名为 `parse_changes`，内部使用 Deepseek 客户端：
```python
def parse_changes(post: dict) -> list[dict]:
    """使用 Deepseek（Anthropic 兼容端点）解析公告中的数值变动。"""
    if not DEEPSEEK_API_KEY:
        return _parse_offline(post)

    try:
        import anthropic
        client = anthropic.Anthropic(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )

        text = clean_html(post["description"])
        if len(text) > 8000:
            text = text[:8000] + "\n...[truncated]"

        message = client.messages.create(
            model=DEEPSEEK_MODEL,
            max_tokens=1024,
            system="你是一个游戏数据分析助手。只返回有效的JSON数组。",
            messages=[{
                "role": "user",
                "content": f"{EXTRACTION_PROMPT}\n\n公告内容：\n{text}"
            }]
        )

        response_text = message.content[0].text.strip()
        response_text = re.sub(r'^```json?\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)

        try:
            changes = json.loads(response_text)
            if isinstance(changes, list):
                return changes
        except json.JSONDecodeError:
            print(f"[WARN] Deepseek 返回非JSON格式: {response_text[:200]}")

    except Exception as e:
        print(f"[ERROR] Deepseek API 调用失败: {e}")

    return []


# 旧名兼容
parse_with_claude = parse_changes
```
（`clean_html`、`_parse_offline`、`is_balance_update`、`EXTRACTION_PROMPT`、`format_changes_for_display` 均不变）

- [ ] **Step 4: 运行确认通过**

Run: `/d/wyq/miniconda3/python.exe -m unittest tests/test_parser.py -v`
Expected: PASS（3 个测试）

- [ ] **Step 5: 提交**

```bash
git add change_parser.py tests/test_parser.py
git commit -m "feat: switch change parsing to Deepseek anthropic-compatible endpoint"
```

---

### Task 4: balance_monitor.py — 抽取 run_check() 返回结构化结果

**Files:**
- Modify: `balance_monitor.py`

**Interfaces:**
- Produces: `run_check() -> dict`，返回 `{new_posts:int, balance_posts:int, applied:int, version:str|None, message:str, changes:list}`；`_resolve_field(field:str) -> str|None` 辅助函数。供 Task 5 的 server.py 调用。

- [ ] **Step 1: 写测试**

创建 `tests/test_check.py`：
```python
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
```

- [ ] **Step 2: 运行确认失败**

Run: `/d/wyq/miniconda3/python.exe -m unittest tests/test_check.py -v`
Expected: FAIL，`AttributeError: module 'balance_monitor' has no attribute 'run_check'`

- [ ] **Step 3: 实现**

把 `cmd_check()` 主体抽成 `run_check()`，逻辑不变但返回结构化结果：
```python
def _resolve_field(field: str):
    """把 Deepseek 返回的属性名解析为 Excel 列名。"""
    from config import COLUMN_MAP
    if field in COLUMN_MAP:
        return field
    for cn, en in COLUMN_MAP.items():
        if cn == field or en == field:
            return cn
    return None


def run_check() -> dict:
    """执行完整检查管线，返回结构化结果。"""
    result = {
        "new_posts": 0, "balance_posts": 0, "applied": 0,
        "version": None, "message": "", "changes": [],
    }

    posts = find_new_posts()
    if not posts:
        result["message"] = "无新公告。"
        return result

    result["new_posts"] = len(posts)
    latest_version = get_latest_version(posts) or posts[-1]["title"][:30]
    result["version"] = latest_version

    wb, ws, row_map, col_map = load_workbook()

    for post in posts:
        if not is_balance_update(post):
            continue

        result["balance_posts"] += 1
        changes = parse_changes(post)
        if not changes:
            continue

        applied = 0
        for change in changes:
            unit = change.get("unit", "")
            field = change.get("field", "")
            new_val = change.get("new", "")
            if not unit or not field:
                continue
            field_en = _resolve_field(field)
            if field_en is None:
                continue
            if apply_change(ws, row_map, col_map, unit, field_en, str(new_val)):
                applied += 1

        if applied > 0:
            save_new_sheet(wb, latest_version)
            log_changes(latest_version, post["title"], changes)
            result["applied"] += applied
            result["changes"].extend(changes)

    if posts:
        last = posts[-1]
        update_last_guid(last["guid"], last["title"], last["pub_date"])

    result["message"] = (
        f"应用 {result['applied']} 条变动至版本 {latest_version}。"
        if result["applied"] else "无平衡性数值变动需要更新。"
    )
    return result
```
修改 `cmd_check()` 只调用 `run_check()` 并打印：
```python
def cmd_check():
    """主流程：检查新公告 → 解析 → 更新"""
    result = run_check()
    print(result["message"])
```
更新 `balance_monitor.py` 顶部 import：`parse_with_claude` → `parse_changes`。

- [ ] **Step 4: 运行确认通过**

Run: `/d/wyq/miniconda3/python.exe -m unittest tests/test_check.py -v`
Expected: PASS

- [ ] **Step 5: 手动回归 CLI**

Run: `/d/wyq/miniconda3/python.exe balance_monitor.py`
Expected: 输出 "无新公告。"（缓存已标记到 1.11.1.1a，且无更新）

- [ ] **Step 6: 提交**

```bash
git add balance_monitor.py tests/test_check.py
git commit -m "refactor: extract run_check() returning structured result"
```

---

### Task 5: server.py — HTTP 服务器 + API

**Files:**
- Create: `server.py`

**Interfaces:**
- Consumes: `config.SERVER_PORT`、`config.ROOT_DIR`；`balance_monitor.run_check()`；`steam_fetcher.find_new_posts()`
- Produces: 端口 `8800` 上的 HTTP 服务，端点 `GET /`、`GET /api/status`、`GET /api/data`、`GET /api/changelog`、`POST /api/check`

- [ ] **Step 1: 写测试**

创建 `tests/test_server.py`：
```python
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
```

- [ ] **Step 2: 运行确认失败**

Run: `/d/wyq/miniconda3/python.exe -m unittest tests/test_server.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'server'`

- [ ] **Step 3: 实现**

创建 `server.py`：
```python
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
```

- [ ] **Step 4: 运行确认通过**

Run: `/d/wyq/miniconda3/python.exe -m unittest tests/test_server.py -v`
Expected: PASS（4 个测试）

- [ ] **Step 5: 提交**

```bash
git add server.py tests/test_server.py
git commit -m "feat: add local HTTP server with balance monitoring API"
```

---

### Task 6: 前端 — 加检查按钮 + 状态条 + API 数据源

**Files:**
- Modify: `build_frontend.py`
- Regenerate: `frontend/index.html`

**Interfaces:**
- Consumes: `GET /api/status`、`GET /api/data`、`GET /api/changelog`、`POST /api/check`（Task 5）

- [ ] **Step 1: 修改 build_frontend.py 的工具条 HTML**

在 `<nav class="tabs">` 之后加检查按钮与状态条（在 `.bar` 内）：
```html
<button id="checkBtn" class="check-btn">&#9881; 检查更新</button>
```
在 `header` 内、`.filters` 之后加状态条：
```html
<div class="statusbar" id="statusBar">初始化中…</div>
```
（`switchTab` 不显示/隐藏 statusbar，它常驻）

- [ ] **Step 2: 加按钮与状态条 CSS**

在 `<style>` 内 `.readout` 规则附近追加：
```css
.check-btn{background:var(--accent);color:#1a1206;border:none;border-radius:5px;padding:6px 14px;font:600 13px var(--sans);cursor:pointer;transition:filter .15s}
.check-btn:hover{filter:brightness(1.1)}
.check-btn:disabled{opacity:.5;cursor:wait}
.statusbar{max-width:1440px;margin:0 auto;padding:0 20px 8px;font:11px var(--mono);color:var(--dim);display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.statusbar .ok{color:var(--spd)}.statusbar .warn{color:var(--atk)}.statusbar .err{color:var(--hp)}
```

- [ ] **Step 3: 加前端逻辑 JS**

在 `<script>` 内、`// 初始化` 之前加：
```js
function api(url, opts){
  return fetch(url, opts).then(function(r){ if(!r.ok) throw new Error(r.status); return r.json(); });
}
function setStatus(text, cls){
  var el=document.getElementById('statusBar');
  el.innerHTML='<span class="'+ (cls||'') +'">'+text+'</span>';
}
function refreshData(){
  api('/api/data').then(function(d){
    if(d && d.length){
      UNITS = d.map(function(u){ return {
        name:u.name, size:u["体型"], move:u["移动类型"],
        cost:+u["造价"]||0, hp:+u["单体血量"]||0, speed:+u["移速"]||0,
        atk:+u["单次攻击"]||0, splash:+u["溅射范围"]||0, interval:+u["攻击间隔"]||0,
        range:+u["射程"]||0, count:+u["数量"]||0, slots:+u["占用格子"]||0,
        unlock:isNaN(+u["解锁费用"])?u["解锁费用"]:(+u["解锁费用"]||0),
        _raw:u
      }});
      renderTable(); renderCards();
    }
  }).catch(function(){ /* 离线：保留内嵌 RAW 数据 */ });
}
function refreshStatus(){
  api('/api/status').then(function(s){
    var parts=['上次检查: '+(s.last_title||'无')];
    if(s.has_new) parts.push('<span class="warn">有新公告，点「检查更新」</span>');
    setStatus(parts.join(' · '));
  }).catch(function(){ setStatus('服务器未连接 · 离线模式','warn'); });
}
document.getElementById('checkBtn').addEventListener('click', function(){
  var btn=document.getElementById('checkBtn');
  btn.disabled=true; setStatus('检查中…','warn');
  fetch('/api/check',{method:'POST'}).then(function(r){return r.json();})
    .then(function(res){
      if(res.ok){
        setStatus('['+(res.version||'?')+'] '+res.message, res.applied>0?'ok':'');
        refreshData();
      } else {
        setStatus('检查失败: '+(res.error||'未知错误'),'err');
      }
    }).catch(function(){ setStatus('检查失败: 无法连接服务器','err'); })
    .finally(function(){ btn.disabled=false; });
});
// 每 30 分钟刷新一次状态显示（不触发检查）
setInterval(refreshStatus, 30*60*1000);
refreshStatus();
```
同时把 `// 初始化` 处的 `renderTable();` 后面加一行 `refreshData();`（保留内嵌数据兜底，但优先用服务器最新数据）。

- [ ] **Step 4: 重新生成 index.html 并校验**

Run: `/d/wyq/miniconda3/python.exe build_frontend.py`
再跑：
```bash
/d/wyq/miniconda3/python.exe -c "
import re
html=open(r'frontend/index.html',encoding='utf-8').read()
assert 'checkBtn' in html and 'statusBar' in html and 'refreshData' in html and 'setInterval' in html
m=re.search(r'<script>(.*?)</script>', html, re.DOTALL)
open(r'frontend/_t.js','w',encoding='utf-8').write(m.group(1))
"
node --check frontend/_t.js && rm frontend/_t.js && echo "JS OK"
```
Expected: `JS OK`

- [ ] **Step 5: 提交**

```bash
git add build_frontend.py frontend/index.html
git commit -m "feat: add check button, status bar, and API data source to frontend"
```

---

### Task 7: 端到端验证

- [ ] **Step 1: 启动服务器**

Run: `/d/wyq/miniconda3/python.exe server.py`
Expected: 打印 `Mechabellum 服务器: http://localhost:8800` 和 `[启动检查] 无新公告。`（或对应信息）

- [ ] **Step 2: 验证 API**

Run:
```bash
curl http://localhost:8800/api/status
curl http://localhost:8800/api/data | head -c 200
curl -X POST http://localhost:8800/api/check
```
Expected: status 返回 JSON 含 `last_title`；data 返回数组；check 返回 `{"ok": true, "message": "无新公告。"}`

- [ ] **Step 3: 浏览器验证**

打开 `http://localhost:8800`：
- 页面正常显示 36 单位数据表
- 顶部状态条显示"上次检查: …"
- 点「检查更新」按钮 → 显示"无新公告。"，按钮恢复可用
- 切换标签正常

- [ ] **Step 4: 全部测试回归**

Run: `/d/wyq/miniconda3/python.exe -m unittest discover tests -v`
Expected: 全部 PASS

- [ ] **Step 5: 最终提交**

```bash
git add -A
git commit -m "chore: end-to-end verification"
git config http.proxy "http://127.0.0.1:7897"
git config https.proxy "http://127.0.0.1:7897"
git push
git config --unset http.proxy
git config --unset https.proxy
```
