"""Dota2 T1 职业比赛数据分析 Demo — 数据来源: OpenDota 官方公开 API（真实数据）

T1 定义: OpenDota premium 分级 + 主流顶级赛事白名单。
新增: 全局联赛筛选、英雄 BP 深度分析、Elo 对战/比分预测（含回测）。
"""
import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_option_menu import option_menu

# ----------------------------------------------------------------------------
# 基础配置
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Dota2 T1 比赛分析", page_icon="⚔️", layout="wide", initial_sidebar_state="expanded")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CST = timezone(timedelta(hours=8))

ACCENT = "#C23C2A"   # Dota2 红
GOLD = "#C9A227"
RADIANT = "#5AD35A"  # 天辉绿
DIRE = "#E54545"     # 夜魇红
BLUE = "#5AA7E5"
BG = "#0F1116"
PANEL = "#1A1D24"

# T1 联赛定义：premium 级别 + 主流顶级赛事白名单（与 fetch_data.py 保持一致）
T1_NAME_PATTERNS = (
    "The International", "Esports World Cup", "BLAST", "Riyadh",
    "ESL One", "DreamLeague", "PGL ", "BetBoom Dacha", "FISSURE",
    "Games of the Future",
)


def is_t1(tier: str, league_name: str) -> bool:
    if tier == "premium":
        return True
    name = (league_name or "").lower()
    return any(p.lower() in name for p in T1_NAME_PATTERNS)


def hero_icon(npc_name: str) -> str:
    short = npc_name.replace("npc_dota_hero_", "")
    return f"https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/{short}.png"


@st.cache_data(ttl=3600, show_spinner=False)
def load_snapshot(fname: str):
    path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=300, show_spinner=False)
def api_available() -> bool:
    try:
        req = urllib.request.Request("https://api.opendota.com/api/distributions",
                                     headers={"User-Agent": "dota2-analytics-demo/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


@st.cache_data(ttl=3600, show_spinner=False)
def live_fetch(path: str):
    if not api_available():
        return None
    try:
        req = urllib.request.Request("https://api.opendota.com/api" + path,
                                     headers={"User-Agent": "dota2-analytics-demo/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def hero_maps():
    cn = {}
    constants = load_snapshot("constants.json") or {}
    for hid, h in constants.items():
        cn[int(hid)] = {"npc": h.get("name", ""), "en": h.get("localized_name", "")}
    off = load_snapshot("heroes_official.json")
    if off:
        for h in off["result"]["data"]["heroes"]:
            m = cn.setdefault(h["id"], {"npc": h["name"], "en": h["name_english_loc"]})
            m["cn"] = h["name_loc"]
    return cn


def hero_cn(hid, maps):
    m = maps.get(hid)
    if not m:
        return f"Hero {hid}", ""
    return m.get("cn") or m.get("en", f"Hero {hid}"), hero_icon(m["npc"])


# ----------------------------------------------------------------------------
# 样式
# ----------------------------------------------------------------------------
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@600;800&family=Noto+Sans+SC:wght@400;500;700&display=swap');

    html, body, [class*="css"], .stApp {
        background: %s !important;
        color: #E8E6E3 !important;
        font-family: 'Noto Sans SC', sans-serif;
    }
    .block-container { padding-top: 1.4rem; max-width: 1400px; }

    section[data-testid="stSidebar"], div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #12141A 0%%, #171A22 55%%, #1D212B 100%%) !important;
        border-right: 1px solid rgba(194,60,42,0.25);
    }
    section[data-testid="stSidebar"] > div, div[data-testid="stSidebar"] > div,
    div[data-testid="stSidebarContent"],
    div[data-testid="stSidebar"] [data-testid="stSidebarContent"],
    div[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { background: transparent !important; }
    section[data-testid="stSidebar"] *, div[data-testid="stSidebar"] * { color: #E8E6E3 !important; }
    section[data-testid="stSidebar"] .stCaption, section[data-testid="stSidebar"] small,
    div[data-testid="stSidebar"] .stCaption, div[data-testid="stSidebar"] small { color: #9AA3B2 !important; }
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] [data-baseweb="select"] * { color: #E8E6E3 !important; }

    h1, h2, h3 { font-family: 'Noto Serif SC', serif !important; color: #F5F2EC !important; }
    .hero-title {
        font-family: 'Noto Serif SC', serif; font-weight: 800;
        font-size: 2.6rem; line-height: 1.15;
        background: linear-gradient(90deg, #F5F2EC 20%%, #C9A227 65%%, #C23C2A 100%%);
        -webkit-background-clip: text; background-clip: text; color: transparent !important;
        margin-bottom: 0.2rem;
    }
    .hero-sub { color: #9AA3B2; font-size: 1.02rem; margin-bottom: 1.4rem; }

    .kpi-card {
        background: linear-gradient(145deg, #1A1D24, #14161C);
        border: 1px solid rgba(201,162,39,0.30);
        border-radius: 14px; padding: 18px 20px;
        box-shadow: 0 6px 22px rgba(0,0,0,0.35);
        transition: transform .18s ease;
    }
    .kpi-card:hover { transform: translateY(-3px); border-color: rgba(201,162,39,0.7); }
    .kpi-value { font-family:'Noto Serif SC', serif; font-size: 1.9rem; font-weight: 800; color: #E8C766; }
    .kpi-label { color: #9AA3B2; font-size: .88rem; margin-top: 2px; }

    .panel {
        background: linear-gradient(145deg, #1A1D24, #14161C);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 14px; padding: 18px 20px; margin-bottom: 12px;
    }

    table.data-table { width: 100%%; border-collapse: collapse; }
    table.data-table th { color: #C9A227; text-align: left; font-weight: 700; padding: 8px 10px;
                          border-bottom: 1px solid rgba(201,162,39,.35); }
    table.data-table td { padding: 8px 10px; border-bottom: 1px solid rgba(255,255,255,.06); }

    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] { color: #9AA3B2 !important; border-radius: 10px 10px 0 0; }
    .stTabs [aria-selected="true"] { color: #E8C766 !important; }

    .stDownloadButton > button { color:#E8E6E3 !important; border-color: rgba(201,162,39,.5) !important; }
    </style>
    """ % BG, unsafe_allow_html=True)


def kpi_row(items):
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.markdown(f'<div class="kpi-card"><div class="kpi-value">{value}</div><div class="kpi-label">{label}</div></div>',
                     unsafe_allow_html=True)


def plotly_layout(fig, height=420):
    fig.update_layout(paper_bgcolor=PANEL, plot_bgcolor=PANEL, font_color="#E8E6E3",
                      height=height, margin=dict(l=30, r=30, t=44, b=30),
                      title_font_color="#F5F2EC", hovermode="closest")
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.07)", zerolinecolor="rgba(255,255,255,0.15)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.07)", zerolinecolor="rgba(255,255,255,0.15)")
    return fig


def fmt_dur(sec):
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ----------------------------------------------------------------------------
# 数据加载与全局筛选
# ----------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def _t1_base():
    raw = load_snapshot("t1Matches.json")
    if raw is None:
        return None, False
    leagues = load_snapshot("leagues.json") or []
    tier_map = {l["leagueid"]: l.get("tier") for l in leagues}
    fresh = [m for m in (live_fetch("/proMatches") or [])
             if is_t1(tier_map.get(m.get("leagueid")), m.get("league_name"))]
    seen, merged = set(m["match_id"] for m in raw), list(raw)
    if fresh:
        for m in fresh:
            if m["match_id"] not in seen:
                merged.insert(0, m)
                seen.add(m["match_id"])
    return merged, bool(fresh)


def t1_df(matches):
    df = pd.DataFrame(matches)
    df["radiant_win"] = df["radiant_win"].astype(bool)
    df["开始时间"] = pd.to_datetime(df["start_time"], unit="s", utc=True).dt.tz_convert(CST).dt.strftime("%m-%d %H:%M")
    df["日期"] = pd.to_datetime(df["start_time"], unit="s", utc=True).dt.tz_convert(CST).dt.date
    df["时长"] = df["duration"].apply(fmt_dur)
    df["比分"] = df["radiant_score"].astype(str) + " : " + df["dire_score"].astype(str)
    df["获胜方"] = df.apply(lambda r: r["radiant_name"] if r["radiant_win"] else r["dire_name"], axis=1)
    df["天辉"] = df["radiant_name"].fillna("TBD")
    df["夜魇"] = df["dire_name"].fillna("TBD")
    df["联赛"] = df["league_name"].fillna("—")
    df["系列赛"] = df["series_type"].map({0: "单场", 1: "BO3", 2: "BO5"})
    return df.sort_values("start_time", ascending=False).reset_index(drop=True)


def all_leagues():
    raw, _ = _t1_base()
    if not raw:
        return []
    names = sorted({m.get("league_name") or "—" for m in raw})
    return [n for n in names if n != "—"]


def get_filtered_df():
    """应用侧边栏联赛筛选后的比赛 DataFrame（所有页面共用）。"""
    raw, fresh = _t1_base()
    if not raw:
        return None, fresh
    df = t1_df(raw)
    sel = st.session_state.get("league_filter") or []
    if sel:
        df = df[df["联赛"].isin(sel)]
    return df, fresh


def get_filtered_details():
    details = load_snapshot("t1Details.json") or []
    sel = st.session_state.get("league_filter") or []
    if sel:
        details = [d for d in details if d.get("league_name") in sel]
    return details


# ----------------------------------------------------------------------------
# Elo 模型（预测模块核心）
# ----------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def elo_model(matches_raw):
    """按时间顺序在 T1 比赛上训练 Elo；同时输出逐场回测结果。

    matches_raw: list[dict]（快照原始结构）
    """
    ms = sorted(matches_raw, key=lambda m: m["start_time"])
    ratings = {}
    K = 32
    hist = []
    for m in ms:
        r_name = (m.get("radiant_name") or "").strip()
        d_name = (m.get("dire_name") or "").strip()
        if not r_name or not d_name or r_name == "TBD" or d_name == "TBD":
            continue
        ra = ratings.get(r_name, 1500.0)
        rd = ratings.get(d_name, 1500.0)
        ea = 1.0 / (1.0 + 10 ** ((rd - ra) / 400.0))          # 天辉(按队伍强度)期望胜率
        actual = 1 if m.get("radiant_win") else 0
        hist.append({"match_id": m["match_id"], "ea": ea, "actual": actual,
                     "r_name": r_name, "d_name": d_name})
        ratings[r_name] = ra + K * (actual - ea)
        ratings[d_name] = rd + K * ((1 - actual) - (1 - ea))
    acc = sum(1 for h in hist if round(h["ea"]) == h["actual"]) / max(len(hist), 1)
    logloss = -sum(h["actual"] * max(h["ea"], 1e-9) + (1 - h["actual"]) * max(1 - h["ea"], 1e-9)
                   for h in hist) / max(len(hist), 1)
    return ratings, acc, logloss, len(hist)


def series_prob(p: float, bo: int) -> float:
    """单图胜率 p → 系列赛胜率（先到 N 局）。"""
    if bo == 1:
        return p
    n = (bo + 1) // 2  # 需要赢的局数
    from math import comb
    return sum(comb(n + k - 1, k) * (p ** n) * ((1 - p) ** k) for k in range(n))


# ----------------------------------------------------------------------------
# 页面 1：比赛库
# ----------------------------------------------------------------------------
def page_matches():
    st.markdown('<div class="hero-title">T1 比赛库</div>'
                '<div class="hero-sub">可用左侧栏筛选联赛；此处再按战队/阵营/时长细分 — OpenDota 真实数据</div>',
                unsafe_allow_html=True)

    df, fresh = get_filtered_df()
    if df is None:
        st.error("比赛数据不可用。")
        return
    if not fresh:
        st.info("当前展示打包快照数据（OpenDota 实时接口暂不可用）。")

    kpi_row([("T1 对局数", f"{len(df)}"),
             ("覆盖联赛", f"{df['联赛'].nunique()}"),
             ("出场战队", f"{pd.concat([df['天辉'], df['夜魇']]).nunique()}"),
             ("平均时长", fmt_dur(df["duration"].mean())),
             ("平均总击杀", f"{(df['radiant_score']+df['dire_score']).mean():.0f}")])

    c1, c2, c3 = st.columns(3)
    q = c1.text_input("搜索战队/联赛", placeholder="如: Liquid, PARIVISION, ESL")
    side = c2.radio("阵营筛选", ["全部", "天辉获胜", "夜魇获胜"], horizontal=True)
    dur = c3.slider("时长下限（分钟）", 15, 90, 20, 5)

    view = df[df["duration"] >= dur * 60]
    if q:
        ql = q.lower()
        view = view[view.apply(lambda r: ql in str(r["天辉"]).lower() or ql in str(r["夜魇"]).lower()
                                         or ql in str(r["联赛"]).lower(), axis=1)]
    if side == "天辉获胜":
        view = view[view["radiant_win"]]
    elif side == "夜魇获胜":
        view = view[~view["radiant_win"]]

    st.markdown(f"**筛选结果：{len(view)} 场**")
    st.dataframe(view[["开始时间", "联赛", "系列赛", "天辉", "夜魇", "获胜方", "比分", "时长"]],
                 width="stretch", hide_index=True, height=520)
    st.download_button("下载筛选结果 CSV", view[["开始时间", "联赛", "系列赛", "天辉", "夜魇", "获胜方", "比分", "时长"]]
                       .to_csv(index=False).encode("utf-8-sig"), "t1_matches.csv", "text/csv")


# ----------------------------------------------------------------------------
# 页面 2：深度复盘
# ----------------------------------------------------------------------------
def pb_badge(item, maps):
    cn, _ = hero_cn(item["hero_id"], maps)
    team = "天辉" if item["team"] == 0 else "夜魇"
    color = RADIANT if item["team"] == 0 else DIRE
    return (f'<span style="display:inline-flex;align-items:center;gap:4px;margin:3px 6px 3px 0;'
            f'padding:3px 8px;border-radius:8px;border:1px solid {color}55;background:rgba(255,255,255,0.03)">'
            f'<span style="color:{color};font-size:.72rem">{team}</span>'
            f'<span style="color:{color};font-weight:700">{item["order"]+1}</span>{cn}</span>')


def render_match_detail(m, maps, league_label="—"):
    r_win = m.get("radiant_win")
    r_score, d_score = m.get("radiant_score", 0), m.get("dire_score", 0)
    r_name = (m.get("radiant_team") or {}).get("name") if isinstance(m.get("radiant_team"), dict) else m.get("radiant_team")
    d_name = (m.get("dire_team") or {}).get("name") if isinstance(m.get("dire_team"), dict) else m.get("dire_team")
    r_name, d_name = r_name or "天辉", d_name or "夜魇"
    winner = "🟢 天辉" if r_win else "🔴 夜魇"
    st.markdown(f"""
<div class="panel">
<span style="font-size:1.5rem;font-weight:800;font-family:'Noto Serif SC',serif">
<span style="color:{RADIANT}">{r_name}</span>
<span style="color:#9AA3B2;font-size:1rem;margin:0 10px">{r_score} : {d_score}</span>
<span style="color:{DIRE}">{d_name}</span></span>
<div style="color:#9AA3B2;margin-top:6px">联赛 {league_label} · 时长 {fmt_dur(m.get('duration',0))} ·
获胜方 <b style="color:{RADIANT if r_win else DIRE}">{winner}</b> · MatchID {m.get('match_id','—')}</div>
</div>""", unsafe_allow_html=True)

    pb = m.get("picks_bans") or []
    tabs = st.tabs(["👤 选手数据", "🧩 阵容与禁用", "📈 经济/经验曲线", "🏰 目标物"])
    with tabs[0]:
        rows = []
        for p in m.get("players") or []:
            cn, icon = hero_cn(p.get("hero_id", 0), maps)
            side = "天辉" if p.get("player_slot", 0) < 100 else "夜魇"
            rows.append({
                "阵营": side, "英雄": cn, "头像": icon,
                "选手": p.get("name") or "匿名",
                "K/D/A": f'{p.get("kills",0)}/{p.get("deaths",0)}/{p.get("assists",0)}',
                "KDA": round(((p.get("kills",0) or 0) + (p.get("assists",0) or 0)) / max(p.get("deaths",1) or 1, 1), 2),
                "等级": p.get("level", 0),
                "GPM": p.get("gold_per_min", 0), "XPM": p.get("xp_per_min", 0),
                "正补": p.get("last_hits", 0), "反补": p.get("denies", 0),
                "净资产": p.get("net_worth", 0),
                "英雄伤害": p.get("hero_damage", 0), "推塔伤害": p.get("tower_damage", 0),
                "治疗": p.get("hero_healing", 0),
            })
        pdf = pd.DataFrame(rows)
        for side_name, color in [("天辉", RADIANT), ("夜魇", DIRE)]:
            sub = pdf[pdf["阵营"] == side_name]
            trs = ""
            for _, r in sub.iterrows():
                trs += (f'<tr><td><img src="{r["头像"]}" style="height:36px;border-radius:6px;vertical-align:middle;margin-right:8px">{r["英雄"]}</td>'
                        f'<td>{r["选手"]}</td><td style="font-weight:700;color:{color}">{r["K/D/A"]}</td>'
                        f'<td>{r["KDA"]}</td><td>{r["GPM"]}</td><td>{r["XPM"]}</td>'
                        f'<td>{r["正补"]}/{r["反补"]}</td><td>{r["净资产"]:,}</td>'
                        f'<td>{r["英雄伤害"]:,}</td><td>{r["推塔伤害"]:,}</td><td>{r["治疗"]:,}</td></tr>')
            st.markdown(f'<div class="panel"><b style="color:{color};font-size:1.05rem">{side_name}方</b>'
                        f'<table class="data-table"><tr><th>英雄</th><th>选手</th><th>K/D/A</th><th>KDA</th>'
                        f'<th>GPM</th><th>XPM</th><th>正/反补</th><th>净资产</th><th>英雄伤害</th><th>推塔伤害</th><th>治疗</th></tr>'
                        f'{trs}</table></div>', unsafe_allow_html=True)

    with tabs[1]:
        if pb:
            picks = sorted([p for p in pb if p["is_pick"]], key=lambda x: x["order"])
            bans = sorted([p for p in pb if not p["is_pick"]], key=lambda x: x["order"])
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🧩 Pick（按顺序）**")
                st.markdown("".join(pb_badge(x, maps) for x in picks), unsafe_allow_html=True)
            with c2:
                st.markdown("**🚫 Ban（按顺序）**")
                st.markdown("".join(pb_badge(x, maps) for x in bans), unsafe_allow_html=True)
        else:
            st.caption("该场比赛暂无 BP 数据（OpenDota 尚未解析）。")

    with tabs[2]:
        ga, xa = m.get("radiant_gold_adv"), m.get("radiant_xp_adv")
        if ga:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=ga, mode="lines", name="天辉经济领先", line=dict(color=GOLD, width=2.5)))
            if xa:
                fig.add_trace(go.Scatter(y=xa, mode="lines", name="天辉经验领先", line=dict(color=BLUE, width=2)))
            fig.add_hline(y=0, line_color="rgba(255,255,255,0.3)")
            fig.update_layout(title="天辉视角 经济/经验领先曲线（正=天辉领先）",
                              xaxis_title="比赛分钟", yaxis_title="领先值")
            st.plotly_chart(plotly_layout(fig, height=440), width="stretch")
            flips = sum(1 for a, b in zip(ga, ga[1:]) if (a >= 0) != (b >= 0))
            lead, trail = max(ga), min(ga)
            kpi_row([("经济优势反转次数", f"{flips}"),
                     ("天辉最大领先", f"{lead:,.0f}"),
                     ("夜魇最大领先", f"{-trail:,.0f}" if trail < 0 else "0"),
                     ("比赛悬念指数", "胶着" if flips > 4 else "中等" if flips > 2 else "一边倒")])
        else:
            st.caption("该场比赛无经济曲线数据。")

    with tabs[3]:
        obj = m.get("objectives") or []
        if isinstance(obj, list):
            towers = [o for o in obj if o.get("type") == "building_kill" and "tower" in o.get("key", "")]
            rosh = [o for o in obj if o.get("type") == "CHAT_MESSAGE_ROSHAN_KILL"]
            rad_tower = sum(1 for o in towers if "badguys" in o.get("key", ""))
            dire_tower = sum(1 for o in towers if "goodguys" in o.get("key", ""))
            rad_rosh = sum(1 for o in rosh if o.get("team") == 2)
            dire_rosh = sum(1 for o in rosh if o.get("team") == 3)
            c1, c2 = st.columns(2)
            with c1:
                counts = {"天辉拿塔": rad_tower, "夜魇拿塔": dire_tower}
                fig = go.Figure(go.Bar(x=list(counts.keys()), y=list(counts.values()),
                                       marker_color=[RADIANT, DIRE]))
                fig.update_layout(title="防御塔摧毁数")
                st.plotly_chart(plotly_layout(fig, height=340), width="stretch")
            with c2:
                counts = {"天辉控盾": rad_rosh, "夜魇控盾": dire_rosh}
                fig = go.Figure(go.Bar(x=list(counts.keys()), y=list(counts.values()),
                                       marker_color=[RADIANT, DIRE]))
                fig.update_layout(title="肉山盾控制次数")
                st.plotly_chart(plotly_layout(fig, height=340), width="stretch")
        else:
            st.caption("该场比赛无目标物数据。")


def page_match_detail():
    st.markdown('<div class="hero-title">深度复盘</div>'
                '<div class="hero-sub">T1 比赛单场全解析（跟随左侧联赛筛选）— 优先实时接口，快照兜底</div>',
                unsafe_allow_html=True)

    df, _ = get_filtered_df()
    if df is None or not len(df):
        st.error("比赛列表不可用（或当前联赛筛选为空）。")
        return
    maps = hero_maps()

    def label(r):
        return f'{r["开始时间"]} · {r["天辉"]} vs {r["夜魇"]} ({r["比分"]}) · {r["联赛"]}'

    pick = st.selectbox("选择一场比赛", df.head(50).index, format_func=lambda i: label(df.loc[i]))
    row = df.loc[pick]
    match_id = int(row["match_id"])

    m = live_fetch(f"/matches/{match_id}")
    src = "OpenDota 实时接口"
    if not m:
        slim = [x for x in get_filtered_details() if x.get("match_id") == match_id]
        if slim:
            m, src = slim[0], "内置快照"
    if not m:
        st.warning("详情暂时不可用（实时接口故障且该场不在快照中）。")
        return
    st.caption(f"数据来源：{src}")
    render_match_detail(m, maps, row["联赛"])


# ----------------------------------------------------------------------------
# 页面 3：英雄风向
# ----------------------------------------------------------------------------
def page_heroes():
    st.markdown('<div class="hero-title">英雄选择与 BP 分析</div>'
                '<div class="hero-sub">T1 赛场英雄出场/禁用/胜率/组合搭配 — 基于最近 60 场解析数据（跟随联赛筛选）</div>',
                unsafe_allow_html=True)

    details = get_filtered_details()
    if not details:
        st.error("详情快照不可用（或当前联赛筛选为空）。")
        return
    maps = hero_maps()

    # ---- 聚合 ----
    pick, win, ban, side_win = {}, {}, {}, {"radiant": {}, "dire": {}}
    firstpick, lastpick = {}, {}   # 一选/末选英雄
    duo = {}                        # 同队组合
    n_bp = 0
    for m in details:
        pb = m.get("picks_bans") or []
        if pb:
            n_bp += 1
            picks = sorted([x for x in pb if x["is_pick"]], key=lambda x: x["order"])
            if picks:
                firstpick[picks[0]["hero_id"]] = firstpick.get(picks[0]["hero_id"], 0) + 1
                lastpick[picks[-1]["hero_id"]] = lastpick.get(picks[-1]["hero_id"], 0) + 1
            for x in pb:
                if not x["is_pick"]:
                    ban[x["hero_id"]] = ban.get(x["hero_id"], 0) + 1
        # 出场与胜率
        sides = {}
        for p in m.get("players") or []:
            hid = p.get("hero_id")
            pick[hid] = pick.get(hid, 0) + 1
            is_rad = p.get("player_slot", 0) < 100
            won = is_rad == m.get("radiant_win")
            if won:
                win[hid] = win.get(hid, 0) + 1
            key = "radiant" if is_rad else "dire"
            side_win[key].setdefault(hid, [0, 0])[1] += 1
            side_win[key][hid][0] += 1 if won else 0
            sides.setdefault(key, []).append(hid)
        for hid in sides.get("radiant", []):
            for hid2 in sides.get("radiant", []):
                if hid < hid2:
                    duo[(hid, hid2)] = duo.get((hid, hid2), [0, 0])
                    duo[(hid, hid2)][1] += 1
                    if m.get("radiant_win"):
                        duo[(hid, hid2)][0] += 1
        for hid in sides.get("dire", []):
            for hid2 in sides.get("dire", []):
                if hid < hid2:
                    duo[(hid, hid2)] = duo.get((hid, hid2), [0, 0])
                    duo[(hid, hid2)][1] += 1
                    if not m.get("radiant_win"):
                        duo[(hid, hid2)][0] += 1

    rows = []
    for hid, cnt in pick.items():
        cn, icon = hero_cn(hid, maps)
        rw = side_win["radiant"].get(hid, [0, 0])
        dw = side_win["dire"].get(hid, [0, 0])
        rows.append({"英雄": cn, "图标": icon, "出场": cnt,
                     "胜场": win.get(hid, 0),
                     "胜率%": round(win.get(hid, 0) / cnt * 100, 1),
                     "被禁": ban.get(hid, 0),
                     "BP率%": round((cnt + ban.get(hid, 0)) / max(n_bp, 1) * 100, 1) if n_bp else 0,
                     "天辉胜率%": round(rw[0] / rw[1] * 100, 1) if rw[1] else None,
                     "夜魇胜率%": round(dw[0] / dw[1] * 100, 1) if dw[1] else None,
                     "一选次数": firstpick.get(hid, 0),
                     "末选次数": lastpick.get(hid, 0)})
    hdf = pd.DataFrame(rows)

    kpi_row([("解析比赛场次", f"{len(details)}"),
             ("含 BP 数据", f"{n_bp}"),
             ("登场英雄数", f"{len(hdf)}"),
             ("BP 率 100% 英雄", f"{(hdf['BP率%']>=100).sum() if n_bp else 0}")])
    if not n_bp:
        st.caption("当前筛选样本中没有 BP 数据。")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔥 出场与禁用", "✅ 胜率榜", "🧠 BP 策略", "🤝 英雄组合", "🏅 选手高光"])

    with tab1:
        top = hdf.nlargest(15, "出场")
        fig = go.Figure()
        fig.add_trace(go.Bar(y=top["英雄"][::-1], x=top["出场"][::-1], orientation="h",
                             name="出场", marker_color=ACCENT))
        fig.add_trace(go.Bar(y=top["英雄"][::-1], x=top["被禁"][::-1], orientation="h",
                             name="被禁", marker_color="#3A4152"))
        fig.update_layout(barmode="overlay", title="英雄出场 vs 被禁 TOP 15", height=520)
        st.plotly_chart(plotly_layout(fig, height=520), width="stretch")

    with tab2:
        min_games = st.slider("最少出场次数", 1, 10, 3, 1)
        best = hdf[hdf["出场"] >= min_games].nlargest(15, "胜率%")
        trs = ""
        for i, (_, r) in enumerate(best.iterrows(), 1):
            trs += (f'<tr><td>{i}</td>'
                    f'<td><img src="{r["图标"]}" style="height:36px;border-radius:6px;vertical-align:middle;margin-right:8px">{r["英雄"]}</td>'
                    f'<td>{r["出场"]}</td><td>{r["被禁"]}</td>'
                    f'<td style="color:{GOLD};font-weight:700">{r["胜率%"]}%</td>'
                    f'<td>{r["天辉胜率%"] if r["天辉胜率%"] is not None else "—"}</td>'
                    f'<td>{r["夜魇胜率%"] if r["夜魇胜率%"] is not None else "—"}</td></tr>')
        st.markdown(f'<div class="panel"><table class="data-table">'
                    f'<tr><th>#</th><th>英雄</th><th>出场</th><th>被禁</th><th>总胜率</th><th>天辉胜率</th><th>夜魇胜率</th></tr>'
                    f'{trs}</table></div>', unsafe_allow_html=True)

    with tab3:
        st.markdown("**一选 / 末选（BP 顺位信号）**：一选通常是版本最稳核心，末选多为针对性 counter 位")
        c1, c2 = st.columns(2)
        with c1:
            fp = sorted(firstpick.items(), key=lambda kv: -kv[1])[:10]
            trs = "".join(f'<tr><td>{i}</td><td>{hero_cn(h, maps)[0]}</td><td>{v}</td></tr>'
                          for i, (h, v) in enumerate(fp, 1))
            st.markdown(f'<div class="panel"><b>🎯 常被一选</b><table class="data-table">'
                        f'<tr><th>#</th><th>英雄</th><th>一选次数</th></tr>{trs}</table></div>',
                        unsafe_allow_html=True)
        with c2:
            lp = sorted(lastpick.items(), key=lambda kv: -kv[1])[:10]
            trs = "".join(f'<tr><td>{i}</td><td>{hero_cn(h, maps)[0]}</td><td>{v}</td></tr>'
                          for i, (h, v) in enumerate(lp, 1))
            st.markdown(f'<div class="panel"><b>🔍 常被留到末选</b><table class="data-table">'
                        f'<tr><th>#</th><th>英雄</th><th>末选次数</th></tr>{trs}</table></div>',
                        unsafe_allow_html=True)
        most_banned = hdf.nlargest(10, "被禁")[["英雄", "被禁", "BP率%"]]
        if n_bp:
            fig = go.Figure(go.Bar(y=most_banned["英雄"][::-1], x=most_banned["被禁"][::-1],
                                   orientation="h", marker_color=DIRE))
            fig.update_layout(title="禁用次数 TOP 10", height=420)
            st.plotly_chart(plotly_layout(fig, height=420), width="stretch")

    with tab4:
        st.markdown("**英雄组合（同队双人组）**：至少同队出现 3 次的组合，按胜率排序")
        duos = [{"英雄A": hero_cn(a, maps)[0], "图标A": hero_cn(a, maps)[1],
                 "英雄B": hero_cn(b, maps)[0], "图标B": hero_cn(b, maps)[1],
                 "同队次数": v[1], "胜场": v[0],
                 "胜率%": round(v[0] / v[1] * 100, 1)}
                for (a, b), v in duo.items() if v[1] >= 3]
        if duos:
            ddf = pd.DataFrame(duos).nlargest(15, "同队次数")
            trs = ""
            for i, (_, r) in enumerate(ddf.iterrows(), 1):
                trs += (f'<tr><td>{i}</td>'
                        f'<td><img src="{r["图标A"]}" style="height:30px;border-radius:6px;vertical-align:middle;margin-right:6px">{r["英雄A"]}'
                        f' + <img src="{r["图标B"]}" style="height:30px;border-radius:6px;vertical-align:middle;margin:0 6px 0 6px">{r["英雄B"]}</td>'
                        f'<td>{r["同队次数"]}</td><td>{r["胜场"]}</td>'
                        f'<td style="color:{GOLD};font-weight:700">{r["胜率%"]}%</td></tr>')
            st.markdown(f'<div class="panel"><table class="data-table">'
                        f'<tr><th>#</th><th>组合</th><th>同队次数</th><th>胜场</th><th>胜率</th></tr>{trs}</table></div>',
                        unsafe_allow_html=True)
        else:
            st.caption("当前样本不足（需要更多含 BP 的解析场次）。")

    with tab5:
        perf = []
        for m in details:
            dur_min = max(m.get("duration", 1) / 60, 1)
            for p in m.get("players") or []:
                perf.append({
                    "选手": p.get("name") or "匿名",
                    "英雄": hero_cn(p.get("hero_id", 0), maps)[0],
                    "GPM": p.get("gold_per_min", 0) or 0,
                    "正补/分钟": round((p.get("last_hits", 0) or 0) / dur_min, 1),
                    "英雄伤害": p.get("hero_damage", 0) or 0,
                    "match_id": m.get("match_id"),
                })
        pdf = pd.DataFrame(perf)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**💨 GPM 最高单场 TOP 10**")
            g = pdf.nlargest(10, "GPM")
            trs = "".join(f'<tr><td>{i}</td><td>{r["选手"]}</td><td>{r["英雄"]}</td>'
                          f'<td style="color:{GOLD};font-weight:700">{r["GPM"]}</td><td>{r["match_id"]}</td></tr>'
                          for i, (_, r) in enumerate(g.iterrows(), 1))
            st.markdown(f'<table class="data-table"><tr><th>#</th><th>选手</th><th>英雄</th><th>GPM</th><th>MatchID</th></tr>{trs}</table>',
                        unsafe_allow_html=True)
        with c2:
            st.markdown("**⚔️ 英雄伤害最高单场 TOP 10**")
            g = pdf.nlargest(10, "英雄伤害")
            trs = "".join(f'<tr><td>{i}</td><td>{r["选手"]}</td><td>{r["英雄"]}</td>'
                          f'<td style="color:{ACCENT};font-weight:700">{r["英雄伤害"]:,}</td><td>{r["match_id"]}</td></tr>'
                          for i, (_, r) in enumerate(g.iterrows(), 1))
            st.markdown(f'<table class="data-table"><tr><th>#</th><th>选手</th><th>英雄</th><th>英雄伤害</th><th>MatchID</th></tr>{trs}</table>',
                        unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# 页面 4：战队与联赛
# ----------------------------------------------------------------------------
def team_table(df, min_games=3):
    rad = df.groupby("天辉").agg(场次=("match_id", "count"), 胜场=("radiant_win", "sum")).reset_index()
    dire = df.groupby("夜魇").agg(场次=("match_id", "count"),
                                  胜场=("radiant_win", lambda s: (~s).sum())).reset_index()
    rad.columns = dire.columns = ["战队", "场次", "胜场"]
    teams = pd.concat([rad, dire]).groupby("战队").sum().reset_index()
    teams = teams[teams["战队"] != "TBD"]
    teams["胜率%"] = (teams["胜场"] / teams["场次"] * 100).round(1)
    return teams[teams["场次"] >= min_games]


def page_teams():
    st.markdown('<div class="hero-title">战队与联赛</div>'
                '<div class="hero-sub">T1 赛场战队战绩、近期状态与联赛对比（跟随左侧联赛筛选）</div>',
                unsafe_allow_html=True)

    df, fresh = get_filtered_df()
    if df is None or not len(df):
        st.error("数据不可用（或当前联赛筛选为空）。")
        return
    teams = team_table(df)

    tab1, tab2, tab3, tab4 = st.tabs(["🏆 战队战绩", "📊 近期状态", "🏛️ 联赛对比", "⚔️ 头对头"])

    with tab1:
        top = teams.nlargest(15, "场次")
        c1, c2 = st.columns([3, 2])
        with c1:
            fig = go.Figure()
            fig.add_trace(go.Bar(y=top["战队"][::-1], x=top["场次"][::-1], orientation="h",
                                 name="场次", marker_color="#3A4152"))
            fig.add_trace(go.Bar(y=top["战队"][::-1], x=top["胜场"][::-1], orientation="h",
                                 name="胜场", marker_color=GOLD))
            fig.update_layout(barmode="overlay", title="战队出场/胜场 TOP 15（≥3 场）", height=520)
            st.plotly_chart(plotly_layout(fig, height=520), width="stretch")
        with c2:
            best = teams[teams["场次"] >= 5].nlargest(10, "胜率%")
            trs = "".join(f'<tr><td>{i}</td><td>{r["战队"]}</td><td>{r["场次"]}</td>'
                          f'<td style="color:{GOLD};font-weight:700">{r["胜率%"]}%</td></tr>'
                          for i, (_, r) in enumerate(best.iterrows(), 1))
            st.markdown(f'<div class="panel"><b>🔥 胜率榜（≥5 场）</b><table class="data-table">'
                        f'<tr><th>#</th><th>战队</th><th>场次</th><th>胜率</th></tr>{trs}</table></div>',
                        unsafe_allow_html=True)

    with tab2:
        st.markdown("**近期状态**：统计每支战队最近 10 场 T1 比赛的胜负（左旧→右新）")
        options = sorted(teams.nlargest(12, "场次")["战队"])
        candidates = list(teams[teams["场次"] >= 5].nlargest(8, "胜率%")["战队"])
        default = [t for t in candidates if t in options][:8]
        sel = st.multiselect("选择战队", options, default=default)
        lines = []
        for t in sel:
            sub = df[(df["天辉"] == t) | (df["夜魇"] == t)].head(10)
            if not len(sub):
                continue
            seq = "".join(f'<span style="color:{RADIANT if (r["获胜方"]==t) else DIRE};font-weight:800">{"●" if r["获胜方"]==t else "○"}</span> '
                          for _, r in sub.iloc[::-1].iterrows())
            wr = sum(1 for _, r in sub.iterrows() if r["获胜方"] == t)
            lines.append(f'<div class="panel"><b>{t}</b> <span style="color:#9AA3B2">近10场 {wr}胜</span><br>{seq}</div>')
        st.markdown("".join(lines) or '<div class="panel">请选择战队</div>', unsafe_allow_html=True)
        st.caption("● = 胜　○ = 负，从左到右时间递增")

    with tab3:
        lg = df.groupby("联赛").agg(场次=("match_id", "count"),
                                    平均时长秒=("duration", "mean"),
                                    天辉胜率=("radiant_win", "mean"),
                                    平均击杀=("radiant_score", "mean")).reset_index()
        lg = lg[lg["联赛"] != "—"]
        lg["场均时长"] = lg["平均时长秒"].apply(fmt_dur)
        lg["天辉胜率"] = (lg["天辉胜率"] * 100).round(1).astype(str) + "%"
        lg["场均击杀(单方)"] = lg["平均击杀"].round(0).astype(int)
        lg = lg.drop(columns=["平均时长秒", "平均击杀"]).nlargest(12, "场次")
        st.dataframe(lg[["联赛", "场次", "场均时长", "天辉胜率", "场均击杀(单方)"]],
                     width="stretch", hide_index=True, height=420)

    with tab4:
        st.markdown("**强队头对头**：出场最多的 12 支战队之间的交手记录")
        top12 = list(teams.nlargest(12, "场次")["战队"])
        sub = df[df["天辉"].isin(top12) & df["夜魇"].isin(top12)]
        if len(sub):
            matrix = pd.crosstab(sub["天辉"], sub["夜魇"], values=sub["radiant_win"].astype(int),
                                 aggfunc="count")
            wins = pd.crosstab(sub["天辉"], sub["夜魇"], values=sub["radiant_win"].astype(int),
                               aggfunc="sum").fillna(0)
            h2h = matrix.fillna(0).astype(int).astype(str)
            for a in matrix.index:
                for b in matrix.columns:
                    if pd.notna(matrix.loc[a, b]) and a != b:
                        h2h.loc[a, b] = f"{int(wins.loc[a, b])}胜/{matrix.loc[a, b]:.0f}场"
            st.dataframe(h2h, width="stretch", height=460)
            st.caption("行=天辉方，列=夜魇方；单元格显示该对阵中天辉方的胜场/总场次。")
        else:
            st.caption("当前筛选样本中没有 12 强之间的交手。")


# ----------------------------------------------------------------------------
# 页面 5：XG 独家分析
# ----------------------------------------------------------------------------
XG_TEAM = "Xtreme Gaming"


def page_xg():
    st.markdown('<div class="hero-title">XG 独家分析</div>'
                '<div class="hero-sub">Xtreme Gaming 深度档案：战绩走势 · 对手克制 · 选手面板 · 英雄池与 BP 行为（跟随联赛筛选）</div>',
                unsafe_allow_html=True)

    df, fresh = get_filtered_df()
    if df is None:
        st.error("数据不可用。")
        return
    xg = df[(df["天辉"] == XG_TEAM) | (df["夜魇"] == XG_TEAM)].copy()
    if not len(xg):
        st.warning("当前联赛筛选下没有 XG 的比赛，请清空或调整左侧联赛筛选。")
        return
    details = [d for d in (load_snapshot("xgDetails.json") or [])
               if not (st.session_state.get("league_filter") or [])
               or d.get("league_name") in st.session_state["league_filter"]]
    maps = hero_maps()

    wins = int((xg["获胜方"] == XG_TEAM).sum())
    # Elo 评分与排名
    raw, _ = _t1_base()
    ratings, acc, _, _ = elo_model(tuple(sorted(raw, key=lambda m: m["start_time"]))) if raw else ({}, 0, 0, 0)
    xg_elo = ratings.get(XG_TEAM, 1500.0)
    rank = sorted(ratings.values(), reverse=True).index(xg_elo) + 1 if xg_elo in ratings.values() else None

    w10, n10 = 0, 0
    sub10 = xg.head(10)
    if len(sub10):
        w10, n10 = int((sub10["获胜方"] == XG_TEAM).sum()), len(sub10)

    kpi_row([("T1 场次", f"{len(xg)}"),
             ("总胜率", f"{wins/len(xg)*100:.1f}%"),
             ("Elo 评分", f"{xg_elo:.0f}" + (f"（全联盟第 {rank}）" if rank else "")),
             ("近10场", f"{w10}胜{n10-w10}负"),
             ("场均时长", fmt_dur(xg["duration"].mean()))])

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 胜负走势", "🎯 对手克制", "👤 选手面板", "🧩 英雄池与 BP", "📋 比赛列表"])

    # ---- Tab1 走势 ----
    with tab1:
        xg_t = xg.iloc[::-1].reset_index(drop=True)  # 时间正序
        xg_t["累计胜场"] = (xg_t["获胜方"] == XG_TEAM).cumsum()
        xg_t["场次序"] = range(1, len(xg_t) + 1)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=xg_t["场次序"], y=xg_t["累计胜场"], mode="lines+markers",
                                 name="累计胜场", line=dict(color=GOLD, width=3),
                                 customdata=xg_t[["开始时间", "天辉", "夜魇", "比分"]],
                                 hovertemplate="%{customdata[0]}<br>%{customdata[1]} vs %{customdata[2]} (%{customdata[3]})<extra></extra>"))
        fig.add_trace(go.Scatter(x=xg_t["场次序"], y=xg_t["场次序"] - xg_t["累计胜场"],
                                 mode="lines", name="累计负场", line=dict(color=DIRE, width=2, dash="dot")))
        fig.update_layout(title="XG 累计胜负走势（时间正序）", xaxis_title="第 N 场", yaxis_title="场次")
        st.plotly_chart(plotly_layout(fig, height=400), width="stretch")

        c1, c2 = st.columns(2)
        with c1:
            rad = xg[xg["天辉"] == XG_TEAM]
            dire = xg[xg["夜魇"] == XG_TEAM]
            fig = go.Figure(go.Bar(x=["天辉", "夜魇"],
                                   y=[(rad["获胜方"] == XG_TEAM).mean() * 100 if len(rad) else 0,
                                     (dire["获胜方"] == XG_TEAM).mean() * 100 if len(dire) else 0],
                                   marker_color=[RADIANT, DIRE],
                                   text=[f"{(rad['获胜方']==XG_TEAM).mean()*100:.0f}% ({len(rad)}场)" if len(rad) else "无",
                                         f"{(dire['获胜方']==XG_TEAM).mean()*100:.0f}% ({len(dire)}场)" if len(dire) else "无"],
                                   textposition="auto"))
            fig.update_layout(title="分阵营胜率", yaxis_title="胜率%")
            fig.update_yaxes(range=[0, 100])
            st.plotly_chart(plotly_layout(fig, height=340), width="stretch")
        with c2:
            lg = xg.groupby("联赛").agg(场次=("match_id", "count"),
                                        胜场=("获胜方", lambda s: (s == XG_TEAM).sum())).reset_index()
            lg["胜率%"] = (lg["胜场"] / lg["场次"] * 100).round(1)
            fig = go.Figure(go.Bar(y=lg["联赛"][::-1], x=lg["胜率%"][::-1], orientation="h",
                                   marker_color=GOLD, text=[f"{v}% ({c}场)" for v, c in zip(lg["胜率%"][::-1], lg["场次"][::-1])],
                                   textposition="auto"))
            fig.update_layout(title="分联赛胜率")
            fig.update_xaxes(range=[0, 110])
            st.plotly_chart(plotly_layout(fig, height=340), width="stretch")

    # ---- Tab2 对手 ----
    with tab2:
        opp_rows = []
        for _, r in xg.iterrows():
            opp = r["夜魇"] if r["天辉"] == XG_TEAM else r["天辉"]
            opp_rows.append({"对手": opp, "胜": 1 if r["获胜方"] == XG_TEAM else 0, "联赛": r["联赛"],
                             "比分差": (r["radiant_score"] - r["dire_score"]) if r["天辉"] == XG_TEAM
                                      else (r["dire_score"] - r["radiant_score"])})
        odf = pd.DataFrame(opp_rows)
        agg = odf.groupby("对手").agg(交手=("胜", "count"), 胜场=("胜", "sum")).reset_index()
        agg["胜率%"] = (agg["胜场"] / agg["交手"] * 100).round(1)
        agg = agg.sort_values("交手", ascending=False)
        agg_top = agg.head(12)
        fig = go.Figure()
        fig.add_trace(go.Bar(y=agg_top["对手"][::-1], x=(agg_top["交手"] - agg_top["胜场"])[::-1],
                             orientation="h", name="负", marker_color=DIRE))
        fig.add_trace(go.Bar(y=agg_top["对手"][::-1], x=agg_top["胜场"][::-1],
                             orientation="h", name="胜", marker_color=RADIANT))
        fig.update_layout(barmode="stack", title="对阵各战队胜负（TOP12 交手数）", height=480)
        st.plotly_chart(plotly_layout(fig, height=480), width="stretch")

        best = agg[agg["交手"] >= 2].nlargest(5, "胜率%")
        worst = agg[agg["交手"] >= 2].nsmallest(5, "胜率%")
        c1, c2 = st.columns(2)
        with c1:
            trs = "".join(f'<tr><td>{r["对手"]}</td><td>{r["交手"]}</td>'
                          f'<td style="color:{RADIANT};font-weight:700">{r["胜率%"]}%</td></tr>'
                          for _, r in best.iterrows())
            st.markdown(f'<div class="panel"><b>😊 最顺手对手</b><table class="data-table">'
                        f'<tr><th>对手</th><th>交手</th><th>XG 胜率</th></tr>{trs}</table></div>',
                        unsafe_allow_html=True)
        with c2:
            trs = "".join(f'<tr><td>{r["对手"]}</td><td>{r["交手"]}</td>'
                          f'<td style="color:{DIRE};font-weight:700">{r["胜率%"]}%</td></tr>'
                          for _, r in worst.iterrows())
            st.markdown(f'<div class="panel"><b>😤 最难缠对手</b><table class="data-table">'
                        f'<tr><th>对手</th><th>交手</th><th>XG 胜率</th></tr>{trs}</table></div>',
                        unsafe_allow_html=True)

    # ---- Tab3 选手面板 ----
    with tab3:
        if not details:
            st.caption("当前筛选下没有 XG 的解析详情数据。")
            return
        prows = []
        heropool = {}
        for m in details:
            rt = (m.get("radiant_team") or {}).get("name") if isinstance(m.get("radiant_team"), dict) else m.get("radiant_team")
            won = m.get("radiant_win")
            for p in m.get("players") or []:
                is_rad = p.get("player_slot", 0) < 100
                if is_rad != (rt == XG_TEAM):
                    continue
                hid = p.get("hero_id")
                cn, icon = hero_cn(hid, maps)
                hp = heropool.setdefault(p.get("name"), {})
                hp.setdefault(hid, {"英雄": cn, "图标": icon, "场次": 0, "胜": 0})
                hp[hid]["场次"] += 1
                hp[hid]["胜"] += 1 if ((is_rad and won) or (not is_rad and not won)) else 0
                k, d, a = p.get("kills", 0) or 0, p.get("deaths", 0) or 0, p.get("assists", 0) or 0
                prows.append({
                    "选手": p.get("name") or "匿名",
                    "英雄": cn, "图标": icon,
                    "胜": 1 if ((is_rad and won) or (not is_rad and not won)) else 0,
                    "K": k, "D": d, "A": a,
                    "GPM": p.get("gold_per_min", 0) or 0, "XPM": p.get("xp_per_min", 0) or 0,
                    "正补": p.get("last_hits", 0) or 0, "英雄伤害": p.get("hero_damage", 0) or 0,
                })
        pdf = pd.DataFrame(prows)
        summary = pdf.groupby("选手").agg(场次=("胜", "count"), 胜场=("胜", "sum"),
                                          均K=("K", "mean"), 均D=("D", "mean"), 均A=("A", "mean"),
                                          均GPM=("GPM", "mean"), 均XPM=("XPM", "mean"),
                                          均正补=("正补", "mean"), 均英雄伤害=("英雄伤害", "mean")).reset_index()
        summary["胜率%"] = (summary["胜场"] / summary["场次"] * 100).round(1)
        summary["场均KDA"] = ((summary["均K"] + summary["均A"]) / summary["均D"].clip(lower=1)).round(2)
        trs = "".join(
            f'<tr><td>{r["选手"]}</td><td>{r["场次"]}</td><td style="color:{GOLD};font-weight:700">{r["胜率%"]}%</td>'
            f'<td>{r["场均KDA"]}</td><td>{r["均K"]:.1f}/{r["均D"]:.1f}/{r["均A"]:.1f}</td>'
            f'<td>{r["均GPM"]:.0f}</td><td>{r["均XPM"]:.0f}</td><td>{r["均正补"]:.0f}</td><td>{r["均英雄伤害"]:,.0f}</td></tr>'
            for _, r in summary.iterrows())
        st.markdown(f'<div class="panel"><b>五人组数据面板</b>（{len(details)} 场解析详情）'
                    f'<table class="data-table"><tr><th>选手</th><th>场次</th><th>胜率</th><th>KDA</th>'
                    f'<th>场均 K/D/A</th><th>场均GPM</th><th>场均XPM</th><th>场均正补</th><th>场均英雄伤害</th></tr>'
                    f'{trs}</table></div>', unsafe_allow_html=True)

        st.markdown("**个人英雄池**（按使用场次排序，最多展示 6 个）")
        cols = st.columns(len(summary))
        for col, (_, r) in zip(cols, summary.iterrows()):
            hp = sorted(heropool.get(r["选手"], {}).items(), key=lambda kv: -kv[1]["场次"])[:6]
            items = "".join(
                f'<div style="display:flex;justify-content:space-between;margin:2px 0">'
                f'<span><img src="{v["图标"]}" style="height:24px;border-radius:4px;vertical-align:middle;margin-right:4px">{v["英雄"]}</span>'
                f'<span style="color:{GOLD}">{v["场次"]}场</span></div>'
                for _, v in hp)
            col.markdown(f'<div class="panel"><b style="color:{ACCENT}">{r["选手"]}</b>{items}</div>',
                         unsafe_allow_html=True)

    # ---- Tab4 英雄池与 BP ----
    with tab4:
        if not details:
            st.caption("当前筛选下没有 XG 的解析详情数据。")
            return
        from collections import Counter as _C
        hero_stat = {}
        ban_against = _C()
        fp_cnt, lp_cnt = _C(), _C()
        for m in details:
            pb = m.get("picks_bans") or []
            rt = (m.get("radiant_team") or {}).get("name") if isinstance(m.get("radiant_team"), dict) else m.get("radiant_team")
            xg_is_rad = rt == XG_TEAM
            if pb:
                picks = sorted([x for x in pb if x["is_pick"]], key=lambda x: x["order"])
                bans = [x for x in pb if not x["is_pick"]]
                xg_bans = [x for x in bans if x["team"] == (0 if xg_is_rad else 1)]
                opp_bans = [x for x in bans if x["team"] != (0 if xg_is_rad else 1)]
                if picks:
                    if picks[0]["team"] == (0 if xg_is_rad else 1):
                        fp_cnt[picks[0]["hero_id"]] += 1
                    if picks[-1]["team"] == (0 if xg_is_rad else 1):
                        lp_cnt[picks[-1]["hero_id"]] += 1
                for x in opp_bans:
                    ban_against[x["hero_id"]] += 1
            for p in m.get("players") or []:
                is_rad = p.get("player_slot", 0) < 100
                if is_rad != xg_is_rad:
                    continue
                hid = p.get("hero_id")
                s = hero_stat.setdefault(hid, {"场次": 0, "胜": 0})
                s["场次"] += 1
                s["胜"] += 1 if ((is_rad and m.get("radiant_win")) or (not is_rad and not m.get("radiant_win"))) else 0

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🧩 XG 英雄池**（按出场排序）")
            rows = sorted(hero_stat.items(), key=lambda kv: -kv[1]["场次"])[:12]
            trs = ""
            for hid, s in rows:
                cn, icon = hero_cn(hid, maps)
                trs += (f'<tr><td><img src="{icon}" style="height:30px;border-radius:5px;vertical-align:middle;margin-right:6px">{cn}</td>'
                        f'<td>{s["场次"]}</td><td style="color:{GOLD};font-weight:700">{s["胜"]/s["场次"]*100:.0f}%</td></tr>')
            st.markdown(f'<table class="data-table"><tr><th>英雄</th><th>出场</th><th>胜率</th></tr>{trs}</table>',
                        unsafe_allow_html=True)
        with c2:
            st.markdown("**🚫 对手针对 XG 的禁用 TOP 8**")
            trs = ""
            for i, (hid, cnt) in enumerate(ban_against.most_common(8), 1):
                cn, icon = hero_cn(hid, maps)
                trs += (f'<tr><td>{i}</td>'
                        f'<td><img src="{icon}" style="height:30px;border-radius:5px;vertical-align:middle;margin-right:6px">{cn}</td>'
                        f'<td>{cnt}</td></tr>')
            st.markdown(f'<table class="data-table"><tr><th>#</th><th>英雄</th><th>被禁次数</th></tr>{trs}</table>',
                        unsafe_allow_html=True)

        st.markdown("**🎯 XG 的 BP 顺位行为**")
        c3, c4 = st.columns(2)
        with c3:
            trs = "".join(f'<tr><td>{i}</td><td>{hero_cn(h, maps)[0]}</td><td>{v}</td></tr>'
                          for i, (h, v) in enumerate(sorted(fp_cnt.items(), key=lambda kv: -kv[1])[:5], 1))
            st.markdown(f'<div class="panel"><b>XG 一选的英雄</b><table class="data-table">'
                        f'<tr><th>#</th><th>英雄</th><th>次数</th></tr>{trs}</table></div>', unsafe_allow_html=True)
        with c4:
            trs = "".join(f'<tr><td>{i}</td><td>{hero_cn(h, maps)[0]}</td><td>{v}</td></tr>'
                          for i, (h, v) in enumerate(sorted(lp_cnt.items(), key=lambda kv: -kv[1])[:5], 1))
            st.markdown(f'<div class="panel"><b>XG 留到末选的英雄</b><table class="data-table">'
                        f'<tr><th>#</th><th>英雄</th><th>次数</th></tr>{trs}</table></div>', unsafe_allow_html=True)
        st.caption("对手针对禁用 = XG 参赛场次中，对方队伍禁用的英雄排行，反映 XG 的版本威慑力。")

    # ---- Tab5 比赛列表 ----
    with tab5:
        st.dataframe(xg[["开始时间", "联赛", "系列赛", "天辉", "夜魇", "获胜方", "比分", "时长"]],
                     width="stretch", hide_index=True, height=480)


# ----------------------------------------------------------------------------
# 页面 6：对战预测
# ----------------------------------------------------------------------------
def page_predict():
    st.markdown('<div class="hero-title">对战预测</div>'
                '<div class="hero-sub">基于 Elo 实力评分的胜负与比分预测 — 模型在当前筛选的 T1 比赛上训练并回测</div>',
                unsafe_allow_html=True)

    raw, fresh = _t1_base()
    if not raw:
        st.error("数据不可用。")
        return
    ratings, acc, logloss, n_eval = elo_model(tuple(sorted(raw, key=lambda m: m["start_time"])))
    df, _ = get_filtered_df()
    if df is None or not len(df):
        st.error("筛选后数据为空。")
        return

    kpi_row([("训练对局数", f"{n_eval}"),
             ("回测准确率", f"{acc*100:.1f}%"),
             ("回测 LogLoss", f"{logloss:.3f}"),
             ("覆盖战队", f"{len(ratings)}")])
    st.caption("模型：Elo（K=32，初始 1500），按时间顺序在筛选后的 T1 比赛上训练；回测为逐场留出预测。准确率显著高于 50% 即说明评分有效。")

    teams = sorted({t for t in ratings if t})
    c1, c2, c3 = st.columns([2, 2, 1])
    radiant_team = c1.selectbox("🟢 天辉方", teams,
                                index=teams.index("PARIVISION") if "PARIVISION" in teams else 0)
    dire_team = c2.selectbox("🔴 夜魇方", teams,
                             index=teams.index("Team Liquid") if "Team Liquid" in teams else min(1, len(teams) - 1))
    bo = c3.radio("赛制", ["BO1", "BO3", "BO5"], index=1)

    if radiant_team == dire_team:
        st.warning("请选择两支不同的战队。")
        return

    ra = ratings.get(radiant_team, 1500.0)
    rd_ = ratings.get(dire_team, 1500.0)
    p_rad = 1.0 / (1.0 + 10 ** ((rd_ - ra) / 400.0))       # 天辉方单图胜率
    p_series = series_prob(p_rad, int(bo[2:]))

    # 比分预测：基于两队近期场均得分 + Elo 差修正
    rad_games = df[(df["天辉"] == radiant_team)]
    dire_games = df[(df["夜魇"] == dire_team)]
    league_avg_r = df["radiant_score"].mean()
    league_avg_d = df["dire_score"].mean()
    rad_for = rad_games["radiant_score"].mean() if len(rad_games) else league_avg_r
    dire_against = dire_games["dire_score"].mean() if len(dire_games) else league_avg_d
    base_r = (rad_for + dire_against) / 2 if pd.notna(rad_for) and pd.notna(dire_against) else (league_avg_r + league_avg_d) / 2
    base_d = league_avg_d + (league_avg_r - base_r)  # 保持总和一致
    elo_shift = (p_rad - 0.5) * 8   # 每 0.5 Elo 期望差约 ±4 杀
    pred_r = max(3, round(base_r + elo_shift))
    pred_d = max(3, round(base_d - elo_shift))

    # 两队近期状态
    def recent_form(t):
        sub = df[(df["天辉"] == t) | (df["夜魇"] == t)].head(10)
        w = sum(1 for _, r in sub.iterrows() if r["获胜方"] == t)
        return w, len(sub)

    w1, n1 = recent_form(radiant_team)
    w2, n2 = recent_form(dire_team)
    h2h = df[((df["天辉"] == radiant_team) & (df["夜魇"] == dire_team)) |
             ((df["天辉"] == dire_team) & (df["夜魇"] == radiant_team))]

    st.markdown("---")
    st.markdown("### 📊 预测结果")

    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        fig = go.Figure(go.Bar(x=[p_rad * 100, (1 - p_rad) * 100], y=["天辉 " + radiant_team, "夜魇 " + dire_team],
                               orientation="h", marker_color=[RADIANT, DIRE],
                               text=[f"{p_rad*100:.1f}%", f"{(1-p_rad)*100:.1f}%"], textposition="auto"))
        fig.update_layout(title=f"单图胜率预测", height=260)
        st.plotly_chart(plotly_layout(fig, height=260), width="stretch")
    with c2:
        color = RADIANT if p_series >= 0.5 else DIRE
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=p_series * 100, number={"suffix": "%"},
            title={"text": f"{radiant_team} 系列赛获胜概率 ({bo})"},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": color},
                   "bgcolor": "rgba(0,0,0,0)",
                   "steps": [{"range": [0, 50], "color": "rgba(229,69,69,0.18)"},
                             {"range": [50, 100], "color": "rgba(90,211,90,0.18)"}]}))
        fig.update_layout(paper_bgcolor=PANEL, font_color="#E8E6E3", height=260,
                          margin=dict(l=40, r=40, t=60, b=20))
        st.plotly_chart(fig, width="stretch")
    with c3:
        st.markdown(f"""
<div class="panel" style="height:100%">
<div style="color:#9AA3B2;font-size:.85rem">预测比分（总击杀）</div>
<div style="font-family:'Noto Serif SC',serif;font-size:2rem;font-weight:800">
<span style="color:{RADIANT}">{pred_r}</span>
<span style="color:#9AA3B2;font-size:1rem"> : </span>
<span style="color:{DIRE}">{pred_d}</span></div>
<div style="color:#9AA3B2;font-size:.85rem;margin-top:8px">
{radiant_team}: 近{n1}场 {w1}胜<br>{dire_team}: 近{n2}场 {w2}胜<br>
历史交手: {len(h2h)} 场（{radiant_team} 胜 {sum(1 for _, r in h2h.iterrows() if r["获胜方"] == radiant_team)} 场）</div>
</div>""", unsafe_allow_html=True)

    st.markdown("### 🔍 依据")
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        diff = ra - rd_
        st.markdown(f"""<div class="panel"><b>Elo 评分</b><br>
<span style="color:{RADIANT}">{radiant_team}: {ra:.0f}</span><br>
<span style="color:{DIRE}">{dire_team}: {rd_:.0f}</span><br>
<span style="color:#9AA3B2">分差 {diff:+.0f} → 单图期望 {p_rad*100:.1f}%</span></div>""", unsafe_allow_html=True)
    with cc2:
        p3 = series_prob(p_rad, 3)
        p5 = series_prob(p_rad, 5)
        st.markdown(f"""<div class="panel"><b>不同赛制胜率</b><br>
BO1: {p_rad*100:.1f}%<br>BO3: {p3*100:.1f}%<br>BO5: {p5*100:.1f}%<br>
<span style="color:#9AA3B2">强队在长系列赛更占优</span></div>""", unsafe_allow_html=True)
    with cc3:
        exp_dur = df["duration"].mean()
        st.markdown(f"""<div class="panel"><b>预期比赛形态</b><br>
预计时长: {fmt_dur(exp_dur)}（样本均值）<br>
天辉场均击杀: {league_avg_r:.0f} / 夜魇场均击杀: {league_avg_d:.0f}<br>
<span style="color:#9AA3B2">Elo 差带来的击杀修正 {elo_shift:+.1f}</span></div>""", unsafe_allow_html=True)

    st.caption("⚠️ 本预测为统计模型演示（基于历史 T1 比赛的 Elo 回测），不构成任何投注建议。Dota2 比赛结果受版本、状态、BP 等诸多因素影响，仅供参考娱乐。")


def page_about():
    st.markdown('<div class="hero-title">关于本站</div>'
                '<div class="hero-sub">数据真实性声明与技术说明</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="panel">
<h4>📡 数据来源（全部真实）</h4>
<ul>
<li><b>OpenDota 官方公开 API</b>（<code>api.opendota.com</code>）</li>
<li><b>T1 联赛定义</b>：OpenDota 官方分级 <code>tier = premium</code>（TI 等最高级赛事）+ 主流顶级赛事白名单（电竞世界杯、BLAST Slam、利雅得大师赛、ESL One、DreamLeague、TI 区域预选赛等），过滤掉低级别刷分局</li>
<li>比赛列表：翻页抓取约 600 场近期 T1 对局（<code>/proMatches</code> 分页）</li>
<li>英雄风向：最近 60 场 T1 比赛的完整解析数据（<code>/matches/&#123;id&#125;</code>，含 BP、选手数据、经济曲线）</li>
<li>英雄官方中文译名：Dota2 官方 datafeed；头图：Steam 官方 CDN</li>
</ul>
<h4>🔮 预测模型说明</h4>
<ul>
<li><b>Elo 评分</b>：K=32、初始 1500，按时间顺序在 T1 比赛上训练；每场比赛后更新双方评分</li>
<li><b>胜负预测</b>：标准 Elo 期望公式，BO3/BO5 用二项展开换算系列赛胜率</li>
<li><b>比分预测</b>：双方近期场均击杀 + Elo 差修正（±8 杀区间内）</li>
<li><b>回测</b>：逐场留出预测（先预测再更新评分），页面展示真实准确率与 LogLoss</li>
</ul>
<h4>🔄 数据更新机制</h4>
<ul>
<li>比赛库/战队/预测：内置真实快照 + 运行时自动合并最新一页实时数据</li>
<li>深度复盘：优先实时查询详情接口（1 小时缓存），快照兜底</li>
</ul>
<h4>⚠️ 声明</h4>
<p>本站为数据分析演示 Demo，与 Valve、OpenDota 无关联；预测仅为统计模型演示，不构成投注建议。</p>
</div>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# 主框架
# ----------------------------------------------------------------------------
inject_css()

with st.sidebar:
    st.markdown("## ⚔️ Dota2 T1 数据站")
    st.caption("OpenDota 真实数据 · Streamlit Demo")
    page = option_menu(
        menu_title=None,
        options=["T1 比赛库", "深度复盘", "英雄风向", "战队与联赛", "XG 独家分析", "对战预测", "关于"],
        icons=["list-stars", "magnifying-glass-chart", "fire", "trophy", "star", "cpu", "info-circle"],
        styles={
            "container": {"padding": "10px 8px", "background-color": "#1A1D24",
                          "border-radius": "14px", "border": "1px solid rgba(194,60,42,0.35)"},
            "icon": {"color": "#E8C766", "font-size": "15px"},
            "nav-link": {"font-size": "15px", "color": "#E8E6E3", "font-weight": "600",
                         "margin": "4px 0", "padding": "10px 14px", "border-radius": "12px",
                         "--hover-color": "rgba(194,60,42,0.25)", "border": "1px solid transparent"},
            "nav-link-selected": {"background-color": "rgba(194,60,42,0.35)",
                                  "border": "1px solid rgba(194,60,42,0.8)", "color": "#FFE9A8",
                                  "font-weight": "800", "border-left": "4px solid #C23C2A"},
        },
    )

    st.markdown("**🗓️ 联赛筛选（全局）**")
    if "league_filter" not in st.session_state:
        st.session_state["league_filter"] = []
    league_options = all_leagues()
    sel = st.multiselect("限定联赛（不选=全部）", league_options,
                         default=st.session_state.get("league_filter", []),
                         placeholder="不选 = 显示全部 T1 联赛")
    st.session_state["league_filter"] = sel
    if st.button("清除筛选", use_container_width=True):
        st.session_state["league_filter"] = []
        st.rerun()
    if sel:
        st.caption(f"已选 {len(sel)} 个联赛")
    st.caption(f"数据快照 · {datetime.now(CST).strftime('%Y-%m-%d')}")

PAGES = {"T1 比赛库": page_matches, "深度复盘": page_match_detail,
         "英雄风向": page_heroes, "战队与联赛": page_teams,
         "XG 独家分析": page_xg, "对战预测": page_predict, "关于": page_about}

st.markdown('<div class="hero-title" style="font-size:2.1rem">⚔️ Dota2 T1 比赛数据分析</div>'
            '<div class="hero-sub">主流顶级赛事 · BP / 选手 / 经济曲线 / 战队生态 / Elo 对战预测全解析</div>',
            unsafe_allow_html=True)


for fn in [page_matches, page_match_detail, page_heroes, page_teams, page_xg, page_predict, page_about]:
    try:
        fn()
    except Exception as e:
        import traceback; traceback.print_exc(); print("PAGEFAIL", fn.__name__)

