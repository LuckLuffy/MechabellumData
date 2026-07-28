"""Scan running game memory for ConfigDataContainer and dump all unit stats."""
import pymem, struct, ctypes, json, os
from ctypes import wintypes

pm = pymem.Pymem("Mechabellum.exe")
handle = pm.process_handle
print(f"PID: {pm.process_id}")

def read_safe(addr, size):
    try: return pm.read_bytes(addr, size)
    except: return None

# Find GameAssembly base
ga_base = 0
for mod in pm.list_modules():
    if mod.name.lower() == 'gameassembly.dll':
        ga_base = mod.lpBaseOfDll
        break
print(f"GameAssembly.dll @ 0x{ga_base:X}")

# Target heap regions (found from previous scan)
heap_regions = [
    (0x0000019500000000, 0x0000019509000000),
    (0x0000019600900000, 0x000001960B900000),
    (0x0000019760000000, 0x000001976B8AB000),
    (0x00000196E0000000, 0x00000196EB007000),
    (0x00000197A0000000, 0x00000197AAC00000),
    (0x0000019680000000, 0x0000019690000000),
    (0x0000019620000000, 0x0000019630000000),
    (0x0000019639F00000, 0x0000019649F00000),
    (0x00000195E0000000, 0x00000195EF000000),
]

print("Scanning heap for ConfigDataContainer...")
found = False

for base, end in heap_regions:
    if found: break
    total = (end - base)
    scanned = 0
    for addr in range(base, end, 8):
        scanned += 8
        if scanned % (50*1024*1024) == 0:
            print(f"  {base:016X}: {scanned/total*100:.0f}%", end='\r')

        try:
            data = read_safe(addr, 0x170)
            if data is None: continue

            # Read mechDatas List at offset 0x68
            mech_items = struct.unpack_from('<Q', data, 0x68)[0]
            mech_size = struct.unpack_from('<i', data, 0x70)[0]
            mech_ver = struct.unpack_from('<i', data, 0x74)[0]

            # cardDatas List at offset 0x60
            card_items = struct.unpack_from('<Q', data, 0x60)[0]
            card_size = struct.unpack_from('<i', data, 0x68)[0]

            # Validate
            if not (15 <= mech_size <= 80): continue
            if not (15 <= card_size <= 80): continue
            if not (0 <= mech_ver <= 200): continue
            if not (0x19500000000 <= mech_items <= 0x19A00000000): continue
            if not (0x19500000000 <= card_items <= 0x19A00000000): continue

            # Count valid-looking list pointers in the structure
            valid = 0
            for off in range(0x20, 0x150, 8):
                p = struct.unpack_from('<Q', data, off)[0]
                if p == 0 or (0x19500000000 <= p <= 0x19A00000000):
                    valid += 1
            if valid < 8: continue

            # Verify first MechData entry
            md0_data = read_safe(mech_items, 8)
            if md0_data is None: continue
            md0 = struct.unpack_from('<Q', md0_data, 0)[0]
            if not (0x19500000000 <= md0 <= 0x19A00000000): continue

            md0_bytes = read_safe(md0, 0xA8)
            if md0_bytes is None: continue
            life = struct.unpack_from('<i', md0_bytes, 0x38)[0]
            damage = struct.unpack_from('<i', md0_bytes, 0x3C)[0]
            speed = struct.unpack_from('<i', md0_bytes, 0x40)[0]
            mtype = struct.unpack_from('<i', md0_bytes, 0x64)[0]

            if not (50 < life < 200000): continue
            if not (5 < damage < 30000): continue
            if not (1 < speed <= 20): continue
            if mtype not in (0, 1, 2): continue

            # FOUND!
            print(f"\n\n[FOUND!] ConfigDataContainer @ 0x{addr:X}")
            print(f"  mechDatas: items=0x{mech_items:X}, size={mech_size}")
            print(f"  cardDatas: items=0x{card_items:X}, size={card_size}")

            # --- DUMP ALL MECH DATA ---
            units = []
            print(f"\n{'='*80}")
            print(f"MechData ({mech_size} units)")
            print(f"{'='*80}")
            print(f"{'#':>3s} {'HP':>8s} {'ATK':>7s} {'SPD':>3s} {'AIR':>3s} {'Type':>7s} {'Move':>12s} {'Skill':>6s} {'AtkStr':>6s} {'Radius':>8s}")
            print("-"*80)

            for i in range(mech_size):
                ptr_data = read_safe(mech_items + i*8, 8)
                if ptr_data is None: continue
                ptr = struct.unpack_from('<Q', ptr_data, 0)[0]
                if ptr == 0: continue

                md = read_safe(ptr, 0xA8)
                if md is None: continue

                life = struct.unpack_from('<i', md, 0x38)[0]
                damage = struct.unpack_from('<i', md, 0x3C)[0]
                speed = struct.unpack_from('<i', md, 0x40)[0]
                is_fly = struct.unpack_from('<i', md, 0x44)[0] != 0
                skill = struct.unpack_from('<i', md, 0x60)[0]
                mtype = struct.unpack_from('<i', md, 0x64)[0]
                mvtype = struct.unpack_from('<i', md, 0x68)[0]
                atk_str = struct.unpack_from('<i', md, 0x90)[0]
                radius_raw = struct.unpack_from('<q', md, 0xA0)[0]

                type_s = ['Small', 'Medium', 'Huge'][mtype] if mtype < 3 else f'?{mtype}'
                move_s = ['Normal', 'Underground', 'Cloak'][mvtype] if mvtype < 3 else f'?{mvtype}'
                fly_s = 'YES' if is_fly else 'no'

                print(f"{i:3d} {life:8d} {damage:7d} {speed:3d} {fly_s:3s} "
                      f"{type_s:7s} {move_s:12s} {skill:6d} {atk_str:6d} "
                      f"{radius_raw/10000:8.2f}")

                units.append({
                    'index': i, 'life': life, 'damage': damage, 'moveSpeed': speed,
                    'isFly': is_fly, 'mechType': mtype, 'moveType': mvtype,
                    'mainSkillID': skill, 'attackStrength': atk_str,
                    'radius': radius_raw, 'ptr': f'0x{ptr:X}'
                })

            # --- DUMP ALL CARD DATA ---
            cards = []
            print(f"\n{'='*80}")
            print(f"CardData ({card_size} units)")
            print(f"{'='*80}")
            print(f"{'#':>3s} {'ID':>5s} {'Cost':>6s} {'Cnt':>4s} {'Slot':>4s} {'Unlock':>7s} {'Upkeep':>7s} {'Special':>7s}")
            print("-"*80)

            for i in range(card_size):
                ptr_data = read_safe(card_items + i*8, 8)
                if ptr_data is None: continue
                ptr = struct.unpack_from('<Q', ptr_data, 0)[0]
                if ptr == 0: continue

                cd = read_safe(ptr, 0xF8)
                if cd is None: continue

                money = struct.unpack_from('<i', cd, 0x58)[0]
                upkeep = struct.unpack_from('<i', cd, 0x5C)[0]
                mech_id = struct.unpack_from('<i', cd, 0x80)[0]
                count = struct.unpack_from('<i', cd, 0x84)[0]
                slot = struct.unpack_from('<i', cd, 0x88)[0]
                unlock = struct.unpack_from('<i', cd, 0xA0)[0]
                special = struct.unpack_from('<i', cd, 0xC0)[0]

                print(f"{i:3d} {mech_id:5d} {money:6d} {count:4d} {slot:4d} "
                      f"{unlock:7d} {upkeep:7d} {special:7d}")

                cards.append({
                    'index': i, 'mechID': mech_id, 'baseMoney': money,
                    'mechCount': count, 'slotSize': slot, 'unlockPrice': unlock,
                    'maintenanceSupply': upkeep, 'specialUnit': special,
                    'ptr': f'0x{ptr:X}'
                })

            # Save to JSON
            out = {'mechDatas': units, 'cardDatas': cards,
                   'configDataContainer': f'0x{addr:X}'}
            out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'unit_data_from_memory.json')
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(out, f, indent=2, ensure_ascii=False)
            print(f"\n[OK] Saved to {out_path}")

            found = True
            break
        except:
            continue

if not found:
    print("\n[FAIL] Not found. Try:")
    print("  1. Enter a practice/training match")
    print("  2. Deploy at least 1 unit")
    print("  3. Re-run this script")
