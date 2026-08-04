"""Build self-contained frontend HTML with inlined data.

军事工业 HUD 风格 —— 深钢色 + 琥珀色准星点缀，数字用等宽字体。
单文件、零依赖、离线可开。sticky 表头偏移用 JS 实测，杜绝遮盖。

两种模式：
- local（默认）：含服务器专属 UI（检查更新按钮/状态条/轮询），供 exe 内嵌
- web：纯静态数据页（无服务器按钮，加"数据更新于"横幅），供 GitHub Pages
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

# ============ 共享 CSS ============
CSS = """<style>
/* ===== 设计令牌 ===== */
:root{
  --bg:#0b0e13;            /* 深钢蓝黑 */
  --surface:#12161d;       /* 面板 */
  --surface2:#1a2029;      /* 面板抬升 */
  --border:#262d38;        /* 分隔线 */
  --border-bright:#333c4a;
  --accent:#ffb454;        /* 琥珀 · 准星 */
  --accent-2:#4fc3f7;      /* 青 · 数据 */
  --text:#e2e6ec;
  --dim:#8a94a0;
  --hp:#ff5f5f;
  --atk:#ffb454;
  --spd:#4fc3f7;
  --giant:#d2a8ff;
  --air:#79c0ff;
  --small:#8a94a0;
  --row-hover:#161c26;
  --mono:'Cascadia Code','Consolas',ui-monospace,monospace;
  --sans:'Segoe UI','Microsoft YaHei',-apple-system,BlinkMacSystemFont,sans-serif;
  --display:'Bahnschrift','Segoe UI',sans-serif;
}
*{margin:0;padding:0;box-sizing:border-box}
html{scrollbar-color:var(--border) var(--bg)}
body{background:var(--bg);color:var(--text);font:15px/1.7 var(--sans);min-height:100vh}

/* ===== 顶部工具条（sticky） ===== */
.toolbar{position:sticky;top:0;z-index:30;background:var(--surface);border-bottom:1px solid var(--border)}
.toolbar .accent-line{height:2px;background:linear-gradient(90deg,var(--accent),transparent 70%)}
.bar{max-width:1440px;margin:0 auto;padding:10px 20px;display:flex;align-items:center;gap:20px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:12px;min-width:0}
.brand-mark{width:30px;height:30px;border:1px solid var(--accent);border-radius:4px;display:grid;place-items:center;color:var(--accent);font-size:13px;flex-shrink:0;background:rgba(255,180,84,.06)}
.brand h1{font:700 18px/1.2 var(--display);letter-spacing:.5px;white-space:nowrap}
.brand h1 em{font-style:normal;color:var(--accent)}
.brand .sub{font-size:11px;color:var(--dim);letter-spacing:2px;text-transform:uppercase}
.tabs{display:flex;gap:2px;margin-left:auto;background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:2px}
.tab{padding:5px 16px;border-radius:4px;cursor:pointer;color:var(--dim);font-size:13px;transition:all .15s}
.tab:hover{color:var(--text)}
.tab.active{background:var(--accent);color:#1a1206;font-weight:600}

.filters{max-width:1440px;margin:0 auto;padding:0 20px 10px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.filters input,.filters select{background:var(--surface2);border:1px solid var(--border);border-radius:5px;padding:7px 12px;color:var(--text);font:14px var(--sans);outline:none;transition:border-color .15s}
.filters input:focus,.filters select:focus{border-color:var(--accent)}
.filters input{flex:1;min-width:180px;max-width:300px}
.readout{display:inline-flex;align-items:center;gap:6px;margin-left:auto;font:13px var(--mono);color:var(--dim);letter-spacing:1px}
.readout b{color:var(--accent);font-size:15px}
.check-btn{background:var(--accent);color:#1a1206;border:none;border-radius:5px;padding:6px 14px;font:600 13px var(--sans);cursor:pointer;transition:filter .15s}
.check-btn:hover{filter:brightness(1.1)}
.check-btn:disabled{opacity:.5;cursor:wait}
.statusbar{max-width:1440px;margin:0 auto;padding:0 20px 8px;font:11px var(--mono);color:var(--dim);display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.statusbar .ok{color:var(--spd)}.statusbar .warn{color:var(--atk)}.statusbar .err{color:var(--hp)}
/* 网页版更新横幅 */
.web-banner{max-width:1440px;margin:0 auto;padding:0 20px 10px;font:11px var(--mono);color:var(--spd);letter-spacing:1px}

/* ===== 主内容 ===== */
main{max-width:1440px;margin:0 auto;padding:16px 20px 60px}

/* ===== 数据表 ===== */
/* 表格自身体积内滚动：表头吸在滚动容器顶部(top:0)，
   不会与上方 sticky 工具栏互相重叠 */
.table-wrap{overflow:auto;max-height:72vh;border:1px solid var(--border);border-radius:8px;background:var(--surface)}
/* border-collapse:separate 是 th sticky 生效的前提（collapse 下 Chrome 会失效） */
table{width:100%;border-collapse:separate;border-spacing:0;font-size:14px;min-width:900px}
thead th{position:sticky;top:0;z-index:5;background:var(--surface2);padding:13px 14px;text-align:left;border-bottom:2px solid var(--border);cursor:pointer;user-select:none;white-space:nowrap;font:600 13px var(--sans);color:var(--dim);letter-spacing:.5px}
thead th:hover{color:var(--text)}
/* 冻结第一列（兵种名）：横向滚动时保持可见 */
thead th:first-child{position:sticky;left:0;z-index:6;border-right:1px solid var(--border-bright)}
tbody td:first-child{position:sticky;left:0;z-index:4;background:var(--surface);border-right:1px solid var(--border-bright)}
tbody tr:hover td:first-child{background:var(--row-hover)}
thead th.sorted{color:var(--accent)}
thead th.sorted::after{content:' ▲';font-size:9px;color:var(--accent)}
thead th.sorted.desc::after{content:' ▼'}
tbody td{padding:12px 14px;border-bottom:1px solid var(--border);white-space:nowrap}
tbody tr{transition:background .1s}
tbody tr:hover td{background:var(--row-hover)}
tbody tr:last-child td{border-bottom:none}
.num{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums}
.name-cell{font-weight:600;display:flex;align-items:center;gap:8px}
.tag{display:inline-flex;align-items:center;padding:2px 9px;border-radius:3px;font:600 12px var(--sans);letter-spacing:.5px}
.tag.super-giant{background:rgba(255,180,84,.14);color:var(--accent);border:1px solid rgba(255,180,84,.4)}
.tag.giant{background:rgba(210,168,255,.12);color:var(--giant);border:1px solid rgba(210,168,255,.3)}
.tag.medium{background:rgba(79,195,247,.10);color:var(--air);border:1px solid rgba(79,195,247,.3)}
.tag.small{background:rgba(138,148,160,.10);color:var(--small);border:1px solid rgba(138,148,160,.25)}
.tag.fly{background:rgba(121,192,255,.08);color:var(--air);border:1px solid rgba(121,192,255,.2)}
.tag.aa{background:rgba(126,231,135,.14);color:#7ee787;border:1px solid rgba(126,231,135,.35)}
.cost{color:var(--accent);font-weight:600}
.hp{color:var(--hp);font-weight:600}
.atk{color:var(--atk);font-weight:600}
.spd{color:var(--spd);font-weight:600}

/* ===== 卡片视图 ===== */
.card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:20px;cursor:pointer;transition:border-color .15s,transform .1s}
.card:hover{border-color:var(--accent);transform:translateY(-1px)}
.card h3{margin-bottom:10px;display:flex;align-items:center;gap:8px;font:600 15px var(--sans)}
.card-row{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid rgba(38,45,56,.6);font-size:14px}
.card-row:last-child{border:none}
.card-label{color:var(--dim)}.card-value{font-family:var(--mono);font-weight:600}

/* ===== 详情弹窗 ===== */
.overlay{display:none;position:fixed;inset:0;background:rgba(5,7,10,.7);z-index:90;backdrop-filter:blur(2px)}
.overlay.show{display:block}
.popup{display:none;position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:var(--surface);border:1px solid var(--border-bright);border-radius:10px;padding:24px;z-index:100;max-width:460px;width:92%;max-height:82vh;overflow-y:auto;box-shadow:0 16px 48px rgba(0,0,0,.6)}
.popup.show{display:block}
.close-btn{position:absolute;top:10px;right:14px;background:none;border:none;color:var(--dim);font-size:22px;cursor:pointer;line-height:1}
.close-btn:hover{color:var(--text)}
.popup h3{font:700 18px var(--display);display:flex;align-items:center;gap:10px;margin-bottom:6px}
.popup .popup-sub{font:11px var(--mono);color:var(--dim);letter-spacing:1px;margin-bottom:14px}
.stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--border);border:1px solid var(--border);border-radius:6px;overflow:hidden}
.stat-cell{background:var(--surface2);padding:9px 12px;display:flex;justify-content:space-between;align-items:center}
.stat-cell .k{font-size:12px;color:var(--dim)}
.stat-cell .v{font-family:var(--mono);font-weight:600}

/* ===== 关于 ===== */
.about-card{max-width:560px;margin:24px auto;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:28px}
.about-card h3{font:700 20px var(--display);margin-bottom:8px}
.about-card p{color:var(--dim);margin:8px 0}
.about-card a{color:var(--accent)}

/* ===== 响应式 ===== */
@media(max-width:768px){
  .bar{flex-direction:column;align-items:stretch;gap:10px;padding:10px 14px}
  .tabs{margin-left:0;justify-content:center}
  .brand h1{white-space:normal}
  .filters{padding:0 14px 10px}
  .readout{margin-left:0}
  main{padding:14px}
  .stat-grid{grid-template-columns:1fr}
}
@media(prefers-reduced-motion:reduce){
  *{transition:none!important}
}
</style>"""

# ============ 头部（含条件占位） ============
HEADER = """<header class="toolbar">
  <div class="accent-line"></div>
  <div class="bar">
    <div class="brand">
      <div class="brand-mark">&#9670;</div>
      <div>
        <h1><em>MECHABELLUM</em> 兵种数据</h1>
        <div class="sub">钢铁指挥官 · 兵种数据</div>
      </div>
    </div>
    <nav class="tabs">
      <div class="tab active" data-tab="table">数据表</div>
      <div class="tab" data-tab="cards">卡片</div>
      <div class="tab" data-tab="about">关于</div>
    </nav>
    __CHECK_BTN__
  </div>
  <div class="filters" id="filters-table">
    <input type="text" id="search" placeholder="搜索兵种..." oninput="renderTable()">
    <select id="typeFilter" onchange="renderTable()">
      <option value="">全部体型</option><option value="超巨型">超巨型</option><option value="巨型">巨型</option><option value="中型">中型</option><option value="小型">小型</option>
    </select>
    <select id="moveFilter" onchange="renderTable()">
      <option value="">全部机动</option><option value="飞行">飞行</option><option value="地面">地面</option>
    </select>
    <span class="readout" id="countDisplay"></span>
  </div>
  <div class="filters" id="filters-cards" style="display:none">
    <input type="text" id="cardSearch" placeholder="搜索兵种..." oninput="renderCards()">
    <select id="cardTypeFilter" onchange="renderCards()">
      <option value="">全部体型</option><option value="超巨型">超巨型</option><option value="巨型">巨型</option><option value="中型">中型</option><option value="小型">小型</option>
    </select>
  </div>
  __BOTTOM_BAR__
</header>"""

# ============ 主内容 ============
MAIN = """<main>
  <div id="tab-table">
    <div class="table-wrap">
      <table id="unitTable">
        <thead><tr>
          <th data-sort="name">兵种</th><th data-sort="size">体型</th>
          <th data-sort="cost" class="num">造价</th><th data-sort="hp" class="num">血量</th>
          <th data-sort="total_hp" class="num">总血量</th>
          <th data-sort="speed" class="num">移速</th><th data-sort="atk" class="num">攻击力</th>
          <th data-sort="single_out" class="num">对单输出</th>
          <th data-sort="burst" class="num">爆发峰值</th>
          <th data-sort="splash" class="num">溅射</th><th data-sort="interval" class="num">间隔</th>
          <th data-sort="dps" class="num">对单DPS</th>
          <th data-sort="total_dps" class="num">总DPS</th>
          <th data-sort="dps_ratio" class="num">输出性价比</th>
          <th data-sort="hp_ratio" class="num">血量性价比</th>
          <th data-sort="range" class="num">射程</th><th data-sort="count" class="num">数量</th>
          <th data-sort="slots" class="num">格子</th><th data-sort="unlock" class="num">解锁</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </div>

  <div id="tab-cards" style="display:none">
    <div class="card-grid" id="cardGrid"></div>
  </div>

  <div id="tab-about" style="display:none">
    <div class="about-card">
      <h3>钢铁指挥官 · 兵种数据</h3>
      <p>数据来源：游戏内手动采集（2026-07-29 · v1.11.1.1.2207）</p>
      <p>自动监控：Steam RSS → 平衡性检测 → Deepseek 解析 → 数据表更新</p>
      <p>技术栈：Python + openpyxl + Deepseek API + 纯静态前端</p>
      <p><a href="https://github.com/LuckLuffy/MechabellumData">GitHub 仓库</a></p>
    </div>
  </div>
</main>"""

# ============ 弹窗 ============
POPUP = """<div class="overlay" id="overlay"></div>
<div class="popup" id="detailPanel">
  <button class="close-btn" id="closeBtn">&times;</button>
  <div id="detailContent"></div>
</div>"""

# ============ JS 核心（共享） ============
JS_PRE = """var RAW = __DATA_JSON__;

// 统一映射函数：内嵌 RAW 与服务器 /api/data 两条路径共用，避免字段漂移
// 新表结构：对单输出F/爆发峰值G/对单DPSH 由表格提供（含武器数）
function makeUnit(u){
  var cost = +u["造价"]||0, hp = +u["单体血量"]||0;
  var atk = +u["攻击力"]||0;              // 攻击力 E
  var single_out = +u["对单输出"]||0;     // 对单输出 F（=攻击力×武器数）
  var burst = +u["爆发峰值"]||0;          // 爆发峰值 G（=F×数量，雷霆×3深渊×10）
  var dps = +u["对单DPS"]||0;            // 对单DPS H（=F/间隔，深渊=G/间隔）
  var count = +u["数量"]||0;
  var total_dps = dps * count;           // 总DPS = 对单DPS × 数量
  var total_hp = hp * count;             // 总血量 = 血量 × 数量
  return {
    name: u.name, size: u["体型"], move: u["移动类型"],
    cost: cost, hp: hp, speed: +u["移速"]||0, atk: atk,
    single_out: single_out, burst: burst, dps: dps,
    splash: +u["溅射范围"]||0, interval: +u["攻击间隔"]||0,
    range: +u["射程"]||0, count: count, slots: +u["占用格子"]||0,
    unlock: isNaN(+u["解锁费用"]) ? u["解锁费用"] : (+u["解锁费用"]||0),
    total_dps: total_dps,
    total_hp: total_hp,
    dps_ratio: cost > 0 ? dps / cost : 0,   // 输出性价比 = 对单DPS / 造价
    hp_ratio: cost > 0 ? hp / cost : 0,     // 血量性价比 = 血量 / 造价
    _raw: u
  };
}
var UNITS = RAW.map(makeUnit);

var sortField = 'cost', sortDesc = false;

function fmt(v){ return v==null||isNaN(v)?'-':Number.isInteger(v)?v.toLocaleString():v }
function fmt2(v){ return (v==null||isNaN(v)) ? '-' : v.toFixed(2) }
function sizeTag(s){ return '<span class="tag '+(s==='超巨型'?'super-giant':s==='巨型'?'giant':s==='中型'?'medium':'small')+'">'+s+'</span>' }
function flyTag(){ return '<span class="tag fly">飞行</span>' }
// 对空标签：以下单位具备显著对空能力
var AA_UNITS = ['长弓','野马','先知','台风','熔点'];
function aaTag(name){ return AA_UNITS.indexOf(name)>=0 ? '<span class="tag aa">对空</span>' : ''; }

/* ===== 数据表 ===== */
function renderTable(){
  var q = (document.getElementById('search').value||'').toLowerCase();
  var tf = document.getElementById('typeFilter').value;
  var mf = document.getElementById('moveFilter').value;
  var list = UNITS.filter(function(u){
    if(q && u.name.toLowerCase().indexOf(q)===-1) return false;
    if(tf && u.size !== tf) return false;
    if(mf && u.move !== mf) return false;
    return true;
  });
  list.sort(function(a,b){
    var va=a[sortField], vb=b[sortField];
    if(sortField==='name'||sortField==='size'||sortField==='move')
      return sortDesc ? String(vb).localeCompare(String(va)) : String(va).localeCompare(String(vb));
    return sortDesc ? (vb||0)-(va||0) : (va||0)-(vb||0);
  });
  var html='';
  for(var i=0;i<list.length;i++){
    var u=list[i];
    html+='<tr data-unit="'+u.name+'">';
    html+='<td><div class="name-cell">'+u.name+' '+sizeTag(u.size)+(u.move==='飞行'?flyTag():'')+aaTag(u.name)+'</div></td>';
    html+='<td>'+u.size+'</td>';
    html+='<td class="num cost">'+fmt(u.cost)+'</td>';
    html+='<td class="num hp">'+fmt(u.hp)+'</td>';
    html+='<td class="num hp">'+fmt(u.total_hp)+'</td>';
    html+='<td class="num spd">'+fmt(u.speed)+'</td>';
    html+='<td class="num atk">'+fmt(u.atk)+'</td>';
    html+='<td class="num atk">'+fmt(u.single_out)+'</td>';
    html+='<td class="num atk">'+fmt(u.burst)+'</td>';
    html+='<td class="num">'+fmt(u.splash)+'</td>';
    html+='<td class="num">'+fmt(u.interval)+'</td>';
    html+='<td class="num">'+fmt2(u.dps)+'</td>';
    html+='<td class="num">'+fmt2(u.total_dps)+'</td>';
    html+='<td class="num">'+fmt2(u.dps_ratio)+'</td>';
    html+='<td class="num">'+fmt2(u.hp_ratio)+'</td>';
    html+='<td class="num">'+fmt(u.range)+'</td>';
    html+='<td class="num">'+fmt(u.count)+'</td>';
    html+='<td class="num">'+fmt(u.slots)+'</td>';
    html+='<td class="num">'+fmt(u.unlock)+'</td></tr>';
  }
  document.querySelector('#unitTable tbody').innerHTML=html;
  document.getElementById('countDisplay').innerHTML='UNIT <b>'+list.length+'</b> / '+UNITS.length;
  var ths=document.querySelectorAll('#unitTable th');
  for(var j=0;j<ths.length;j++){
    var th=ths[j];
    th.classList.remove('sorted','desc');
    if(th.getAttribute('data-sort')===sortField){
      th.classList.add('sorted');
      if(sortDesc) th.classList.add('desc');
    }
  }
}

/* ===== 卡片视图 ===== */
function renderCards(){
  var q=(document.getElementById('cardSearch').value||'').toLowerCase();
  var tf=document.getElementById('cardTypeFilter').value;
  var list=UNITS.filter(function(u){
    if(q && u.name.toLowerCase().indexOf(q)===-1) return false;
    if(tf && u.size !== tf) return false;
    return true;
  });
  var html='';
  for(var i=0;i<list.length;i++){
    var u=list[i];
    html+='<div class="card" data-unit="'+u.name+'">';
    html+='<h3>'+u.name+' '+sizeTag(u.size)+(u.move==='飞行'?flyTag():'')+aaTag(u.name)+'</h3>';
    html+='<div class="card-row"><span class="card-label">造价</span><span class="card-value cost">'+fmt(u.cost)+'</span></div>';
    html+='<div class="card-row"><span class="card-label">血量</span><span class="card-value hp">'+fmt(u.hp)+'</span></div>';
    html+='<div class="card-row"><span class="card-label">攻击力</span><span class="card-value atk">'+fmt(u.atk)+'</span></div>';
    html+='<div class="card-row"><span class="card-label">对单DPS</span><span class="card-value atk">'+fmt2(u.dps)+'</span></div>';
    html+='<div class="card-row"><span class="card-label">总DPS</span><span class="card-value">'+fmt2(u.total_dps)+'</span></div>';
    html+='<div class="card-row"><span class="card-label">数量 × 格子</span><span class="card-value">'+fmt(u.count)+' × '+fmt(u.slots)+'</span></div>';
    html+='</div>';
  }
  document.getElementById('cardGrid').innerHTML=html;
}

/* ===== 详情弹窗 ===== */
function showDetail(name){
  var u=UNITS.find(function(x){return x.name===name}); if(!u) return;
  var r=u._raw;
  // 用映射后的 u 取计算值，用 _raw 取原始列
  var rows=[
    ['造价', u.cost, 'cost'],
    ['单体血量', u.hp, 'hp'],
    ['总血量', u.total_hp, ''],
    ['移速', u.speed, 'spd'],
    ['攻击力', u.atk, 'atk'],
    ['对单输出', u.single_out, ''],
    ['爆发峰值', u.burst, ''],
    ['对单DPS', u.dps, ''],
    ['总DPS', u.total_dps, ''],
    ['输出性价比', u.dps_ratio, ''],
    ['血量性价比', u.hp_ratio, ''],
    ['溅射范围', u.splash, ''],
    ['攻击间隔', u.interval, ''],
    ['射程', u.range, ''],
    ['对空', r['对空'], ''],
    ['数量', u.count, ''],
    ['占用格子', u.slots, ''],
    ['解锁费用', u.unlock, ''],
    ['伤害血量', r['伤害血量'], ''],
    ['升级经验要求', r['升级经验要求'], ''],
    ['提供经验', r['提供经验'], '']
  ];
  var h='<h3>'+u.name+' '+sizeTag(u.size)+(u.move==='飞行'?flyTag():'')+aaTag(u.name)+'</h3>';
  h+='<div class="popup-sub">UNIT #'+u._raw.id+' · '+(u.move==='飞行'?'AIR':'GROUND')+' · '+u.size+'</div>';
  h+='<div class="stat-grid">';
  for(var i=0;i<rows.length;i++){
    var label=rows[i][0], val=rows[i][1], cls=rows[i][2];
    var v=(val!==undefined && val!==null)?val:'-';
    h+='<div class="stat-cell"><span class="k">'+label+'</span><span class="v '+cls+'">'+v+'</span></div>';
  }
  h+='</div>';
  document.getElementById('detailContent').innerHTML=h;
  document.getElementById('overlay').classList.add('show');
  document.getElementById('detailPanel').classList.add('show');
}
function closeDetail(){
  document.getElementById('overlay').classList.remove('show');
  document.getElementById('detailPanel').classList.remove('show');
}

/* ===== 标签切换 ===== */
function switchTab(t){
  var tabs=document.querySelectorAll('.tab');
  for(var i=0;i<tabs.length;i++) tabs[i].classList.toggle('active',tabs[i].getAttribute('data-tab')===t);
  document.getElementById('tab-table').style.display=t==='table'?'':'none';
  document.getElementById('tab-cards').style.display=t==='cards'?'':'none';
  document.getElementById('tab-about').style.display=t==='about'?'':'none';
  document.getElementById('filters-table').style.display=t==='table'?'':'none';
  document.getElementById('filters-cards').style.display=t==='cards'?'':'none';
  if(t==='table') renderTable();
  if(t==='cards') renderCards();
}

/* ===== 事件绑定 ===== */
document.querySelectorAll('.tab').forEach(function(t){
  t.addEventListener('click',function(){switchTab(t.getAttribute('data-tab'))});
});
document.querySelectorAll('#unitTable th').forEach(function(th){
  th.addEventListener('click',function(){
    var f=th.getAttribute('data-sort');
    if(sortField===f) sortDesc=!sortDesc; else{sortField=f;sortDesc=false}
    renderTable();
  });
});
document.getElementById('closeBtn').addEventListener('click',closeDetail);
document.getElementById('overlay').addEventListener('click',closeDetail);
document.addEventListener('keydown',function(e){if(e.key==='Escape')closeDetail()});
document.addEventListener('click',function(e){
  var el=e.target.closest&&e.target.closest('[data-unit]');
  if(el) showDetail(el.getAttribute('data-unit'));
});
"""

# ============ JS 服务器专属（仅 local 模式） ============
JS_API = """
/* ===== API 数据源（仅本地服务器版） ===== */
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
      UNITS = d.map(makeUnit);
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
"""

JS_INIT_LOCAL = """
/* ===== 初始化 ===== */
renderTable();
refreshData();
"""

JS_INIT_WEB = """
/* ===== 初始化（静态网页版：直接渲染内嵌数据） ===== */
renderTable();
renderCards();
"""


def render_page(data_json: str, web: bool = False, updated_at: str = "") -> str:
    """渲染完整 HTML。

    web=True 时：无服务器按钮/状态条/轮询，加"数据更新于"横幅。
    """
    if web:
        check_btn = ""
        bottom_bar = (
            '<div class="web-banner">&#128197; 数据更新于 ' + updated_at + ' · 每周自动更新</div>'
        )
        api_js = ""
        init_js = JS_INIT_WEB
    else:
        check_btn = '<button id="checkBtn" class="check-btn">&#9881; 检查更新</button>'
        bottom_bar = '<div class="statusbar" id="statusBar">初始化中…</div>'
        api_js = JS_API
        init_js = JS_INIT_LOCAL

    head = (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>Mechabellum 兵种数据 · 钢铁指挥官</title>\n'
        + CSS
        + '</head>\n<body>\n'
    )

    header = HEADER.replace("__CHECK_BTN__", check_btn).replace("__BOTTOM_BAR__", bottom_bar)
    js = JS_PRE.replace("__DATA_JSON__", data_json) + api_js + init_js

    return (
        head + header + MAIN + POPUP
        + '<script>\n' + js + '</script>\n</body>\n</html>'
    )


def main():
    with open(os.path.join(ROOT, 'frontend', 'unit_data.json'), 'r', encoding='utf-8') as f:
        data = json.load(f)
    data_json = json.dumps(data, ensure_ascii=False)
    html = render_page(data_json, web=False)
    out_path = os.path.join(ROOT, 'frontend', 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Built: {out_path} ({len(html)} bytes, {len(data)} units)')


if __name__ == "__main__":
    main()
