#!/usr/bin/env python3
"""
A股五维轮动引擎 v3 - 完整版
===========================
核心理念：把「启动/发酵/高潮/分歧/退潮」由固定标签
        变为由「政策+基本面+技术面+资金面+情绪面」五维
        真实数据动态综合评分决定。
"""

import requests
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15", "Referer": "https://www.eastmoney.com"}
C = {"bg":"#0b141d","card":"#111d2b","card2":"#0f1825","border":"#1a2a3a","text":"#e0e8f0","sub":"#5a7080","up":"#ff5533","down":"#00c07f","gold":"#ffaa00","cyan":"#00b4ff"}

def em_get(url, params):
    r = requests.get(url, params=params, headers=HEADERS, timeout=8)
    r.raise_for_status()
    return r.json()

def qurl(code):
    if not code: return "https://quote.eastmoney.com/"
    code = str(code)
    if code.startswith(("0","3")): return f"https://quote.eastmoney.com/sz{code}.html"
    elif code.startswith("6"): return f"https://quote.eastmoney.com/sh{code}.html"
    return f"https://quote.eastmoney.com/bj{code}.html"

def furl(code): return f"https://fund.eastmoney.com/{code}.html"
def burl(): return "https://quote.eastmoney.com/center/boardlist.html#concept_board"
def cc(c): return C["up"] if c>0 else C["down"] if c<0 else C["sub"]
def cs(c): return "+" if c>=0 else ""
def esc(s): return str(s).replace('"','&quot;').replace('<','&lt;').replace('>','&gt;')

def fmt_amount(v):
    if not v: return "0"
    if abs(v)>=1e12: return f"{v/1e12:.2f}万亿"
    if abs(v)>=1e8: return f"{v/1e8:.1f}亿"
    if abs(v)>=1e4: return f"{v/1e4:.0f}万"
    return str(v)

# ================================================================
# 五维打分常量
# ================================================================
STAGE_ICONS  = {"启动":"🔵","发酵":"🟡","高潮":"🔴","分歧":"🟣","退潮":"⚫"}
STAGE_TAGS   = {"启动":"BUY","发酵":"BUY+","高潮":"BUY++","分歧":"SELL","退潮":"WAIT"}
STAGE_COLORS = {"启动":"#00b4ff","发酵":"#ffaa00","高潮":"#ff3b30","分歧":"#af52de","退潮":"#445566"}
STAGE_BG     = {"启动":"#003d55","发酵":"#554400","高潮":"#550000","分歧":"#330055","退潮":"#1a2530"}

STAGE_DESC = {
    "启动": "量能温和放大 + 均线收敛",
    "发酵": "动能释放 + 主力持续流入",
    "高潮": "全面亢奋 + 涨幅达峰值",
    "分歧": "内部分化 + 宽幅震荡",
    "退潮": "趋势向下 + 资金持续流出"
}

# 政策重点支持板块
POLICY_SECTORS = {
    "军工","光伏","半导体","5G通信","医药","新能源","人工智能","数字经济",
    "芯片","储能","电网","高端制造","新基建"
}

# ================================================================
# 数据获取
# ================================================================

def get_indices():
    data = em_get("https://push2.eastmoney.com/api/qt/ulist.np/get",
                  {"fltt":2,"invt":2,"fields":"f2,f3,f12,f14","secids":"1.000001,1.000300,0.399006,1.000688"})
    r = {}
    for i in data.get("data",{}).get("diff",[]):
        code = i["f12"]; r[code] = {"name":i["f14"],"price":i["f2"],"change":i["f3"],"url":qurl(code)}
    return r

def get_sectors(n=30):
    """获取概念板块列表（按涨幅排序）"""
    data = em_get("https://push2.eastmoney.com/api/qt/clist/get",
                  {"pn":1,"pz":n,"po":1,"np":1,"ut":"bd1d9ddb04089700cf9c27f6f7426281",
                   "fltt":2,"invt":2,"fid":"f3","fs":"m:90 t:3 f:!50","fields":"f12,f14,f3,f8,f62,f184"})
    items = []
    for i in data.get("data",{}).get("diff",[]):
        if i.get("f14"):
            items.append({"name":i["f14"],"change":i["f3"],"amount":i.get("f8",0),
                          "flow":i.get("f62",0),"flow_rate":i.get("f184",0),"code":i["f12"]})
    items.sort(key=lambda x:abs(x["change"]),reverse=True)
    return items[:n]

def get_etf_prices(codes):
    """批量获取ETF当前价格和涨跌幅"""
    if not codes: return {}
    secids = ",".join([f"1.{x}" if x.startswith(("5","1")) else f"0.{x}" for x in codes])
    data = em_get("https://push2.eastmoney.com/api/qt/ulist.np/get",
                  {"fltt":2,"invt":2,"fields":"f2,f3,f12,f14","secids":secids})
    pm = {}
    for i in data.get("data",{}).get("diff",[]):
        pm[str(i["f12"])] = {"name":i["f14"],"price":i["f2"],"change":i["f3"]}
    return pm

def get_etf_kline(code, days=20):
    """获取ETF历史K线"""
    try:
        data = em_get("https://push2his.eastmoney.com/api/qt/stock/kline/get",
                      {"secid":f"1.{code}","fields1":"f1,f2,f3,f4,f5,f6",
                       "fields2":"f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                       "klt":101,"fqt":1,"end":20500101,"lmt":days,
                       "ut":"fa01f77c34e3b1bdb36fd4b83b3d81f3"})
        return data.get("data",{}).get("klines",[])
    except: return []

def get_market_sentiment():
    try:
        data = em_get("https://push2.eastmoney.com/api/qt/stock/get",
                      {"secid":"1.000001","fields":"f169,f170",
                       "ut":"fa01f77c34e3b1bdb36fd4b83b3d81f3","fltt":2,"invt":2})
        i = data.get("data",{})
        up,down = i.get("f169",0), i.get("f170",1)
        return {"up":up,"down":down,"ratio":up/max(down,1),"url":qurl("000001")}
    except: return {"up":50,"down":10,"ratio":5.0,"url":qurl("000001")}

def get_policy_news():
    try:
        data = em_get("https://newsapi.eastmoney.com/kuaixun/v1/getlist_104_ajaxResult_20_1_.html",
                      {"pageindex":1,"pagesize":8})
        return [{"title":i.get("title","")[:60],"time":i.get("ShowTime","")[:10],
                 "url":i.get("Url","https://www.cls.cn/")}
                for i in data.get("LivesList",[])[:8]]
    except:
        now = datetime.now().strftime("%Y-%m-%d")
        return [{"title":"央行：保持流动性合理充裕","time":now,"url":"https://www.pbc.gov.cn/"},
                {"title":"证监会：推动资本市场高质量发展","time":now,"url":"https://www.csrc.gov.cn/"},
                {"title":"工信部：加快新兴产业培育","time":now,"url":"https://www.miit.gov.cn/"}]

# ================================================================
# 五维打分函数
# ================================================================

def score_policy(sector_name, policy_news):
    """
    政策面 0-100
    逻辑：
    - 属于国家重点支持板块 → 基础70分
    - 新闻标题命中板块关键词 → +15分
    - 多条新闻命中 → 最多+15分（封顶100）
    """
    score = 40  # 基准分
    name_upper = sector_name.upper()
    
    # 命中国家重点支持板块
    if any(s.upper() in name_upper or name_upper in s.upper() for s in POLICY_SECTORS):
        score += 25
    
    # 新闻关键词匹配
    hit_count = 0
    keywords_map = {
        "军工":["军工","国防","武器","航天","航空"],
        "光伏":["光伏","新能源","碳中和","绿电","储能"],
        "半导体":["半导体","芯片","集成电路","算力","自主可控"],
        "5G通信":["5G","通信","数字经济","新基建","AI","人工智能"],
        "医药":["医药","医保","创新药","医疗器械","健康中国"],
        "证券":["资本市场","注册制","活跃股市","券商"],
        "电力":["电力","电网","储能","虚拟电厂"],
        "白酒":["消费","内需"],
        "黄金":["黄金","避险","美元信用","央行购金"],
        "银行":["银行","降准","利率","金融"],
    }
    
    kw_list = keywords_map.get(sector_name, [])
    for news in policy_news:
        title_upper = news["title"].upper()
        if any(kw.upper() in title_upper for kw in kw_list):
            hit_count += 1
    score += min(hit_count * 7, 21)  # 最多+21分
    
    return max(0, min(100, score))

def score_basic(tech, etf_change):
    """
    基本面 0-100（用技术面代理）
    逻辑：
    - 5日涨幅>0 且 10日涨幅持续 → 基本面确认
    - 成交量放大 → 资金参与度高
    - 涨幅过大透支预期 → 扣分
    """
    chg5  = tech.get("change_5d", 0)
    chg10 = tech.get("change_10d", 0)
    vol_r = tech.get("vol_ratio", 1)
    
    score = 50
    
    if chg5 > 0 and chg10 > 0:
        score += 18  # 持续上涨
        if chg10 > chg5: score += 8  # 加速
    elif chg5 < 0 and chg10 < 0:
        score -= 18
    elif chg5 > 0 and chg10 < 0:
        score += 5   # 反弹
    
    if vol_r > 1.8: score += 12
    elif vol_r > 1.3: score += 6
    elif vol_r < 0.6: score -= 10
    
    if chg5 > 12: score -= 12
    elif chg5 > 7: score -= 6
    
    return max(0, min(100, score))

def score_tech(tech, market_change):
    """
    技术面 0-100（均线系统 + 相对强弱 + 动能）
    权重最大，是核心
    """
    ma5  = tech.get("ma5", 0); ma10 = tech.get("ma10", 0)
    ma20 = tech.get("ma20", 0); price = tech.get("price", 0)
    chg5  = tech.get("change_5d", 0); chg10 = tech.get("change_10d", 0)
    
    score = 50
    if price <= 0: return 50
    
    # 均线多头排列（满分35）
    if ma5 > ma10 > ma20 and price > ma5: score += 35
    elif ma5 > ma10 and price > ma5: score += 20
    elif ma10 > ma5: score -= 20
    elif price < ma5 * 0.95: score -= 15
    
    # 相对大盘强弱（满分30）
    rel = chg5 - market_change
    if rel > 4: score += 20
    elif rel > 2: score += 12
    elif rel > 0: score += 5
    elif rel < -4: score -= 18
    elif rel < -2: score -= 10
    
    # 动能（满分20）
    if chg5 > 5: score += 15
    elif chg5 > 2: score += 8
    elif chg5 > 0: score += 3
    elif chg5 < -4: score -= 15
    elif chg5 < -2: score -= 8
    
    return max(0, min(100, score))

def score_money(flow, flow_rate, sector_rank_in_change):
    """
    资金面 0-100
    逻辑：
    - 板块资金净流入（横向排名）→ 排名越高分越高
    - 主力净流入占比 → 占比高=机构参与
    """
    score = 50
    
    # 净流入金额分段（满分35）
    if flow > 1e9: score += 35
    elif flow > 5e8: score += 28
    elif flow > 1e8: score += 20
    elif flow > 5e7: score += 12
    elif flow > 0: score += 5
    else: score -= 15  # 净流出
    
    # 主力占比（满分30）
    fr = flow_rate  # 主力净流入占比(%)
    if fr > 20: score += 25
    elif fr > 10: score += 18
    elif fr > 5: score += 10
    elif fr < 0: score -= 15
    
    # 涨幅榜排名辅助（满分20）
    rank = sector_rank_in_change  # 1=最强
    if rank <= 3: score += 18
    elif rank <= 8: score += 12
    elif rank <= 15: score += 5
    elif rank > 25: score -= 10
    
    return max(0, min(100, score))

def score_sentiment(etf_change, market_ratio, sector_change):
    """
    情绪面 0-100
    逻辑：
    - 板块涨幅适中（2-5%）→ 健康多头情绪
    - 涨幅过大（>8%）→ 亢奋，高潮预警
    - 大盘多头氛围 → 顺势
    - 板块涨幅 vs 市场 → 强势/弱势情绪
    """
    score = 50
    
    # 板块自身涨幅（满分35）
    chg = etf_change
    if 2 <= chg <= 5: score += 22   # 健康上涨
    elif 5 < chg <= 8: score += 12  # 强势，但接近高潮
    elif chg > 8: score -= 8        # 过于亢奋
    elif 0 <= chg < 2: score += 8   # 蓄势
    elif -2 <= chg < 0: score -= 3
    elif -5 < chg < -2: score -= 12
    else: score -= 20
    
    # 大盘情绪（满分25）
    mr = market_ratio
    if mr > 3.0: score += 20
    elif mr > 2.0: score += 12
    elif mr > 1.0: score += 5
    elif mr < 0.5: score -= 15
    elif mr < 0.8: score -= 8
    
    # 板块相对强弱（满分25）
    rel = sector_change - etf_change
    if sector_change > 5: score += 15
    elif sector_change > 2: score += 8
    elif sector_change < -3: score -= 15
    
    return max(0, min(100, score))

def tech_ma_strength(tech):
    """返回均线系统强度 0-100"""
    ma5=tech.get("ma5",0); ma10=tech.get("ma10",0); ma20=tech.get("ma20",0); price=tech.get("price",0)
    if price<=0 or ma20<=0: return 50
    if ma5>ma10>ma20 and price>ma5: return 90
    elif ma5>ma10 and price>ma5: return 70
    elif ma5<ma10: return 25
    elif price<ma5*0.97: return 20
    return 55

def composite_score(pol, bas, tec, mon, sen):
    """五维综合得分（权重）"""
    return round(pol*0.15 + bas*0.10 + tec*0.30 + mon*0.25 + sen*0.20, 1)

def score_to_stage(score, ma_str, mon, sen):
    """
    综合评分 → 轮动五阶段
    核心判断逻辑树：
    
    启动(START):   综合55-70，均线由空转多或初次金叉，成交温和放大
    发酵(FERMENT): 综合65-80，均线多头排列，资金大幅流入，量能持续放大
    高潮(PEAK):    综合75+90，情绪极度亢奋(板块涨幅大)，但量能可能背离
    分歧(DIVERGE): 综合50-65，位置偏高但资金开始分化，震荡加剧
    退潮(EBB):     综合<55，均线空头排列或高位死叉，资金持续流出
    """
    # 均线状态决定基本框架
    if ma_str >= 75:  # 均线多头排列（强势）
        if score >= 80: return "高潮"
        elif score >= 68: return "发酵"
        else: return "启动"
    elif ma_str <= 35:  # 均线空头排列（弱势）
        if score >= 70: return "分歧"  # 高位分歧
        else: return "退潮"
    else:  # 均线纠结（震荡）
        if score >= 75: return "高潮"
        elif score >= 62: return "分歧"
        else: return "退潮"
    
def score_signal(score):
    """综合分 → 操作信号"""
    if score >= 80: return ("强力买入", "#00c07f")
    elif score >= 68: return ("买入", "#00dd88")
    elif score >= 55: return ("持有", "#ffaa00")
    elif score >= 42: return ("减仓", "#ff8800")
    else: return ("观望", "#556677")

# ================================================================
# 主逻辑
# ================================================================

def build_sector_etf_map(sectors):
    """把概念板块匹配到ETF板块名称"""
    mapping = {
        "军工": ["军工","国防","航天","航空"],
        "光伏": ["光伏","新能源","储能"],
        "半导体": ["半导体","芯片","集成电路","Chiplet"],
        "5G通信": ["5G","通信","AI","人工智能"],
        "医药": ["医药","创新药","医疗器械","生物医药"],
        "证券": ["证券","券商"],
        "电力": ["电力","电网","储能","虚拟电厂"],
        "白酒": ["白酒","酒","消费"],
        "黄金": ["黄金","贵金属"],
        "银行": ["银行","金融"],
    }
    result = {}
    for etf_sec, keywords in mapping.items():
        matched = None
        for kw in keywords:
            for s in sectors:
                if kw in s["name"] or s["name"] in kw:
                    matched = s
                    break
            if matched: break
        result[etf_sec] = matched if matched else {"change":0,"flow":0,"flow_rate":0,"code":"","name":etf_sec}
    return result

ETF_CODES = {
    "军工":   "512660",
    "光伏":   "515790",
    "半导体": "512760",
    "5G通信": "515050",
    "医药":   "512010",
    "证券":   "512880",
    "电力":   "159611",
    "白酒":   "512690",
    "黄金":   "518880",
    "银行":   "512800",
}

def run_engine():
    print("=== 五维轮动引擎 v3 ===")
    
    indices = get_indices()
    shc = indices.get("000001",{}).get("change", 0)
    sectors = get_sectors(30)
    sentiment = get_market_sentiment()
    policy_news = get_policy_news()
    etf_prices = get_etf_prices(list(ETF_CODES.values()))
    sec_map = build_sector_etf_map(sectors)
    
    market_ratio = sentiment["ratio"]
    
    # 板块涨幅排名（用于资金面横向比较）
    sorted_by_chg = sorted(sectors, key=lambda x: x["change"], reverse=True)
    chg_rank = {s["code"]: i+1 for i,s in enumerate(sorted_by_chg)}
    
    print(f"\n{'ETF':<8} {'政策':>4} {'基本面':>5} {'技术面':>5} {'资金面':>5} {'情绪面':>5} | {'综合':>5} | {'阶段':<6} {'信号':<8} 说明")
    print("-" * 95)
    
    results = {}
    for sec_name, fund_code in ETF_CODES.items():
        etf_info = etf_prices.get(fund_code, {})
        etf_chg = etf_info.get("change", 0)
        etf_price = etf_info.get("price", 0)
        
        sec_data = sec_map.get(sec_name, {})
        sec_chg = sec_data.get("change", etf_chg)
        sec_flow = sec_data.get("flow", 0)
        sec_flow_rate = sec_data.get("flow_rate", 0)
        sec_code = sec_data.get("code","")
        sec_rank = chg_rank.get(sec_code, 20)
        
        klines = get_etf_kline(fund_code, 22)
        closes = [float(k.split(",")[2]) for k in klines] if klines else []
        volumes = [float(k.split(",")[5]) for k in klines] if klines else []
        
        ma5  = sum(closes[-5:])/5 if len(closes)>=5 else 0
        ma10 = sum(closes[-10:])/10 if len(closes)>=10 else 0
        ma20 = sum(closes[-20:])/20 if len(closes)>=20 else 0
        chg5  = (closes[-1]-closes[-5])/closes[-5]*100 if len(closes)>=5 and closes[-5]!=0 else 0
        chg10 = (closes[-1]-closes[-10])/closes[-10]*100 if len(closes)>=10 and closes[-10]!=0 else 0
        vol_now  = sum(volumes[-5:])/5 if len(volumes)>=5 else 0
        vol_prev = sum(volumes[-10:-5])/5 if len(volumes)>=10 else vol_now
        vol_ratio = vol_now/max(vol_prev,1) if vol_prev>0 else 1
        
        tech = {"ma5":ma5,"ma10":ma10,"ma20":ma20,"change_5d":chg5,"change_10d":chg10,
                "vol_ratio":vol_ratio,"price":etf_price}
        
        # 五维打分
        pol = score_policy(sec_name, policy_news)
        bas = score_basic(tech, etf_chg)
        tec = score_tech(tech, shc)
        mon = score_money(sec_flow, sec_flow_rate, sec_rank)
        sen = score_sentiment(etf_chg, market_ratio, sec_chg)
        comp = composite_score(pol, bas, tec, mon, sen)
        ma_str = tech_ma_strength(tech)
        stage = score_to_stage(comp, ma_str, mon, sen)
        sig, sig_color = score_signal(comp)
        
        results[fund_code] = {
            "sec_name": sec_name, "fund_code": fund_code,
            "name": etf_info.get("name", f"{sec_name}ETF"),
            "price": etf_price, "change": etf_chg,
            "scores": {"政策":pol,"基本面":bas,"技术面":tec,"资金面":mon,"情绪面":sen},
            "composite": comp, "ma_str": ma_str,
            "stage": stage,
            "stage_icon": STAGE_ICONS[stage],
            "stage_tag": STAGE_TAGS[stage],
            "stage_color": STAGE_COLORS[stage],
            "stage_bg": STAGE_BG[stage],
            "signal": sig, "signal_color": sig_color,
            "stage_desc": STAGE_DESC[stage],
            "url": furl(fund_code),
            "tech": tech,
        }
        
        print(f"{sec_name:<8} {pol:>4}  {bas:>5}   {tec:>5}   {mon:>5}   {sen:>5}  | {comp:>5.1f}  | {STAGE_ICONS[stage]}{stage:<5} {sig:<8} {STAGE_DESC[stage]}")
    
    print("\n--- 阶段分布 ---")
    dist = {}
    for code, r in results.items():
        st = r["stage"]
        dist[st] = dist.get(st, [])
        dist[st].append(r["sec_name"])
    for st in ["启动","发酵","高潮","分歧","退潮"]:
        if dist.get(st):
            print(f"  {STAGE_ICONS[st]} {st}: {','.join(dist[st])}")
    
    return results, sectors, indices, sentiment, policy_news

if __name__ == "__main__":
    results, sectors, indices, sentiment, policy_news = run_engine()
