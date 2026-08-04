"""平衡性变更解析模块 — 关键词检测 + Deepseek（Anthropic 兼容端点）结构化提取"""
import json
import os
import re
import html as html_mod
from config import COLUMN_MAP, CACHE_DIR, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

PARSED_DIR = os.path.join(CACHE_DIR, "parsed_posts")

EXTRACTION_PROMPT = """从以下 Mechabellum 更新公告中，提取所有兵种数值变动。

返回纯净JSON数组（不要markdown代码块），每个变动一个对象：
[{"unit": "中文单位名", "field": "属性名", "old": 旧值或null, "new": "新值或描述"}]

属性名限定为：造价 单体血量 移速 单次攻击 溅射范围 攻击间隔 射程 对空 数量 占用格子 解锁费用

规则：
- 单位名必须用中文（如爬虫、弧光、尖牙、台风、火神、沙虫等）
- 数值变动可能是绝对值（"263"→"300"）或相对值（"+30%"/"-15%"）
- 新增单位或科技不要提取，只提取已有基础属性的变更
- 如果公告没有数值变动，返回空数组[]
- 不要编造数据，只提取公告中明确提到的数值"""


def is_balance_update(post: dict) -> bool:
    """判断公告是否涉及平衡性调整"""
    title = post.get("title", "")
    # 提取纯文本
    text = html_mod.unescape(post.get("description", ""))
    text = re.sub(r"<[^>]+>", " ", text)
    combined = (title + " " + text).lower()

    # 必须包含平衡相关的强信号词，避免 bugfix 误判
    strong_signals = [
        "balance", "平衡",
        "buff", "加强", "increas",
        "nerf", "削弱", "decreas", "reduc",
        "adjust", "调整",
        "remake", "重制", "rework",
        "hp", "health", "生命", "血量",
        "damage", "伤害", "atk",
        "cost", "费用",
        "speed", "速度",
        "attribute", "属性",
        "stat", "stats",
    ]
    for kw in strong_signals:
        if kw.lower() in combined:
            return True
    return False


def clean_html(html_str: str) -> str:
    """HTML → 可读纯文本（保留结构信息）"""
    text = html_mod.unescape(html_str)
    # 保留标题标记
    text = re.sub(r'<div class="bb_h1"><b>(.*?)</b></div>', r'\n## \1\n', text)
    # 列表项
    text = re.sub(r'<li>\s*<p class="bb_paragraph">(.*?)</p>\s*</li>', r'- \1\n', text, flags=re.DOTALL)
    # 段落
    text = re.sub(r'<p class="bb_paragraph">(.*?)</p>', r'\1\n', text, flags=re.DOTALL)
    # 其他标签
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    # 清理空白
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text


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

        response_text = "".join(
            getattr(block, "text", "") or ""
            for block in message.content
        ).strip()
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


def _parse_offline(post: dict) -> list[dict]:
    """离线模式：保存公告文本供后续分析"""
    os.makedirs(PARSED_DIR, exist_ok=True)
    news_id = post.get("news_id", "unknown")
    text = clean_html(post["description"])
    filename = os.path.join(PARSED_DIR, f"{news_id}.txt")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"标题：{post['title']}\n")
        f.write(f"日期：{post['pub_date']}\n")
        f.write(f"URL：{post['guid']}\n")
        f.write(f"{'='*60}\n\n")
        f.write(text)
        f.write(f"\n\n{'='*60}\n")
        f.write("请将以上公告中的数值变动提取为JSON，格式参考 change_parser.py 中的 EXTRACTION_PROMPT。")

    print(f"[INFO] 公告已保存到 {filename}（离线模式 - 需手动分析）")
    return []


def format_changes_for_display(changes: list[dict]) -> str:
    """格式化变更列表供人类阅读"""
    if not changes:
        return "无平衡性数值变动。"
    lines = []
    for c in changes:
        unit = c.get("unit", "?")
        field = c.get("field", "?")
        old = c.get("old", "?")
        new = c.get("new", "?")
        lines.append(f"  {unit} | {field}: {old} → {new}")
    return "\n".join(lines)


if __name__ == "__main__":
    # 测试：解析一段示例公告
    test_post = {
        "title": "Update 1.12: Balance Adjustments",
        "description": '<div class="bb_h1"><b>Balance</b></div>'
                       '<ul class="bb_ul"><li><p class="bb_paragraph">'
                       'Crawler HP increased from 263 to 300</p></li>'
                       '<li><p class="bb_paragraph">'
                       'Fang attack decreased by 10%</p></li></ul>',
        "guid": "test123",
        "news_id": "test",
        "pub_date": "2026-07-29",
    }
    print(f"Balance update: {is_balance_update(test_post)}")
    changes = parse_with_claude(test_post)
    print(f"Changes: {json.dumps(changes, ensure_ascii=False, indent=2)}")
