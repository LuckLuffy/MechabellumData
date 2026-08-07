# MechabellumData

钢铁指挥官兵种数据监控项目：Steam 公告 → Deepseek 解析 → 数据表 → 静态前端（Netlify / GitHub Pages）。

> 项目方向：**云端更新 + 网页展示**。exe 打包已于 2026-08-05 退役，源码归档在 `local/exe_packaging/`（不提交、不再维护）。

## 上下文纪律（重要 —— 避免「上下文超过 1M」报错）

本项目大文件多、会话易膨胀。务必遵守：

1. **生成文件禁止整读**：`frontend/index.html`、`web/index.html`、`frontend/unit_data.json(.js)` 是脚本产物（单文件内嵌完整数据集，约 40KB）。改前端先读源模板 `build_frontend.py`；查具体内容用 Grep 定向搜索。
2. **git diff 优先 `--stat` 或限定单文件**，别把生成文件几十 KB 的 diff 整段留在会话里。
3. **探索用子代理**（Agent / Explore），主会话只收结论。
4. **长会话及时 `/compact`**；独立任务开新会话，别长期复用。

## 构建管线（生成文件由脚本重生成，勿手改）

- `convert_to_json.py`：Excel → `frontend/unit_data.json(.js)`
- `build_frontend.py`：`unit_data.json` → `frontend/index.html`（local 模式，含 API 按钮）
- `build_web.py`：→ `web/index.html` + `web/updated_at.txt`（web 模式，纯静态）
- 每周一 CI（`.github/workflows/update.yml`）自动更新数据并重新生成 web/，Netlify 监听 push 自动部署
