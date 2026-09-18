"""Dota2 职业比赛数据分析 Demo — 数据来源: OpenDota 官方公开 API（真实数据）"""
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
st.set_page_config(page_title="Dota2 比赛数据分析", page_icon="⚔️", layout="wide", initial_sidebar_state="expanded")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CST = timezone(timedelta(hours=8))

ACCENT = "#C23C2A"   # Dota2 红
GOLD = "#C9A227"
RADIANT = "#5AD35A"  # 天辉绿
DIRE = "#E54545"     # 夜魇红
BG = "#0F1116"
PANEL = "#1A1D24"


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
    """探活检查（5 分钟缓存），避免 OpenDota 宕机时每页都等超时。"""
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


def get_data(fname: str, api_path: str):
    """快照优先，然后尝试在线刷新（失败则用快照兜底）。"""
    snap = load_snapshot(fname)
    live = live_fetch(api_path)
    return live if live is not None else snap, (live is not None)


@st.cache_data(ttl=3600, show_spinner=False)
def hero_maps():
    """hero_id -> (中文名, 英文名, npc_name/图标)。合并官方中文名与 OpenDota constants。"""
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


def prepare_matches():
    matches, live = get_data("proMatches.json", "/proMatches")
    df = pd.DataFrame(matches)
    df["radiant_win"] = df["radiant_win"].astype(bool)
    df["开始时间"] = pd.to_datetime(df["start_time"], unit="s", utc=True).dt.tz_convert(CST).dt.strftime("%m-%d %H:%M")
    df["时长"] = df["duration"].apply(fmt_dur)
    df["比分"] = df["radiant_score"].astype(str) + " : " + df["dire_score"].astype(str)
    df["获胜方"] = df.apply(lambda r: r["radiant_name"] if r["radiant_win"] else r["dire_name"], axis=1)
    df["天辉"] = df["radiant_name"].fillna("TBD")
    df["夜魇"] = df["dire_name"].fillna("TBD")
    df["联赛"] = df["league_name"].fillna("—")
    df["系列赛"] = df["series_type"].map({0: "单场", 1: "BO3", 2: "BO5"})
    return df, live


# ----------------------------------------------------------------------------
# 页面 1：比赛库
# ----------------------------------------------------------------------------
def page_matches():
    st.markdown('<div class="hero-title">比赛库</div>'
                '<div class="hero-sub">全球职业赛场最近 100 场对局 — OpenDota 实时职业比赛库</div>',
                unsafe_allow_html=True)

    df, live = prepare_matches()
    if not len(df):
        st.error("职业比赛数据不可用（OpenDota 接口故障且无快照）。")
        return
    if not live:
        st.info("当前展示打包快照数据（OpenDota 实时接口暂不可用）。")

    kpi_row([("对局数量", f"{len(df)}"),
             ("平均时长", fmt_dur(df["duration"].mean())),
             ("天辉胜率", f"{df['radiant_win'].mean()*100:.1f}%"),
             ("平均总击杀", f"{(df['radiant_score']+df['dire_score']).mean():.0f}"),
             ("最长血战", fmt_dur(df['duration'].max()))])

    c1, c2, c3 = st.columns(3)
    q = c1.text_input("搜索战队/联赛", placeholder="如: Liquid, Paravision")
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


# ----------------------------------------------------------------------------
# 页面 2：深度复盘
# ----------------------------------------------------------------------------
def pb_badge(item, maps):
    cn, icon = hero_cn(item["hero_id"], maps)
    team = "天辉" if item["team"] == 0 else "夜魇"
    color = RADIANT if item["team"] == 0 else DIRE
    return (f'<span style="display:inline-flex;align-items:center;gap:4px;margin:3px 6px 3px 0;'
            f'padding:3px 8px;border-radius:8px;border:1px solid {color}55;background:rgba(255,255,255,0.03)">'
            f'<span style="color:{color};font-size:.72rem">{team}</span>'
            f'<span style="color:{color};font-weight:700">{item["order"]+1}</span>{cn}</span>')


def page_match_detail():
    st.markdown('<div class="hero-title">深度复盘</div>'
                '<div class="hero-sub">单场比赛全解析：BP 阶段、选手数据、经济/经验走势 — OpenDota 实时详情接口</div>',
                unsafe_allow_html=True)

    df, _ = prepare_matches()
    if not len(df):
        st.error("比赛列表不可用。")
        return

    maps = hero_maps()

    def label(r):
        win = "天辉" if r["radiant_win"] else "夜魇"
        return f'{r["开始时间"]} · {r["天辉"]} vs {r["夜魇"]} ({r["比分"]}) · {r["联赛"]}'

    pick = st.selectbox("选择一场比赛", df.head(40).index, format_func=lambda i: label(df.loc[i]))
    match_id = int(df.loc[pick, "match_id"])

    with st.spinner(f"拉取比赛 {match_id} 的完整详情..."):
        m = live_fetch(f"/matches/{match_id}")
    if not m:
        st.warning("详情接口暂时不可用（此项为实时查询，带 1 小时缓存）。请稍后重试。")
        return

    # 基本信息
    r_win = m.get("radiant_win")
    r_score, d_score = m.get("radiant_score", 0), m.get("dire_score", 0)
    league = df.loc[pick, "联赛"]
    winner = "🟢 天辉" if r_win else "🔴 夜魇"
    st.markdown(f"""
<div class="panel">
<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
<div>
<span style="font-size:1.5rem;font-weight:800;font-family:'Noto Serif SC',serif">
<span style="color:{RADIANT}">{m.get('radiant_team',{}).get('name','天辉')}</span>
<span style="color:#9AA3B2;font-size:1rem;margin:0 10px">{r_score} : {d_score}</span>
<span style="color:{DIRE}">{m.get('dire_team',{}).get('name','夜魇')}</span></span>
<div style="color:#9AA3B2;margin-top:6px">联赛 {league} · 时长 {fmt_dur(m.get('duration',0))} ·
获胜方 <b style="color:{RADIANT if r_win else DIRE}">{winner}</b> · MatchID {match_id}</div>
</div>
</div></div>""", unsafe_allow_html=True)

    # BP 阶段
    pb = m.get("picks_bans") or []
    if pb:
        picks = [x for x in pb if x["is_pick"]]
        bans = [x for x in pb if not x["is_pick"]]
        tab1, tab2, tab3 = st.tabs(["👤 选手数据", "🧩 阵容 (Pick)", "🚫 禁用 (Ban)"])
        with tab2:
            st.markdown("".join(pb_badge(x, maps) for x in sorted(picks, key=lambda x: x["order"])),
                        unsafe_allow_html=True)
        with tab3:
            st.markdown("".join(pb_badge(x, maps) for x in sorted(bans, key=lambda x: x["order"])),
                        unsafe_allow_html=True)
    else:
        tab1, = st.tabs(["👤 选手数据"])
        st.caption("该场比赛暂无 BP 数据（OpenDota 尚未解析或数据源缺失），展示选手数据。")

    with tab1:
        players = m.get("players") or []
        rows = []
        for p in players:
            cn, icon = hero_cn(p.get("hero_id", 0), maps)
            side = "天辉" if p.get("player_slot", 0) < 100 else "夜魇"
            rows.append({
                "阵营": side, "英雄": cn, "头像": icon,
                "选手": p.get("name") or p.get("personaname") or "匿名",
                "K/D/A": f'{p.get("kills",0)}/{p.get("deaths",0)}/{p.get("assists",0)}',
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
                        f'<td>{r["等级"]}</td><td>{r["GPM"]}</td><td>{r["XPM"]}</td>'
                        f'<td>{r["正补"]}/{r["反补"]}</td><td>{r["净资产"]:,}</td>'
                        f'<td>{r["英雄伤害"]:,}</td><td>{r["推塔伤害"]:,}</td><td>{r["治疗"]:,}</td></tr>')
            st.markdown(f'<div class="panel"><b style="color:{color};font-size:1.05rem">{side_name}方</b>'
                        f'<table class="data-table"><tr><th>英雄</th><th>选手</th><th>K/D/A</th><th>等级</th>'
                        f'<th>GPM</th><th>XPM</th><th>正/反补</th><th>净资产</th><th>英雄伤害</th><th>推塔伤害</th><th>治疗</th></tr>'
                        f'{trs}</table></div>', unsafe_allow_html=True)

    # 经济/经验曲线
    ga, xa = m.get("radiant_gold_adv"), m.get("radiant_xp_adv")
    if ga:
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=ga, mode="lines", name="天辉经济领先", line=dict(color=GOLD, width=2.5),
                                 fill="tozeroy" if sum(1 for x in ga if x >= 0) > len(ga) / 2 else None,
                                 fillcolor="rgba(201,162,39,0.12)"))
        if xa:
            fig.add_trace(go.Scatter(y=xa, mode="lines", name="天辉经验领先", line=dict(color="#5AA7E5", width=2)))
        fig.add_hline(y=0, line_color="rgba(255,255,255,0.3)")
        fig.update_layout(title="天辉视角 经济/经验领先曲线（正=天辉领先）",
                          xaxis_title="比赛分钟", yaxis_title="领先值")
        st.plotly_chart(plotly_layout(fig, height=440), width="stretch")

    # 目标物（objectives 为事件列表）
    obj = m.get("objectives") or []
    towers = [o for o in obj if o.get("type") == "building_kill" and "tower" in o.get("key", "")]
    rosh = [o for o in obj if o.get("type") == "CHAT_MESSAGE_ROSHAN_KILL"]
    if towers or rosh:
        rad_tower = sum(1 for o in towers if "badguys" in o.get("key", ""))   # 摧毁夜魇(坏家伙)建筑 → 天辉拿塔
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


# ----------------------------------------------------------------------------
# 页面 3：赛场统计
# ----------------------------------------------------------------------------
def page_stats():
    st.markdown('<div class="hero-title">赛场统计</div>'
                '<div class="hero-sub">近期职业赛场的宏观规律 — 基于比赛库聚合分析</div>',
                unsafe_allow_html=True)

    df, live = prepare_matches()
    if not len(df):
        st.error("数据不可用。")
        return
    if not live:
        st.info("当前展示打包快照数据（OpenDota 实时接口暂不可用）。")

    tab1, tab2, tab3 = st.tabs(["⏱️ 比赛形态", "🏛️ 联赛活跃度", "🏆 战队战绩"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            fig = px.histogram(df, x="duration", nbins=30, color_discrete_sequence=[ACCENT])
            fig.update_layout(title="比赛时长分布（秒）", xaxis_title="时长(秒)", yaxis_title="场次")
            st.plotly_chart(plotly_layout(fig), width="stretch")
        with c2:
            kills = df["radiant_score"] + df["dire_score"]
            fig = px.histogram(x=kills, nbins=25, color_discrete_sequence=[GOLD])
            fig.update_layout(title="双方总击杀分布", xaxis_title="总击杀", yaxis_title="场次")
            st.plotly_chart(plotly_layout(fig), width="stretch")
        kpi_row([("天辉胜率", f"{df['radiant_win'].mean()*100:.1f}%"),
                 ("夜魇胜率", f"{(1-df['radiant_win'].mean())*100:.1f}%"),
                 ("BO3及以上占比", f"{(df['series_type']>0).mean()*100:.0f}%"),
                 ("40分钟以上占比", f"{(df['duration']>2400).mean()*100:.0f}%")])

    with tab2:
        league = df.groupby("联赛").agg(场次=("match_id", "count"),
                                        平均时长秒=("duration", "mean")).reset_index()
        league = league[league["联赛"] != "—"].nlargest(12, "场次")
        fig = go.Figure(go.Bar(y=league["联赛"][::-1], x=league["场次"][::-1], orientation="h",
                               marker_color=GOLD))
        fig.update_layout(title="各联赛比赛场次 TOP 12")
        st.plotly_chart(plotly_layout(fig, height=480), width="stretch")

    with tab3:
        # 汇总每支战队在样本中的胜负
        rad = df.groupby("天辉").agg(场次=("match_id", "count"),
                                     胜场=("radiant_win", "sum")).reset_index()
        dire = df.groupby("夜魇").agg(场次=("match_id", "count"),
                                      胜场=("radiant_win", lambda s: (~s).sum())).reset_index()
        rad.columns = dire.columns = ["战队", "场次", "胜场"]
        teams = pd.concat([rad, dire]).groupby("战队").sum().reset_index()
        teams = teams[teams["战队"] != "TBD"]
        teams["胜率%"] = (teams["胜场"] / teams["场次"] * 100).round(1)
        teams = teams[teams["场次"] >= 3].nlargest(15, "场次")

        c1, c2 = st.columns([3, 2])
        with c1:
            fig = go.Figure()
            fig.add_trace(go.Bar(y=teams["战队"][::-1], x=teams["场次"][::-1], orientation="h",
                                 name="场次", marker_color="#3A4152"))
            fig.add_trace(go.Bar(y=teams["战队"][::-1], x=teams["胜场"][::-1], orientation="h",
                                 name="胜场", marker_color=GOLD))
            fig.update_layout(barmode="overlay", title="战队出场/胜场 TOP 15（≥3 场）")
            st.plotly_chart(plotly_layout(fig, height=520), width="stretch")
        with c2:
            best = teams[teams["场次"] >= 4].nlargest(8, "胜率%")
            rows = "".join(f'<tr><td>{i}</td><td>{r["战队"]}</td><td>{r["场次"]}</td>'
                           f'<td style="color:{GOLD};font-weight:700">{r["胜率%"]}%</td></tr>'
                           for i, (_, r) in enumerate(best.iterrows(), 1))
            st.markdown(f'<div class="panel"><b>🔥 近期胜率榜</b><table class="data-table">'
                        f'<tr><th>#</th><th>战队</th><th>场次</th><th>胜率</th></tr>{rows}</table></div>',
                        unsafe_allow_html=True)


def page_about():
    st.markdown('<div class="hero-title">关于本站</div>'
                '<div class="hero-sub">数据真实性声明与技术说明</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="panel">
<h4>📡 数据来源（全部真实）</h4>
<ul>
<li><b>OpenDota 官方公开 API</b>（<code>api.opendota.com</code>）——职业比赛列表（<code>/proMatches</code>）、单场完整详情（<code>/matches/&#123;id&#125;</code>：BP、选手数据、经济经验曲线、目标物）</li>
<li><b>Dota2 官方 datafeed</b>（<code>dota2.com/datafeed</code>）——英雄官方中文译名</li>
<li>英雄头图来自 Steam 官方 CDN</li>
</ul>
<h4>🔄 数据更新机制</h4>
<ul>
<li>比赛列表：内置真实快照 + 运行时自动刷新</li>
<li>单场深度复盘：实时查询 OpenDota 详情接口，带 1 小时缓存</li>
</ul>
<h4>⚠️ 声明</h4>
<p>本站为数据分析演示 Demo，与 Valve、OpenDota 无关联；数据仅作演示用途。</p>
</div>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# 主框架
# ----------------------------------------------------------------------------
inject_css()

with st.sidebar:
    st.markdown("## ⚔️ Dota2 比赛数据站")
    st.caption("OpenDota 真实数据 · Streamlit Demo")
    page = option_menu(
        menu_title=None,
        options=["比赛库", "深度复盘", "赛场统计", "关于"],
        icons=["list-stars", "magnifying-glass-chart", "bar-chart-line", "info-circle"],
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
    st.caption(f"数据快照 · {datetime.now(CST).strftime('%Y-%m-%d')}")

PAGES = {"比赛库": page_matches, "深度复盘": page_match_detail,
         "赛场统计": page_stats, "关于": page_about}

st.markdown('<div class="hero-title" style="font-size:2.1rem">⚔️ Dota2 比赛数据分析</div>'
            '<div class="hero-sub">基于 OpenDota 官方公开 API 的职业比赛深度分析 Demo</div>',
            unsafe_allow_html=True)


for fn in [page_matches, page_match_detail, page_stats, page_about]:
    try:
        fn()
    except Exception as e:
        import traceback; traceback.print_exc(); print("PAGEFAIL", fn.__name__)

