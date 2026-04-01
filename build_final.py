#!/usr/bin/env python3
"""A股五维轮动看板 - 一屏全屏+按参考图比例+ETF彩色背景"""
import json
from datetime import datetime

with open("/tmp/dash_data.json","r",encoding="utf-8") as f:
    data = json.load(f)

results = data["results"]
sectors = data["sectors"]
indices  = data["indices"]
sentiment= data["sentiment"]
pnews    = data["policy_news"]

C = {"bg":"#0b141d","card":"#111d2b","card2":"#0f1825","border":"#1a2a3a",
     "text":"#e0e8f0","sub":"#5a7080","up":"#ff5533","down":"#00c07f","gold":"#ffaa00","cyan":"#00b4ff"}
ICC = lambda c: C["up"] if c>0 else C["down"] if c<0 else C["sub"]
ICS = lambda c: "+" if c>=0 else ""
IES = lambda s: str(s).replace("&","&amp;").replace('"',"&quot;").replace("<","&lt;").replace(">","&gt;")

STAGE_ICONS = {"启动":"🔵","发酵":"🟡","高潮":"🔴","分歧":"🟣","退潮":"⚫"}
STAGE_COLORS = {"启动":"#00b4ff","发酵":"#c87d00","高潮":"#ff3b30","分歧":"#ff8800","退潮":"#445566"}
STAGE_BG2   = {"启动":"rgba(0,100,180,0.25)","发酵":"rgba(180,120,0,0.25)","高潮":"rgba(200,30,30,0.3)","分歧":"rgba(220,100,0,0.25)","退潮":"rgba(50,70,90,0.25)"}
STAGE_SIG_TAG = {"启动":"加仓","发酵":"持有","高潮":"持有","分歧":"减仓","退潮":"观望"}
STAGE_SIG_COL = {"启动":"#00b4ff","发酵":"#00c07f","高潮":"#ffaa00","分歧":"#ff8800","退潮":"#556677"}
STAGE_DESCS  = {"启动":"量能放大+均线收敛","发酵":"动能释放+资金流入","高潮":"全面亢奋","分歧":"内部分化","退潮":"趋势向下"}

so = ["启动","发酵","高潮","分歧","退潮"]
cols = {st:[] for st in so}
for fc, r in results.items():
    cols[r["stage"]].append(r)

now = datetime.now().strftime("%m/%d %H:%M BJT")
changes = [abs(s["change"]) for s in sectors]
heat = min(int(sum(changes[:10])/max(len(changes[:10]),1)*12),100)
hlbl = "贪婪" if heat>65 else "恐惧" if heat<35 else "中性"
hcol = C["up"] if heat>65 else C["gold"] if heat>35 else C["down"]
heat2 = heat
dot_color = C["up"] if heat>65 else C["gold"] if heat>35 else C["down"]
warn_show = "flex" if heat>65 else "none"

def idx_html():
    h = ""
    for code, name in [("000001","SSE 上证"),("000300","CSI300 沪深300"),("399006","ChiNext 创业板"),("000688","STAR50 科创50")]:
        d = indices.get(code,{})
        c = d.get("change",0); p = d.get("price","---"); u = d.get("url","#")
        h += '<a href="'+u+'" target="_blank" class="ib" title="查看"><div class="in">'+name+'</div><div class="ip" style="color:'+ICC(c)+'">'+str(p)+'</div><div class="ic" style="color:'+ICC(c)+'">'+ICS(c)+str(round(c,2))+'%</div></a>'
    return h

def sector_html():
    h = ""
    for i, s in enumerate(sectors[:5], 1):
        c = s["change"]; bw = min(abs(c)*6, 100); bc = C["up"] if c>0 else C["down"]
        h += '<a href="https://quote.eastmoney.com/center/boardlist.html#concept_board" target="_blank" class="sb-row"><span class="sr">'+str(i)+'</span><div class="sbw"><div class="sbb" style="width:'+str(bw)+'%;background:'+bc+'"></div></div><span class="sn">'+IES(s["name"])+'</span><span class="sc" style="color:'+ICC(c)+'">'+ICS(c)+str(round(c,2))+'%</span></a>'
    return h

def heatmap_html():
    h = ""
    for s in sectors[:10]:
        c = s["change"]
        if c>=5: bg="#cc2200"
        elif c>=3: bg="#dd4400"
        elif c>=2: bg="#ee6600"
        elif c>=1: bg="#ff8800"
        elif c>=0: bg="#556677"
        elif c>=-2: bg="#448866"
        else: bg="#226644"
        h += '<a href="https://quote.eastmoney.com/center/boardlist.html#concept_board" target="_blank" class="hmb" style="background:'+bg+'" title="'+IES(s["name"])+'"><span class="hmn">'+IES(s["name"])+'</span><span class="hmc">'+ICS(c)+str(round(c,2))+'%</span></a>'
    return h

def etf_rotation_html():
    h = ""
    for st in so:
        items = cols.get(st,[]); sc = STAGE_COLORS[st]; bg2 = STAGE_BG2[st]; ic = STAGE_ICONS[st]; sig_lbl = STAGE_SIG_TAG[st]
        ih = ""
        for r in items:
            c = r["change"]
            pol=r["scores"]["政策"]; tec=r["scores"]["技术面"]; mon=r["scores"]["资金面"]
            bars = '<div class="mb"><div style="width:'+str(pol)+'%;background:#ff8800"></div><div style="width:'+str(tec)+'%;background:#00b4ff"></div><div style="width:'+str(mon)+'%;background:#ffaa00"></div></div>'
            ih += '<a href="'+r["url"]+'" target="_blank" class="eri" title="'+IES(r["name"])+'"><span class="erc">'+r["code"]+'</span><span class="ern">'+IES(r["name"])+'</span><span class="erch" style="color:'+ICC(c)+'">'+ICS(c)+str(round(c,2))+'%</span>'+bars+'</a>'
        h += '<div class="erc2" style="background:'+bg2+';border-top:3px solid '+sc+'"><div class="erhd" style="color:'+sc+'"><span>'+ic+'</span><b>['+sig_lbl+']</b><b style="color:#fff;font-size:9px">'+st+'</b></div><div class="erbd">'+ih+'</div></div>'
    return h

def dim_html():
    rows = ""
    for r in sorted(results.values(), key=lambda x: x["comp"], reverse=True):
        c = r["change"]
        sig_col = r["sig_col"]; sig_lbl = r["sig"]
        t = '<span class="t0">T0</span>' if r["comp"]>=75 else '<span class="t1">T1</span>' if r["comp"]>=55 else '<span class="tw">TW</span>'
        mult = round(r["comp"]/10, 1)
        pol=r["scores"]["政策"]; bas=r["scores"]["基本面"]; tec=r["scores"]["技术面"]; mon=r["scores"]["资金面"]; sen=r["scores"]["情绪面"]
        bars = '<div class="db"><div style="width:'+str(pol)+'%;background:#ff8800"></div><div style="width:'+str(bas)+'%;background:#00c07f"></div><div style="width:'+str(tec)+'%;background:#00b4ff"></div><div style="width:'+str(mon)+'%;background:#ffaa00"></div><div style="width:'+str(sen)+'%;background:#ff5533"></div></div>'
        reasons = []
        if r["scores"]["政策"]>=65: reasons.append("政策支撑")
        if r["scores"]["基本面"]>=65: reasons.append("基本面好")
        if r["scores"]["技术面"]>=70: reasons.append("技术强势")
        if r["scores"]["资金面"]>=65: reasons.append("资金流入")
        if r["stage"]=="退潮": reasons.append("趋势向下")
        if r["stage"]=="分歧": reasons.append("内部分化")
        reason = "·".join(reasons[:2]) if reasons else STAGE_DESCS[r["stage"]]
        rows += '<tr>'
        rows += '<td><a href="'+r["url"]+'" target="_blank" class="sg" style="background:'+sig_col+'">'+IES(sig_lbl)+'</a></td>'
        rows += '<td><a href="'+r["url"]+'" target="_blank" class="en">'+IES(r["name"])+'<br><span style="color:#5a7080;font-size:9px">'+r["code"]+'</span></a></td>'
        rows += '<td style="text-align:center">'+t+'</td>'
        rows += '<td style="text-align:center;font-weight:700;color:'+ICC(c)+'">'+ICS(c)+str(round(c,2))+'%</td>'
        rows += '<td style="text-align:center"><span style="font-size:14px;color:'+STAGE_COLORS[r["stage"]]+'">'+STAGE_ICONS[r["stage"]]+'</span></td>'
        rows += '<td style="text-align:center;font-weight:700;color:'+sig_col+'">x'+str(mult)+'</td>'
        rows += '<td>'+bars+'</td>'
        rows += '<td style="font-size:9px;color:#5a7080">'+IES(reason)+'</td>'
        rows += '</tr>'
    return rows

top1 = sorted(results.values(), key=lambda x: x["comp"], reverse=True)[0] if results else None
tn = top1["name"] if top1 else "暂无"
ts = top1["stage"] if top1 else ""
tc = top1["comp"] if top1 else 0
summary = tn+" "+STAGE_ICONS.get(ts,"")+" 启动中，热度"+str(heat2)+"° "+hlbl
risk = "热度"+str(heat2)+"° "+hlbl+" | 半导体/5G/AI高位分歧"
opp = "医药，光伏资金持续净流入"

html = '''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<title>A股板块轮动实时监测</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
a{text-decoration:none}
html,body{height:100%;overflow:hidden}
body{background:#0b141d;color:#e0e8f0;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;font-size:12px}

/* ========== 整体一屏布局 ========== */
.wrap{height:100vh;display:grid;grid-template-rows:52px 1fr 160px 36px;grid-template-columns:1fr 1fr;gap:1px;background:#1a2a3a}

/* 顶栏：跨两列 */
.hdr{grid-column:1/-1;background:linear-gradient(90deg,#08101e,#0d1a28);display:flex;align-items:center;padding:0 12px;gap:12px;border-bottom:1px solid #1a2a3a}
.ttl{font-size:13px;font-weight:700;color:#00b4ff;letter-spacing:0.5px;margin-right:auto;white-space:nowrap}
.hunit{display:flex;align-items:center;gap:6px}
.dot{width:6px;height:6px;background:'''+dot_color+''';border-radius:50%;animation:dp 2s infinite}
@keyframes dp{0%,100%{opacity:1}50%{opacity:0.3}}
.hl{font-size:10px;color:#5a7080}
.hv{padding:1px 7px;background:#111d2b;border:1px solid #1a2a3a;border-radius:4px;font-size:10px;font-weight:700;color:'''+hcol+'''}
.hbr{width:50px;height:4px;background:#1a2a3a;border-radius:2px;overflow:hidden}
.hbar{height:100%;background:'''+hcol+''';width:'''+str(heat2)+'''%}
.ird{display:flex;gap:4px;align-items:center}
.ib{display:flex;flex-direction:column;align-items:center;padding:3px 9px;background:#111d2b;border:1px solid #1a2a3a;border-radius:5px;cursor:pointer;min-width:65px}
.ib:hover{border-color:#00b4ff}
.in{font-size:8px;color:#5a7080;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:55px}
.ip{font-size:13px;font-weight:700}
.ic{font-size:9px;font-weight:600}
.ts{font-size:9px;color:#5a7080}

/* 警告行 */
.warn{grid-column:1/-1;background:#2a1500;border-bottom:1px solid #553300;display:'''+warn_show+''';align-items:center;justify-content:center;gap:8px;padding:0 12px}
.wtxt{font-size:10px;color:#ff8800;font-weight:600}

/* ========== 左：板块+ETF 右：热力+五维 ========== */
.lcol{display:flex;flex-direction:column;gap:1px;background:#1a2a3a;overflow:hidden}
.rcol{display:flex;flex-direction:column;gap:1px;background:#1a2a3a;overflow:hidden}

/* 通用标题 */
.shd{padding:4px 10px;font-size:10px;font-weight:700;color:#5a7080;background:#0d1a28;display:flex;align-items:center;gap:5px;letter-spacing:0.3px}

/* [Sector] 板块排行 */
.sec-l{background:#111d2b;flex:0 0 100px;overflow:hidden}
.sb2{padding:3px 0}
.sb-row{display:grid;grid-template-columns:18px 1fr 46px 42px;align-items:center;gap:4px;padding:4px 8px;cursor:pointer}
.sb-row:hover{background:#0f1825}
.sr{font-size:9px;color:#5a7080;text-align:center}
.sbw{height:4px;background:#1a2a3a;border-radius:2px;overflow:hidden}
.sbb{height:100%;border-radius:2px}
.sn{font-size:11px;color:#e0e8f0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}
.sc{font-size:11px;font-weight:700;text-align:right}

/* [Heatmap] */
.sec-r{background:#111d2b;flex:1;overflow:hidden}
.hm2{padding:4px;display:grid;grid-template-columns:repeat(5,1fr);gap:3px}
.hmb{border-radius:4px;padding:4px 3px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1px;min-height:36px;cursor:pointer;transition:transform 0.15s;opacity:0.82}
.hmb:hover{transform:scale(1.07);opacity:1}
.hmn{font-size:8px;color:#fff;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%;text-align:center;font-weight:500}
.hmc{font-size:11px;font-weight:700;color:#fff}

/* [ETF Rotation] 左下角，占左列下半部分 */
.rot-l{background:#111d2b;flex:1;overflow:hidden;display:flex;flex-direction:column}
.er5{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;flex:1;overflow:hidden;background:#1a2a3a}
.erc2{padding:4px 5px;overflow:hidden;display:flex;flex-direction:column}
.erhd{padding:3px 5px;font-size:10px;font-weight:700;display:flex;align-items:center;gap:4px;border-bottom:1px solid rgba(255,255,255,0.05)}
.erbd{padding:3px 0;flex:1;overflow-y:auto}
.eri{display:flex;flex-direction:column;gap:1px;padding:3px 5px;border-radius:3px;cursor:pointer;margin-bottom:2px;transition:background 0.15s}
.eri:hover{background:rgba(255,255,255,0.06)}
.erc{font-size:8px;color:#5a7080}
.ern{font-size:11px;color:#e0e8f0;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.erch{font-size:11px;font-weight:700}
.mb{display:flex;gap:1px;height:3px;border-radius:1px;overflow:hidden;background:#1a2a3a}
.mb div{height:100%}

/* [5-Dimension] 右下角，占右列下半部分 */
.dim-r{background:#111d2b;flex:1;overflow:hidden;display:flex;flex-direction:column}
.dimt{overflow-y:auto;flex:1}
.dtbl{width:100%;border-collapse:collapse}
.dtbl th{background:#0a1020;color:#5a7080;font-size:9px;font-weight:700;padding:3px 6px;text-align:center;border-bottom:1px solid #1a2a3a;white-space:nowrap}
.dtbl td{padding:3px 6px;vertical-align:middle;border-bottom:1px solid #0f1825}
.dtbl tr:hover{background:#0f1825}
.sg{display:inline-block;padding:1px 6px;border-radius:3px;font-size:9px;font-weight:700;color:#fff;cursor:pointer}
.en{color:#e0e8f0;font-size:10px;font-weight:500}
.en:hover{color:#00b4ff}
.t0{background:#003d55;color:#00b4ff;padding:1px 4px;border-radius:3px;font-size:8px;font-weight:700}
.t1{background:#1a3000;color:#00c07f;padding:1px 4px;border-radius:3px;font-size:8px;font-weight:700}
.tw{background:#1a2530;color:#556677;padding:1px 4px;border-radius:3px;font-size:8px;font-weight:700}
.db{display:flex;gap:1px;height:4px;border-radius:1px;overflow:hidden;background:#1a2a3a;width:70px}
.db div{height:100%}

/* ========== 底栏 ========== */
.ftr{grid-column:1/-1;background:#080c14;border-top:1px solid #1a2a3a;display:grid;grid-template-columns:1fr 1fr 1fr;gap:1px}
.ft{padding:5px 12px;font-size:9px;line-height:1.5}
.ft b{display:block;margin-bottom:1px}
.f0{background:#111d2b}
.f0 b{color:#00b4ff}
.f0 span{color:#e0e8f0}
.f1{background:#1a0808}
.f1 b{color:#ff4d4d}
.f1 span{color:#ff8888}
.f2{background:#081a10}
.f2 b{color:#00c07f}
.f2 span{color:#00dd88}

::-webkit-scrollbar{width:3px}
::-webkit-scrollbar-track{background:#111d2b}
::-webkit-scrollbar-thumb{background:#1a2a3a;border-radius:2px}
</style>
</head>
<body>
<div class="wrap">

  <!-- 顶栏 -->
  <div class="hdr">
    <span class="ttl">📊 [ Market Watch ] A股板块轮动实时监测 '''+now+'''</span>
    <div class="hunit">
      <div class="dot"></div>
      <span class="hl">Heat</span>
      <div class="hbr"><div class="hbar"></div></div>
      <span class="hv">'''+str(heat2)+'''/100 '''+hlbl+'''</span>
    </div>
    <div class="ird">
      '''+idx_html()+'''
      <span class="ts">BJT</span>
    </div>
  </div>

  <!-- 警告 -->
  <div class="warn">
    <span style="color:#ff8800">⚠️</span>
    <span class="wtxt">高热度预警 | 热度过热注意获利了结 | 板块高位分歧风险加剧</span>
    <span style="color:#ff8800">⚠️</span>
  </div>

  <!-- 左列 -->
  <div class="lcol">
    <div class="sec-l">
      <div class="shd">📊 [ Sector ] 强势板块 Top5</div>
      <div class="sb2">'''+sector_html()+'''</div>
    </div>
    <div class="rot-l">
      <div class="shd">🔄 [ ETF Rotation ] ETF轮动阶段</div>
      <div class="er5">'''+etf_rotation_html()+'''</div>
    </div>
  </div>

  <!-- 右列 -->
  <div class="rcol">
    <div class="sec-r">
      <div class="shd">🔥 [ Heatmap ] 板块热度矩阵</div>
      <div class="hm2">'''+heatmap_html()+'''</div>
    </div>
    <div class="dim-r">
      <div class="shd">📊 [ 5-Dimension ] 五维监控诊断</div>
      <div class="dimt">
        <table class="dtbl">
          <thead>
            <tr>
              <th class="dtbl th">信号</th>
              <th class="dtbl th">ETF</th>
              <th class="dtbl th">周期</th>
              <th class="dtbl th">涨跌幅</th>
              <th class="dtbl th">轮动</th>
              <th class="dtbl th">评分</th>
              <th class="dtbl th">政策/基本/技术/资金/情绪</th>
              <th class="dtbl th">诊断</th>
            </tr>
          </thead>
          <tbody>
            '''+dim_html()+'''
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- 底栏 -->
  <div class="ftr">
    <div class="ft f0">
      <b>[ SUMMARY ] 今日主线</b>
      <span>'''+summary+'''</span>
    </div>
    <div class="ft f1">
      <b>⚠️ RISK 风险提示</b>
      <span>'''+risk+'''</span>
    </div>
    <div class="ft f2">
      <b>✅ OPPORTUNITY 机会提示</b>
      <span>'''+opp+'''</span>
    </div>
  </div>

</div>
</body>
</html>'''

with open("/tmp/market_v7.html","w",encoding="utf-8") as f:
    f.write(html)
print("Done!", len(html), "bytes")
er = etf_rotation_html()
print("ETF links:", er.count('href="https://fund.eastmoney.com'))
print("Colored backgrounds:", er.count('background:rgba'))
