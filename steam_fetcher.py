"""Steam RSS 公告抓取模块"""
import xml.etree.ElementTree as ET
import requests
import json
import os
import re
from datetime import datetime
from config import RSS_URL, HEADERS, PROXY, CACHE_DIR, LAST_CHECK_FILE


def ensure_cache():
    """确保缓存目录和文件存在"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    if not os.path.exists(LAST_CHECK_FILE):
        with open(LAST_CHECK_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_guid": "", "last_title": "", "last_date": ""}, f)


def get_last_guid() -> str:
    """获取上次检查的最新帖子 GUID"""
    ensure_cache()
    with open(LAST_CHECK_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("last_guid", "")


def update_last_guid(guid: str, title: str, date: str):
    """更新缓存中的最新 GUID"""
    ensure_cache()
    with open(LAST_CHECK_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_guid": guid, "last_title": title, "last_date": date}, f)


def fetch_rss() -> list[dict]:
    """抓取 Steam RSS，返回帖子列表 (按时间从旧到新)"""
    try:
        resp = requests.get(RSS_URL, headers=HEADERS, proxies=PROXY, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] 无法连接 Steam RSS: {e}")
        return []

    root = ET.fromstring(resp.content)
    items = []
    for item in root.findall(".//item"):
        title = item.find("title").text or ""
        desc = item.find("description").text or ""
        guid = item.find("guid").text or ""
        pub_date = item.find("pubDate").text or ""

        # 从 guid 提取新闻ID (格式: .../view/687511450598508333)
        news_id = ""
        match = re.search(r"/view/(\d+)", guid)
        if match:
            news_id = match.group(1)

        items.append({
            "title": title,
            "description": desc,
            "guid": guid,
            "news_id": news_id,
            "pub_date": pub_date,
        })

    return items


def find_new_posts() -> list[dict]:
    """查找上次检查后发布的新帖"""
    items = fetch_rss()
    if not items:
        return []

    last_guid = get_last_guid()
    new_posts = []

    # RSS 按时间倒序，遍历找到上次 guid 为止
    for item in items:
        if item["guid"] == last_guid:
            break
        new_posts.append(item)

    # 返回按时间顺序（旧到新）
    new_posts.reverse()
    return new_posts


def get_latest_version(items: list[dict]) -> str:
    """从公告标题中提取最新版本号"""
    for item in items:
        # 匹配 "Update X.X.X" 或 "X.X.X" 版本号
        match = re.search(r"(\d+\.\d+(?:\.\d+(?:\.\d+)?)?[a-z]?)", item["title"])
        if match:
            return match.group(1)
    return ""


if __name__ == "__main__":
    ensure_cache()
    posts = find_new_posts()
    if posts:
        print(f"发现 {len(posts)} 条新公告:")
        for p in posts:
            print(f"  [{p['guid'][-30:]}] {p['title']}")
    else:
        print("无新公告。")
