"""Mechabellum 平衡性监控系统 - 配置文件"""
import os

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Steam RSS
STEAM_APP_ID = "669330"
RSS_URL = f"https://store.steampowered.com/feeds/news/app/{STEAM_APP_ID}/"
STEAM_NEWS_PAGE = f"https://store.steampowered.com/news/app/{STEAM_APP_ID}/view/"

# 基准数据表
BASELINE_XLSX = os.path.join(ROOT_DIR, "钢铁指挥官兵种单位数据表7.29.xlsx")

# 输出目录
OUTPUT_DIR = os.path.join(ROOT_DIR, "outputs")
OUTPUT_PREFIX = "unit_data_v"

# 缓存
CACHE_DIR = os.path.join(ROOT_DIR, "cache")
LAST_CHECK_FILE = os.path.join(CACHE_DIR, "last_check.json")
CHANGE_LOG_FILE = os.path.join(CACHE_DIR, "change_log.json")

# 列名映射（Excel列名 → 内部字段名）
COLUMN_MAP = {
    "兵种名称": "name",
    "造价": "cost",
    "单体血量": "hp",
    "移速": "speed",
    "单次攻击": "atk",
    "溅射范围": "splash",
    "攻击间隔": "interval",
    "射程": "range",
    "对空": "anti_air",
    "数量": "count",
    "占用格子": "slots",
    "解锁费用": "unlock_cost",
    "伤害血量": "damage_hp",
    "升级经验要求": "upgrade_exp",
    "提供经验": "exp_reward",
}

# 反向映射
FIELD_TO_COLUMN = {v: k for k, v in COLUMN_MAP.items()}

# 平衡性关键词（中英文）
BALANCE_KEYWORDS = [
    "平衡", "balance",
    "加强", "buff", "increased", "increase",
    "削弱", "nerf", "decreased", "decrease", "reduced", "reduce",
    "调整", "adjust", "adjusted", "changed", "change",
    "HP", "health", "damage", "伤害", "血量", "生命",
    "费用", "cost", "supply",
    "移速", "速度", "speed",
    "射程", "range",
    "攻击间隔", "attack interval",
    "溅射", "splash",
    "重制", "remake", "rework",
    "属性", "stats", "stat",
]

# HTTP 请求头
HEADERS = {
    "User-Agent": "MechabellumData/1.0 (Balance Monitor)"
}

# 代理配置（如需要）
PROXY = None  # {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
