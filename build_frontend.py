"""Build self-contained frontend HTML with inlined data."""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(ROOT, 'frontend', 'unit_data.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)

data_json = json.dumps(data, ensure_ascii=False)

html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mechabellum 兵种数据 | 钢铁指挥官</title>
<style>
:root{--bg:#0d1117;--surface:#161b22;--border:#30363d;--text:#e6edf3;--text-dim:#8b949e;--accent:#58a6ff;--hp:#f85149;--atk:#ffa657;--spd:#7ee787;--giant:#d2a8ff;--air:#79c0ff;--small:#8b949e;--row-hover:#1c2128}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font:14px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
.container{max-width:1400px;margin:0 auto;padding:16px}
header{background:var(--surface);border-bottom:1px solid var(--border);padding:12px 0;position:sticky;top:0;z-index:10}
header .container{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
h1{font-size:20px}h1 span{color:var(--accent)}
.tabs{display:flex;gap:4px;margin-left:auto}
.tab{padding:6px 16px;border:1px solid var(--border);border-radius:6px;cursor:pointer;background:var(--surface);color:var(--text-dim);font-size:13px}
.tab.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.tab:hover:not(.active){color:var(--text)}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0;align-items:center}
.filters input,.filters select{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:6px 12px;color:var(--text);font-size:13px}
.filters input{flex:1;min-width:200px;max-width:320px}
.badge{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600}
.badge.giant{background:rgba(210,168,255,.15);color:var(--giant)}
.badge.air{background:rgba(121,192,255,.15);color:var(--air)}
.badge.ground{background:rgba(139,148,158,.15);color:var(--small)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{position:sticky;top:56px;background:var(--surface);padding:10px 8px;text-align:left;border-bottom:2px solid var(--border);cursor:pointer;user-select:none;white-space:nowrap}
th:hover{color:var(--accent)}
th.sorted::after{content:' ^';font-size:10px}
th.sorted.desc::after{content:' v'}
td{padding:8px;border-bottom:1px solid var(--border)}
tr:hover td{background:var(--row-hover)}
.num{text-align:right;font-variant-numeric:tabular-nums}
.hp-val{color:var(--hp);font-weight:600}
.atk-val{color:var(--atk);font-weight:600}
.spd-val{color:var(--spd);font-weight:600}
.cost-val{color:var(--accent)}
.unit-name{font-weight:600;display:flex;align-items:center;gap:6px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:16px}
.card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
.card h3{margin-bottom:8px;display:flex;align-items:center;gap:8px}
.card-row{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid rgba(48,54,61,.5)}
.card-row:last-child{border:none}
.card-label{color:var(--text-dim)}.card-value{font-weight:600}
.popup{display:none;position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px;z-index:100;max-width:480px;width:90%;max-height:80vh;overflow-y:auto;box-shadow:0 8px 32px rgba(0,0,0,.5)}
.popup.show{display:block}
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:99}
.overlay.show{display:block}
.close-btn{position:absolute;top:12px;right:12px;background:none;border:none;color:var(--text-dim);font-size:20px;cursor:pointer}
@media(max-width:768px){.card-grid{grid-template-columns:1fr}header .container{flex-direction:column}.tabs{margin-left:0}}
</style>
</head>
<body>
<header><div class="container">
<h1><span>Mechabellum</span> 兵种数据表</h1>
<div class="tabs">
<div class="tab active" onclick="switchTab('table')">数据表</div>
<div class="tab" onclick="switchTab('cards')">卡片</div>
<div class="tab" onclick="switchTab('about')">关于</div>
</div>
</div></header>
<div class="container">
<div id="tab-table">
<div class="filters">
<input type="text" id="search" placeholder="搜索..." oninput="renderTable()">
<select id="typeFilter" onchange="renderTable()"><option value="">全部体型</option><option value="巨型">巨型</option><option value="中型">中型</option><option value="小型">小型</option></select>
<select id="moveFilter" onchange="renderTable()"><option value="">全部移动</option><option value="飞行">飞行</option><option value="地面">地面</option></select>
<span style="color:var(--text-dim);font-size:12px" id="countDisplay"></span>
</div>
<div style="overflow-x:auto">
<table id="unitTable">
<thead><tr>
<th data-sort="name">兵种</th><th data-sort="size">体型</th>
<th data-sort="cost" class="num">造价</th><th data-sort="hp" class="num">血量</th>
<th data-sort="speed" class="num">移速</th><th data-sort="atk" class="num">攻击</th>
<th data-sort="splash" class="num">溅射</th><th data-sort="interval" class="num">间隔</th>
<th data-sort="range" class="num">射程</th><th data-sort="count" class="num">数量</th>
<th data-sort="slots" class="num">格子</th><th data-sort="unlock" class="num">解锁</th>
</tr></thead>
<tbody></tbody>
</table>
</div>
</div>
<div id="tab-cards" style="display:none">
<div class="filters">
<input type="text" id="cardSearch" placeholder="搜索..." oninput="renderCards()">
<select id="cardTypeFilter" onchange="renderCards()"><option value="">全部</option><option value="巨型">巨型</option><option value="中型">中型</option><option value="小型">小型</option></select>
</div>
<div class="card-grid" id="cardGrid"></div>
</div>
<div id="tab-about" style="display:none">
<div class="card" style="max-width:600px;margin:20px auto">
<h3>Mechabellum 钢铁指挥官 - 兵种数据</h3>
<p style="color:var(--text-dim);margin:12px 0">数据来源：游戏内手动采集 (2026-07-29, v1.11.1.1.2207)<br>自动监控：Steam RSS - 平衡性检测 - 自动更新<br>技术栈：Python + openpyxl + Anthropic Claude API</p>
<p><a href="https://github.com/LuckLuffy/MechabellumData" style="color:var(--accent)">GitHub</a></p>
</div>
</div>
</div>
<div class="overlay" id="overlay" onclick="closeDetail()"></div>
<div class="popup" id="detailPanel"><button class="close-btn" onclick="closeDetail()">&times;</button><div id="detailContent"></div></div>
<script>
var RAW = ''' + data_json + ''';

var UNITS = RAW.map(function(u){ return {
  name: u.name, size: u["体型"], move: u["移动类型"],
  cost: +u["造价"]||0, hp: +u["单体血量"]||0, speed: +u["移速"]||0,
  atk: +u["单次攻击"]||0, splash: +u["溅射范围"]||0, interval: +u["攻击间隔"]||0,
  range: +u["射程"]||0, count: +u["数量"]||0, slots: +u["占用格子"]||0,
  unlock: isNaN(+u["解锁费用"]) ? u["解锁费用"] : (+u["解锁费用"]||0),
  anti_air: u["对空"], dmg_hp: u["伤害血量"], exp: u["升级经验要求"], exp_out: u["提供经验"],
  _raw: u
}});

var sortField = 'cost', sortDesc = false;

function fmt(v){ return v==null||isNaN(v)?'-':Number.isInteger(v)?v.toLocaleString():v }
function tag(t,c){ return '<span class="badge '+c+'">'+t+'</span>' }

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
    var va = a[sortField], vb = b[sortField];
    if(sortField==='name'||sortField==='size'||sortField==='move')
      return sortDesc ? String(vb).localeCompare(String(va)) : String(va).localeCompare(String(vb));
    return sortDesc ? (vb||0)-(va||0) : (va||0)-(vb||0);
  });
  var html = '';
  for(var i=0; i<list.length; i++){
    var u = list[i];
    var sizeBadge = u.size==='巨型' ? tag(u.size,'giant') : u.size==='中型' ? tag(u.size,'air') : tag(u.size,'ground');
    var flyBadge = u.move==='飞行' ? tag('飞行','air') : '';
    html += '<tr data-unit="'+u.name+'" class="unit-row" style="cursor:pointer">';
    html += '<td><div class="unit-name">'+u.name+' '+sizeBadge+' '+flyBadge+'</div></td>';
    html += '<td>'+u.size+'</td>';
    html += '<td class="num cost-val">'+fmt(u.cost)+'</td>';
    html += '<td class="num hp-val">'+fmt(u.hp)+'</td>';
    html += '<td class="num spd-val">'+fmt(u.speed)+'</td>';
    html += '<td class="num atk-val">'+fmt(u.atk)+'</td>';
    html += '<td class="num">'+fmt(u.splash)+'</td>';
    html += '<td class="num">'+fmt(u.interval)+'</td>';
    html += '<td class="num">'+fmt(u.range)+'</td>';
    html += '<td class="num">'+fmt(u.count)+'</td>';
    html += '<td class="num">'+fmt(u.slots)+'</td>';
    html += '<td class="num">'+fmt(u.unlock)+'</td></tr>';
  }
  document.querySelector('#unitTable tbody').innerHTML = html;
  document.getElementById('countDisplay').textContent = list.length+' / '+UNITS.length;
  document.querySelectorAll('th').forEach(function(th){
    th.classList.remove('sorted','desc');
    if(th.dataset.sort === sortField){ th.classList.add('sorted'); if(sortDesc) th.classList.add('desc'); }
  });
}

function renderCards(){
  var q = (document.getElementById('cardSearch').value||'').toLowerCase();
  var tf = document.getElementById('cardTypeFilter').value;
  var list = UNITS.filter(function(u){
    if(q && u.name.toLowerCase().indexOf(q)===-1) return false;
    if(tf && u.size !== tf) return false;
    return true;
  });
  var html = '';
  for(var i=0; i<list.length; i++){
    var u = list[i];
    var sizeBadge = u.size==='巨型' ? tag(u.size,'giant') : u.size==='中型' ? tag(u.size,'air') : tag(u.size,'ground');
    var flyBadge = u.move==='飞行' ? tag('飞行','air') : '';
    html += '<div class="card" data-unit="'+u.name+'" style="cursor:pointer">';
    html += '<h3>'+u.name+' '+sizeBadge+' '+flyBadge+'</h3>';
    html += '<div class="card-row"><span class="card-label">造价</span><span class="card-value cost-val">'+fmt(u.cost)+'</span></div>';
    html += '<div class="card-row"><span class="card-label">血量</span><span class="card-value hp-val">'+fmt(u.hp)+'</span></div>';
    html += '<div class="card-row"><span class="card-label">攻击</span><span class="card-value atk-val">'+fmt(u.atk)+'</span></div>';
    html += '<div class="card-row"><span class="card-label">移速</span><span class="card-value spd-val">'+u.speed+'</span></div>';
    html += '<div class="card-row"><span class="card-label">射程</span><span class="card-value">'+fmt(u.range)+'</span></div>';
    html += '<div class="card-row"><span class="card-label">数量x格子</span><span class="card-value">'+fmt(u.count)+' x '+fmt(u.slots)+'</span></div>';
    html += '</div>';
  }
  document.getElementById('cardGrid').innerHTML = html;
}

function showDetail(name){
  var u = UNITS.find(function(x){return x.name===name}); if(!u) return;
  var r = u._raw;
  var fields = [['造价','cost-val'],['单体血量','hp-val'],['移速','spd-val'],['单次攻击','atk-val'],['溅射范围',''],['攻击间隔',''],['射程',''],['对空',''],['数量',''],['占用格子',''],['解锁费用',''],['伤害血量',''],['升级经验要求',''],['提供经验','']];
  var h = '<h3>'+u.name+' '+tag(u.size,u.size==='巨型'?'giant':u.size==='中型'?'air':'ground')+(u.move==='飞行'?tag('飞行','air'):'')+'</h3><div style="margin-top:12px">';
  for(var i=0; i<fields.length; i++){
    var f = fields[i][0], c = fields[i][1];
    var v = r[f] !== undefined ? r[f] : '-';
    h += '<div class="card-row"><span class="card-label">'+f+'</span><span class="card-value '+c+'">'+v+'</span></div>';
  }
  h += '</div>';
  document.getElementById('detailContent').innerHTML = h;
  document.getElementById('overlay').classList.add('show');
  document.getElementById('detailPanel').classList.add('show');
}
function closeDetail(){
  document.getElementById('overlay').classList.remove('show');
  document.getElementById('detailPanel').classList.remove('show');
}
function switchTab(t){
  document.querySelectorAll('.tab').forEach(function(x){x.classList.remove('active')});
  event.target.classList.add('active');
  document.getElementById('tab-table').style.display = t==='table'?'':'none';
  document.getElementById('tab-cards').style.display = t==='cards'?'':'none';
  document.getElementById('tab-about').style.display = t==='about'?'':'none';
  if(t==='table') renderTable();
  if(t==='cards') renderCards();
}
document.querySelectorAll('th').forEach(function(th){
  th.addEventListener('click', function(){
    var f = th.dataset.sort;
    if(sortField===f) sortDesc=!sortDesc; else{sortField=f;sortDesc=false}
    renderTable();
  });
});
document.addEventListener('keydown', function(e){if(e.key==='Escape') closeDetail()});

// Click delegation - no inline onclick needed
document.addEventListener('click', function(e){
  var el = e.target.closest && e.target.closest('[data-unit]');
  if(el){ showDetail(el.getAttribute('data-unit')); }
});
// INIT
renderTable();
</script>
</body>
</html>'''

out_path = os.path.join(ROOT, 'frontend', 'index.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Built: {out_path} ({len(html)} bytes, {len(data)} units)')
