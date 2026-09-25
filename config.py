"""Mechabellum 平衡性监控系统 - 配置文件"""
import os
import sys


def _get_root_dir():
    """解析项目根目录。

    PyInstaller 冻结时 __file__ 指向临时解压目录，须用 exe 所在目录作为
    可写的数据根目录（缓存/输出/前端资源都落在 exe 旁）。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


# 项目根目录
ROOT_DIR = _get_root_dir()


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

# Steam RSS
STEAM_APP_ID = "669330"
RSS_URL = f"https://store.steampowered.com/feeds/news/app/{STEAM_APP_ID}/"
STEAM_NEWS_PAGE = f"https://store.steampowered.com/news/app/{STEAM_APP_ID}/view/"

# 基准数据表
BASELINE_XLSX = os.path.join(ROOT_DIR, "钢铁指挥官兵种数据9.25.xlsx")

# 输出目录
OUTPUT_DIR = os.path.join(ROOT_DIR, "outputs")
OUTPUT_PREFIX = "unit_data_v"

# 缓存
CACHE_DIR = os.path.join(ROOT_DIR, "cache")
LAST_CHECK_FILE = os.path.join(CACHE_DIR, "last_check.json")
CHANGE_LOG_FILE = os.path.join(CACHE_DIR, "change_log.json")

# 列名映射（Excel列名 → 内部字段名）
# 2026-09 新表结构：表内只存「攻击力 + 弹药量」等原始值，
# 对单输出/爆发峰值/对单DPS 由 convert_to_json 推算，不是表内列。
# 已下线的列：对单输出、爆发峰值、对单DPS、占用格子、伤害血量、升级经验要求、提供经验
COLUMN_MAP = {
    "兵种名称": "name",
    "造价": "cost",
    "单体血量": "hp",
    "移速": "speed",
    "攻击力": "atk",
    "弹药量": "ammo",
    "溅射范围": "splash",
    "攻击间隔": "interval",
    "射程": "range",
    "对空": "anti_air",
    "数量": "count",
    "解锁费用": "unlock_cost",
}

# 反向映射
FIELD_TO_COLUMN = {v: k for k, v in COLUMN_MAP.items()}

# 公告属性名 → 表内列名。Deepseek 返回的属性名与表内列名常有出入
# （公告写「单次攻击」，表内叫「攻击力」），不归一化会在 apply_change 里被
# 当成未知列名静默跳过。
FIELD_ALIASES = {
    "单次攻击": "攻击力",
    "单发伤害": "攻击力",
    "攻击": "攻击力",
    "攻击力": "攻击力",
    "弹药数": "弹药量",
    "弹药": "弹药量",
    "武器数": "弹药量",
    "单体血量": "单体血量",
    "血量": "单体血量",
    "生命": "单体血量",
    "生命值": "单体血量",
    "移速": "移速",
    "速度": "移速",
    "移动速度": "移速",
    "造价": "造价",
    "费用": "造价",
    "价格": "造价",
    "攻击间隔": "攻击间隔",
    "间隔": "攻击间隔",
    "攻速": "攻击间隔",
    "溅射范围": "溅射范围",
    "溅射": "溅射范围",
    "射程": "射程",
    "对空": "对空",
    "数量": "数量",
    "解锁费用": "解锁费用",
    "解锁": "解锁费用",
}

# 公告里的派生字段：表内没有对应列，不能直接写入（值口径是 攻击力×弹药量），
# 只登记到变更日志供人工复核，不静默丢弃。
DERIVED_FIELDS = {"对单输出", "爆发峰值", "对单DPS", "总DPS"}

# 公告单位名 → 表内单位名。游戏内译名与表内译名不一致，不映射会 [SKIP] 未知单位。
UNIT_ALIASES = {
    "漩涡": "磁暴",
    "虚空之眼": "魔眼",
}

# 测试服公告不写入正式数据（测试服数值经常不上线）
TEST_SERVER_MARKER = "[Test Server]"

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
