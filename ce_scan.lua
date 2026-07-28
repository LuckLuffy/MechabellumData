-- ============================================================
-- Mechabellum 单位数据自动提取脚本 v1.0
-- 用于 Cheat Engine 7.5
-- 基于 Il2CppDumper 解析的游戏数据结构偏移
-- ============================================================

-- MechData 结构偏移 (TypeDefIndex: 12406)
local OFF_LIFE        = 0x38  -- int 生命值
local OFF_DAMAGE      = 0x3C  -- int 攻击力
local OFF_MOVESPEED   = 0x40  -- int 移动速度
local OFF_ISFLY       = 0x44  -- bool 是否飞行 (int32)
local OFF_ATTACKANGLE = 0x48  -- FPoint (long)
local OFF_ROTATESPEED = 0x50  -- FPoint (long)
local OFF_MAINSKILLID = 0x60  -- int
local OFF_MECHTYPE    = 0x64  -- int 0=Small 1=Medium 2=Huge
local OFF_MOVETYPE    = 0x68  -- int 0=Normal 1=Underground 2=Cloak
local OFF_ATTACKSTR   = 0x90  -- int 对建筑攻击强度
local OFF_RADIUS      = 0xA0  -- FPoint (long)

-- CardData 结构偏移 (TypeDefIndex: 12323)
local OFF_BASEMONEY   = 0x58  -- int 费用
local OFF_MAINTENANCE = 0x5C  -- int 维护费
local OFF_MECHID      = 0x80  -- int 单位ID
local OFF_MECHCOUNT   = 0x84  -- int 每队数量
local OFF_SLOTSIZE    = 0x88  -- int 槽位大小
local OFF_UNLOCKPRICE = 0xA0  -- int 解锁费
local OFF_SPECIALUNIT = 0xC0  -- int 特殊单位标记

-- ConfigDataContainer 偏移 (TypeDefIndex: 12346)
local OFF_CARDDATAS   = 0x60  -- List&lt;CardData&gt;
local OFF_MECHDATAS   = 0x68  -- List&lt;MechData&gt;

-- Crawler 当前版本属性 (用于特征码扫描)
local CRAWLER_LIFE   = 263
local CRAWLER_DAMAGE = 79
local CRAWLER_SPEED  = 16

-- ============================================================
-- 辅助函数
-- ============================================================

-- 读取64位指针
local function ReadPtr(addr)
  if addr == 0 then return 0 end
  return readQword(addr)
end

-- 安全读取 (出错返回0)
local function SafeReadPtr(addr)
  local ok, result = pcall(readQword, addr)
  if ok then return result else return 0 end
end

local function SafeReadInt(addr)
  local ok, result = pcall(readInteger, addr)
  if ok then return result else return 0 end
end

-- ============================================================
-- 主扫描逻辑
-- ============================================================

function ScanForUnitData()

  -- 1. 确认游戏进程
  local proc = process
  if proc == nil or proc == '' then
    showMessage('请先附加到 Mechabellum.exe 进程！')
    return
  end

  -- 2. 获取 GameAssembly.dll 基址
  local ga_base = getAddress('GameAssembly.dll')
  if ga_base == nil then
    showMessage('找不到 GameAssembly.dll，请确认游戏已加载到主菜单或战斗中。')
    return
  end
  print(string.format('GameAssembly.dll @ 0x%X', ga_base))

  -- 3. 构造 Crawler 特征码：life, damage, speed, isFly 作为连续 4 个 int32
  --    用十六进制通配符 ? 处理大小端
  local life_hex = string.format('%02X %02X %02X %02X',
    CRAWLER_LIFE % 256, math.floor(CRAWLER_LIFE / 256) % 256,
    math.floor(CRAWLER_LIFE / 65536) % 256, math.floor(CRAWLER_LIFE / 16777216))
  local dmg_hex = string.format('%02X %02X %02X %02X',
    CRAWLER_DAMAGE % 256, math.floor(CRAWLER_DAMAGE / 256) % 256,
    math.floor(CRAWLER_DAMAGE / 65536) % 256, math.floor(CRAWLER_DAMAGE / 16777216))
  local spd_hex = string.format('%02X %02X %02X %02X',
    CRAWLER_SPEED % 256, math.floor(CRAWLER_SPEED / 256) % 256,
    math.floor(CRAWLER_SPEED / 65536) % 256, math.floor(CRAWLER_SPEED / 16777216))

  local aob = life_hex .. ' ' .. dmg_hex .. ' ' .. spd_hex .. ' 00 00 00 00'
  print('特征码: ' .. aob)
  print('正在扫描内存 (AOB)... 这可能需要30秒...')

  -- 4. AOB 扫描
  local results = AOBScan(aob, '+W+X', 1, '0')
  if results == nil or #results == 0 then
    showMessage('未找到 Crawler 数据。\n请进入训练模式部署一个 Crawler 后重新执行。')
    return
  end

  print(string.format('找到 %d 个匹配地址', #results))

  -- 5. 验证每个匹配地址，找到真正的 MechData
  local mechDataPtrs = {}
  for _, r in ipairs(results) do
    local match_addr = tonumber(r, 16)
    -- life 在 MechData+0x38，所以 MechData 基址 = match_addr - 0x38
    local md_base = match_addr - OFF_LIFE

    -- 验证其他字段是否合理
    local mtype = SafeReadInt(md_base + OFF_MECHTYPE)
    local mvtype = SafeReadInt(md_base + OFF_MOVETYPE)
    local atkstr = SafeReadInt(md_base + OFF_ATTACKSTR)

    if mtype >= 0 and mtype <= 2 and mvtype >= 0 and mvtype <= 2 and atkstr >= 0 and atkstr <= 30 then
      print(string.format('  有效 MechData @ 0x%X (type=%d, move=%d)', md_base, mtype, mvtype))
      table.insert(mechDataPtrs, md_base)
    end
  end

  if #mechDataPtrs == 0 then
    showMessage('找到匹配地址但验证失败。\n请确保 Crawler 已部署（非升级状态）。')
    return
  end

  -- 6. 从 MechData 指针反查 mechDatas 列表
  --    搜索内存中包含该指针的数组区域
  local mech_items_ptr = nil
  local mech_size = 0

  -- 用第一个有效的 MechData 指针搜索
  local target_ptr = mechDataPtrs[1]
  local ptr_bytes = string.format('%02X %02X %02X %02X %02X %02X %02X %02X',
    target_ptr % 256, math.floor(target_ptr / 256) % 256,
    math.floor(target_ptr / 65536) % 256, math.floor(target_ptr / 16777216) % 256,
    math.floor(target_ptr / 4294967296) % 256, math.floor(target_ptr / 1099511627776) % 256,
    math.floor(target_ptr / 281474976710656) % 256, math.floor(target_ptr / 72057594037927936) % 256)

  print('正在定位 mechDatas 列表...')
  local ptr_results = AOBScan(ptr_bytes, '+W+X', 1, '0')

  if ptr_results ~= nil then
    for _, pr in ipairs(ptr_results) do
      local paddr = tonumber(pr, 16)
      -- 检查前后相邻的 8 字节值是否为有效指针（暗示这是数组）
      -- 如果前后都有有效指针，可能就是 mechDatas 数组
      if paddr >= 0x19500000000 then  -- IL2CPP 堆范围
        print(string.format('  候选数组位置: 0x%X', paddr))
        -- 从这个位置向前扫描，找到 List&lt;T&gt; 结构
        -- List 结构: items_ptr(8) + size(4) + version(4)
        -- 搜索包含此指针地址的 List 结构
        for offset = -0x200, 0, 8 do
          local list_addr = paddr - offset
          if list_addr > 0x10000 then
            local items = SafeReadPtr(list_addr)
            local sz = SafeReadInt(list_addr + 0x10)
            if items == paddr and sz >= 15 and sz <= 80 then
              mech_items_ptr = items
              mech_size = sz
              print(string.format('  [FOUND] mechDatas List @ 0x%X, items=0x%X, size=%d',
                list_addr, items, sz))
              break
            end
          end
        end
      end
      if mech_items_ptr ~= nil then break end
    end
  end

  -- 如果找不到列表，直接用单个 MechData
  if mech_items_ptr == nil then
    print('未找到完整列表，仅读取已定位的单个 MechData...')
    mech_items_ptr = mechDataPtrs[1]
    mech_size = 1
  end

  -- 7. 读取并显示所有单位数据
  print('\n' .. string.rep('=', 75))
  print(string.format('单位数据 (共 %d 个)', mech_size))
  print(string.rep('=', 75))
  print(string.format('%-4s %8s %7s %4s %4s %7s %11s %6s',
    'ID', 'HP', 'ATK', 'SPD', '飞行', '体型', '移动方式', '技能ID'))
  print(string.rep('-', 75))

  local type_names = {'Small', 'Medium', 'Huge'}
  local move_names = {'Normal', 'Underground', 'Cloak'}

  for i = 0, mech_size - 1 do
    local ptr
    if mech_size == 1 then
      ptr = mech_items_ptr  -- 单个 MechData 直接读取
    else
      ptr = SafeReadPtr(mech_items_ptr + i * 8)  -- 从数组读取
    end
    if ptr == 0 then goto continue end

    local life = SafeReadInt(ptr + OFF_LIFE)
    local dmg = SafeReadInt(ptr + OFF_DAMAGE)
    local spd = SafeReadInt(ptr + OFF_MOVESPEED)
    local isFly = SafeReadInt(ptr + OFF_ISFLY)
    local skill = SafeReadInt(ptr + OFF_MAINSKILLID)
    local mtype = SafeReadInt(ptr + OFF_MECHTYPE)
    local mvtype = SafeReadInt(ptr + OFF_MOVETYPE)

    local type_s = (mtype >= 0 and mtype <= 2) and type_names[mtype + 1] or ('?' .. mtype)
    local move_s = (mvtype >= 0 and mvtype <= 2) and move_names[mvtype + 1] or ('?' .. mvtype)
    local fly_s = (isFly ~= 0) and '✈' or '-'

    print(string.format('%-4d %8d %7d %4d %4s %7s %11s %6d',
      i, life, dmg, spd, fly_s, type_s, move_s, skill))

    ::continue::
  end

  -- 8. 在 CE 地址列表中创建条目
  print('\n[完成] 数据已输出到 Lua Engine 窗口。')
  print('使用 Ctrl+C 可复制文本。')

  -- 清理
  if results then results.destroy() end
  if ptr_results then ptr_results.destroy() end
end

-- 执行扫描
ScanForUnitData()
