"""
Mechabellum Unit Data Extractor
从游戏内存中直接提取所有单位的 MechData 和 CardData 属性值

用法：
1. 启动 Mechabellum 到主菜单（不需要进战斗）
2. 运行此脚本：python extract_unit_data.py
3. 数据输出到 unit_data_from_memory.json
"""

import pymem
import pymem.process
import struct
import json
import sys
import os
from typing import Optional

# ============================================================
# 已知的字段偏移（从 dump.cs + Il2CppDumper 解析）
# ============================================================

# MechData : ClientConfigData (TypeDefIndex: 12406)
MECHDATA_LIFE = 0x38          # int - HP
MECHDATA_DAMAGE = 0x3C        # int - ATK
MECHDATA_MOVESPEED = 0x40     # int - 速度
MECHDATA_ISFLY = 0x44         # bool
MECHDATA_ATTACK_ANGLE = 0x48  # FPoint (long)
MECHDATA_ROTATE_SPEED = 0x50  # FPoint (long)
MECHDATA_MAIN_SKILL_ID = 0x60 # int
MECHDATA_MECH_TYPE = 0x64     # int (0=Small, 1=Medium, 2=Huge)
MECHDATA_MOVE_TYPE = 0x68     # int (0=Normal, 1=Underground, 2=Cloak)
MECHDATA_ATTACK_STRENGTH = 0x90 # int
MECHDATA_RADIUS = 0xA0        # FPoint (long)

# CardData : ItemData : ConfigData (TypeDefIndex: 12323)
CARDDATA_BASE_MONEY = 0x58       # int - 购买费用
CARDDATA_MAINTENANCE = 0x5C      # int - 维护费
CARDDATA_MECH_ID = 0x80          # int - 单位ID
CARDDATA_MECH_COUNT = 0x84       # int - 每队数量
CARDDATA_SLOT_SIZE = 0x88        # int - 部署槽大小
CARDDATA_UNLOCK_PRICE = 0xA0     # int - 解锁费
CARDDATA_SPECIAL_UNIT = 0xC0     # int
CARDDATA_IS_TEST_UNIT = 0xC4     # bool

# ConfigDataContainer (TypeDefIndex: 12346)
CONTAINER_CARDDATAS = 0x60   # List<CardData>
CONTAINER_MECHDATAS = 0x68   # List<MechData>
CONTAINER_ATTR_UPGRADE = 0x80 # List<AttributeUpgradeData>

# Unity IL2CPP List<T> 结构
LIST_ITEMS = 0x00   # T[] 数组指针
LIST_SIZE = 0x10    # int32 元素数量
LIST_VERSION = 0x14 # int32

# 一些已知单位的基础属性（用于验证定位是否正确）
KNOWN_UNITS = {
    # life, damage, moveSpeed
    'Crawler': (277, 79, 16),
    'Fang': (117, 61, 6),
    'Arclight': (4414, 391, 7),
}

class MemoryReader:
    def __init__(self):
        self.pm: Optional[pymem.Pymem] = None
        self.ga_base = 0

    def attach(self):
        try:
            self.pm = pymem.Pymem("Mechabellum.exe")
            print(f"[OK] 已连接 Mechabellum.exe (PID: {self.pm.process_id})")
            for mod in self.pm.list_modules():
                if mod.name.lower() == 'gameassembly.dll':
                    self.ga_base = mod.lpBaseOfDll
                    print(f"[OK] GameAssembly.dll @ 0x{self.ga_base:X}")
                    return True
            print("[FAIL] 找不到 GameAssembly.dll")
            return False
        except pymem.exception.ProcessNotFound:
            print("[FAIL] 找不到游戏进程，请先启动游戏")
            return False

    def read_ptr(self, addr):
        if addr == 0:
            return 0
        return struct.unpack('<Q', self.pm.read_bytes(addr, 8))[0]

    def read_int(self, addr):
        if addr == 0:
            return 0
        return struct.unpack('<i', self.pm.read_bytes(addr, 4))[0]

    def read_long(self, addr):
        if addr == 0:
            return 0
        return struct.unpack('<q', self.pm.read_bytes(addr, 8))[0]

    def read_bytes(self, addr, size):
        return self.pm.read_bytes(addr, size)

    def is_valid_ptr(self, addr):
        """检查地址是否为有效指针（在合理范围内）"""
        if addr == 0:
            return False
        # GameAssembly 通常在 0x180000000 范围内（Windows 64-bit）
        return 0x10000 < addr < 0x7FFFFFFFFFFF

    def read_mech_data(self, addr):
        """从地址读取 MechData 结构"""
        if not self.is_valid_ptr(addr):
            return None
        try:
            return {
                'life': self.read_int(addr + MECHDATA_LIFE),
                'damage': self.read_int(addr + MECHDATA_DAMAGE),
                'moveSpeed': self.read_int(addr + MECHDATA_MOVESPEED),
                'isFly': self.read_int(addr + MECHDATA_ISFLY) != 0,
                'attackAngle': self.read_long(addr + MECHDATA_ATTACK_ANGLE),
                'rotateSpeed': self.read_long(addr + MECHDATA_ROTATE_SPEED),
                'mainSkillID': self.read_int(addr + MECHDATA_MAIN_SKILL_ID),
                'mechType': self.read_int(addr + MECHDATA_MECH_TYPE),
                'moveType': self.read_int(addr + MECHDATA_MOVE_TYPE),
                'attackStrength': self.read_int(addr + MECHDATA_ATTACK_STRENGTH),
            }
        except:
            return None

    def read_card_data(self, addr):
        """从地址读取 CardData 结构"""
        if not self.is_valid_ptr(addr):
            return None
        try:
            return {
                'baseMoney': self.read_int(addr + CARDDATA_BASE_MONEY),
                'maintenanceSupply': self.read_int(addr + CARDDATA_MAINTENANCE),
                'mechID': self.read_int(addr + CARDDATA_MECH_ID),
                'mechCount': self.read_int(addr + CARDDATA_MECH_COUNT),
                'slotSize': self.read_int(addr + CARDDATA_SLOT_SIZE),
                'unlockPrice': self.read_int(addr + CARDDATA_UNLOCK_PRICE),
                'specialUnit': self.read_int(addr + CARDDATA_SPECIAL_UNIT),
                'isTestUnit': self.read_int(addr + CARDDATA_IS_TEST_UNIT) != 0,
            }
        except:
            return None

    def read_list(self, list_addr):
        """读取 IL2CPP List<T> 中的所有指针"""
        if not self.is_valid_ptr(list_addr):
            return []
        try:
            items_ptr = self.read_ptr(list_addr + LIST_ITEMS)
            size = self.read_int(list_addr + LIST_SIZE)

            if not self.is_valid_ptr(items_ptr) or size <= 0 or size > 200:
                return []

            ptrs = []
            for i in range(size):
                ptr = self.read_ptr(items_ptr + i * 8)
                if self.is_valid_ptr(ptr):
                    ptrs.append(ptr)
            return ptrs
        except:
            return []

    def find_mech_data_list(self):
        """
        查找 ConfigDataContainer 中的 mechDatas 列表。

        策略：扫描已提交的内存区域，寻找符合以下条件的 List<MechData>：
        1. 包含 15-50 个元素
        2. 每个元素指向的地址具有合理的 MechData 字段值
        3. life、damage、moveSpeed 在小正整数范围内
        4. mechType 为 0/1/2
        """
        print("\n[*] 扫描内存中... 这可能需要 1-2 分钟...")

        # 获取进程的内存区域
        regions = []
        try:
            # 获取所有已提交的内存区域
            mbi = self.pm.process_base
            # 简化：扫描 GameAssembly 附近的主要堆区域
            # Windows 64-bit IL2CPP 一般在 0x180000000 区域
            # 以及默认堆区域
            scan_ranges = [
                # GameAssembly.dll 自身
                (self.ga_base, self.ga_base + 0x10000000),  # 256MB after DLL
                # .data/.bss segment after DLL
                (self.ga_base + 0x4000000, self.ga_base + 0x8000000),
            ]
        except:
            scan_ranges = [(0x180000000, 0x1A0000000)]

        candidates = []
        bytes_scanned = 0

        for start, end in scan_ranges:
            # Jump by alignment
            for addr in range(start, min(end, start + 0x10000000), 8):
                bytes_scanned += 8
                if bytes_scanned % (10 * 1024 * 1024) == 0:
                    print(f"  [*] 已扫描 {bytes_scanned / (1024*1024):.0f} MB...", end='\r')

                try:
                    # 尝试读取为 List<T>: items_ptr + size
                    items_ptr = self.read_ptr(addr)
                    size = self.read_int(addr + 0x10)

                    if not (15 <= size <= 50):
                        continue

                    if not self.is_valid_ptr(items_ptr):
                        continue

                    # 检查第一个元素是否是有效的 MechData 指针
                    first_ptr = self.read_ptr(items_ptr)
                    if not self.is_valid_ptr(first_ptr):
                        continue

                    # 验证第一个元素是否像 MechData
                    life = self.read_int(first_ptr + MECHDATA_LIFE)
                    damage = self.read_int(first_ptr + MECHDATA_DAMAGE)
                    speed = self.read_int(first_ptr + MECHDATA_MOVESPEED)
                    mech_type = self.read_int(first_ptr + MECHDATA_MECH_TYPE)

                    # 合理性验证：已知的 MechData 值范围
                    if not (50 < life < 200000):
                        continue
                    if not (10 < damage < 20000):
                        continue
                    if not (1 < speed < 20):
                        continue
                    if mech_type not in (0, 1, 2):
                        continue

                    # 检查第二个元素
                    second_ptr = self.read_ptr(items_ptr + 8)
                    if self.is_valid_ptr(second_ptr):
                        life2 = self.read_int(second_ptr + MECHDATA_LIFE)
                        damage2 = self.read_int(second_ptr + MECHDATA_DAMAGE)
                        speed2 = self.read_int(second_ptr + MECHDATA_MOVESPEED)
                        if not (50 < life2 < 200000 and 10 < damage2 < 20000 and 1 < speed2 < 20):
                            continue

                    # 找到了！验证是否有已知的单位值
                    for unit_name, (exp_life, exp_dmg, exp_spd) in KNOWN_UNITS.items():
                        if life == exp_life and damage == exp_dmg and speed == exp_spd:
                            print(f"\n[FOUND] 匹配 {unit_name}: life={life}, damage={damage}, speed={speed}")
                            print(f"  List @ 0x{addr:X}, items @ 0x{items_ptr:X}, size={size}")
                            return items_ptr, size

                    candidates.append((addr, items_ptr, size, life, damage, speed))

                except pymem.exception.MemoryReadError:
                    continue
                except:
                    continue

        print(f"\n[*] 扫描了 {bytes_scanned / (1024*1024):.0f} MB")

        # 如果没有精确匹配已知值，使用最佳候选
        if candidates:
            print(f"\n[*] 找到 {len(candidates)} 个候选，使用第一个...")
            addr, items_ptr, size, life, dmg, spd = candidates[0]
            print(f"  List @ 0x{addr:X}, size={size}")
            print(f"  首个单位: life={life}, damage={dmg}, speed={spd}")
            return items_ptr, size

        return None, 0


def main():
    print("=" * 60)
    print("Mechabellum 单位数据提取器 v2")
    print("从游戏内存直接读取 MechData / CardData")
    print("=" * 60)

    reader = MemoryReader()
    if not reader.attach():
        print("\n请启动游戏后重试。")
        return

    # 查找 mechDatas 列表
    items_ptr, size = reader.find_mech_data_list()

    if items_ptr is None:
        print("\n[FAIL] 未能定位单位数据列表。")
        print("请确保：")
        print("  1. 游戏已完全加载（到主菜单即可）")
        print("  2. 以管理员权限运行此脚本")
        print("  3. 尝试进训练模式后再次运行")
        return

    print(f"\n=== 找到 {size} 个单位 ===")

    # 读取所有 MechData
    units = []
    for i in range(size):
        ptr = reader.read_ptr(items_ptr + i * 8)
        if ptr == 0:
            continue

        mech = reader.read_mech_data(ptr)
        if mech is None:
            continue

        mech['_ptr'] = f'0x{ptr:X}'
        mech['_index'] = i

        # 输出到控制台
        mech_type_str = ['Small', 'Medium', 'Huge'][mech['mechType']] if 0 <= mech['mechType'] <= 2 else str(mech['mechType'])
        move_type_str = ['Normal', 'Underground', 'Cloak'][mech['moveType']] if 0 <= mech['moveType'] <= 2 else str(mech['moveType'])
        fly_str = '✈飞' if mech['isFly'] else '地'

        print(f"  [{i:2d}] HP={mech['life']:>7d}  ATK={mech['damage']:>6d}  "
              f"Speed={mech['moveSpeed']:>2d}  {fly_str}  "
              f"Type={mech_type_str}  Move={move_type_str}  "
              f"SkillID={mech['mainSkillID']}")

        units.append(mech)

    # 输出 JSON
    output_path = os.path.join(os.path.dirname(__file__), 'unit_data_from_memory.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(units, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] 数据已保存到: {output_path}")
    print(f"      共 {len(units)} 个单位")


if __name__ == '__main__':
    main()
