"""
AssetRipper 自动化提取脚本
通过 AssetRipper Web API 加载游戏文件并导出单位数据
AssetRipper 需已启动: AssetRipper.GUI.Free.exe --headless --port 51234
"""
import requests
import json
import os
import sys
import time

BASE_URL = "http://127.0.0.1:51234"
GAME_DIR = r"D:\wyq\steam\steamapps\common\Mechabellum\Mechabellum_Data"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "ripper_output")

def api_post(endpoint, data=None):
    try:
        r = requests.post(f"{BASE_URL}{endpoint}", data=data, timeout=10)
        return r.status_code, r.text
    except Exception as e:
        return -1, str(e)

def api_get(endpoint):
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        return r.status_code, r.text
    except Exception as e:
        return -1, str(e)

def main():
    print("=" * 60)
    print("AssetRipper 自动化提取")
    print("=" * 60)

    # 1. Reset
    print("\n[1/4] Reset...")
    code, _ = api_post("/Reset")
    if code not in (200, 302, 204):
        print(f"  Reset failed (code={code}) - continuing anyway")
    time.sleep(2)

    # 2. Load the common_assets_all bundle
    bundle = os.path.join(GAME_DIR,
        "StreamingAssets", "aa", "StandaloneWindows64",
        "common_assets_all_366492f37928e10bd0ba30335849ec77.bundle")
    print(f"[2/4] Loading bundle...")
    print(f"  File: {os.path.basename(bundle)}")
    print(f"  Size: {os.path.getsize(bundle)/1024/1024:.0f} MB")

    code, resp = api_post("/LoadFile", {"path": bundle})
    if code == 200:
        print("  Load request sent OK")
    else:
        print(f"  Load returned code={code}")
        print(f"  Response: {resp[:200]}")

    # Wait for processing
    print("  Waiting for processing (up to 60s)...")
    for i in range(60):
        time.sleep(1)
        if i % 10 == 0:
            print(f"    {i}s...", end='\r')
    print("    done waiting.")

    # 3. Check what we got
    print("\n[3/4] Checking loaded assets...")
    code, resp = api_get("/Resources/Data")
    if code == 200 and resp:
        try:
            data = json.loads(resp)
            print(f"  Resources loaded: {len(data) if isinstance(data, list) else 'object'}")
            if isinstance(data, list) and len(data) > 0:
                print(f"  First entry: {json.dumps(data[0], indent=2)[:300]}")
        except:
            print(f"  Raw response: {resp[:500]}")

    # 4. Export primary content
    print(f"\n[4/4] Exporting Primary Content to:\n  {OUTPUT_DIR}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # The export API needs the path form data
    code, resp = api_post("/Export/PrimaryContent", {"path": OUTPUT_DIR})
    if code == 200:
        print("  Export started OK")
    else:
        print(f"  Export returned code={code}: {resp[:200]}")
        # Fallback: try Unity Project export
        print("  Trying Unity Project export instead...")
        code, resp = api_post("/Export/UnityProject", {"path": OUTPUT_DIR})
        print(f"  Export returned code={code}")

    # 5. Wait and check output
    print("\nWaiting for export files...")
    for i in range(30):
        time.sleep(2)
        if os.path.exists(OUTPUT_DIR):
            files = []
            for root, dirs, filenames in os.walk(OUTPUT_DIR):
                for f in filenames:
                    files.append(os.path.join(root, f))
                    if len(files) >= 20:
                        break
            if files:
                print(f"  Found {len(files)} files so far...")
                for f in files[:10]:
                    print(f"    {f}")
                break
        print(f"    waiting {i*2}s...", end='\r')

    print(f"\nDone. Output in: {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
