"""Dota2 T1 职业比赛数据分析 Demo — 数据来源: OpenDota 官方公开 API（真实数据）

T1 定义: OpenDota 官方联赛分级中的 premium（顶级）联赛，如 TI、利雅得大师赛、ESL One、DreamLeague 等。
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


@st.cache_data(ttl=3600, show_spinner=False)
def hero_maps():
    """hero_id -> (中文名, 图标)。合并官方中文名与 OpenDota constants。"""
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


def load_t1():
    df = load_snapshot("t1Matches.json")
    if df is None:
        return None, False
    leagues = load_snapshot("leagues.json") or []
    tier_map = {l["leagueid"]: l.get("tier") for l in leagues}
    fresh = [m for m in (live_fetch("/proMatches") or [])
             if is_t1(tier_map.get(m.get("leagueid")), m.get("league_name"))]
    seen, merged = set(m["match_id"] for m in df), list(df)
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


# ----------------------------------------------------------------------------
# 页面 1：比赛库
# ----------------------------------------------------------------------------
def page_matches():
    st.markdown('<div class="hero-title">T1 比赛库</div>'
                '<div class="hero-sub">主流顶级赛事：TI · 利雅得大师赛 · ESL One · 电竞世界杯 · BLAST Slam · DreamLeague 等 — premium 分级 + 顶级赛事白名单</div>',
                unsafe_allow_html=True)

    matches, fresh = load_t1()
    if not matches:
        st.error("比赛数据不可用。")
        return
    if not fresh:
        st.info("当前展示打包快照数据（OpenDota 实时接口暂不可用）。")
    df = t1_df(matches)

    kpi_row([("T1 对局数", f"{len(df)}"),
             ("覆盖联赛", f"{df['联赛'].nunique()}"),
             ("出场战队", f"{pd.concat([df['天辉'], df['夜魇']]).nunique()}"),
             ("平均时长", fmt_dur(df["duration"].mean())),
             ("平均总击杀", f"{(df['radiant_score']+df['dire_score']).mean():.0f}")])

    c1, c2, c3 = st.columns(3)
    q = c1.text_input("搜索战队/联赛", placeholder="如: Liquid, PARIVISION, ESL")
    side = c2.radio("阵营筛选", ["全部", "天辉获胜", "夜魇获胜"], horizontal=True)
    dur = c3.slider("时长下限（分钟）", 15, 90, 20, 5)

    lg = c1.multiselect("限定联赛", sorted(df["联赛"].unique()))
    view = df[df["duration"] >= dur * 60]
    if q:
        ql = q.lower()
        view = view[view.apply(lambda r: ql in str(r["天辉"]).lower() or ql in str(r["夜魇"]).lower()
                                         or ql in str(r["联赛"]).lower(), axis=1)]
    if lg:
        view = view[view["联赛"].isin(lg)]
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
    r_name = (m.get("radiant_team") or {}).get("name") or m.get("radiant_team") or "天辉"
    d_name = (m.get("dire_team") or {}).get("name") or m.get("dire_team") or "夜魇"
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
                "KDA值": round((p.get("kills",0)+p.get("assists",0))/max(p.get("deaths",0) or 1, 1), 2),
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
                        f'<td>{r["KDA值"]}</td><td>{r["GPM"]}</td><td>{r["XPM"]}</td>'
                        f'<td>{r["正补"]}/{r["反补"]}</td><td>{r["净资产"]:,}</td>'
                        f'<td>{r["英雄伤害"]:,}</td><td>{r["推塔伤害"]:,}</td><td>{r["治疗"]:,}</td></tr>')
            st.markdown(f'<div class="panel"><b style="color:{color};font-size:1.05rem">{side_name}方</b>'
                        f'<table class="data-table"><tr><th>英雄</th><th>选手</th><th>K/D/A</th><th>KDA</th>'
                        f'<th>GPM</th><th>XPM</th><th>正/反补</th><th>净资产</th><th>英雄伤害</th><th>推塔伤害</th><th>治疗</th></tr>'
                        f'{trs}</table></div>', unsafe_allow_html=True)
        st.caption("💡 表内数字为 OpenDota 解析的官方重放数据。")

    with tabs[1]:
        if pb:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🧩 Pick（按顺序）**")
                st.markdown("".join(pb_badge(x, maps) for x in sorted([p for p in pb if p["is_pick"]],
                                                                       key=lambda x: x["order"])),
                            unsafe_allow_html=True)
            with c2:
                st.markdown("**🚫 Ban（按顺序）**")
                st.markdown("".join(pb_badge(x, maps) for x in sorted([p for p in pb if not p["is_pick"]],
                                                                       key=lambda x: x["order"])),
                            unsafe_allow_html=True)
        else:
            st.caption("该场比赛暂无 BP 数据（OpenDota 尚未解析），可先看选手数据与曲线。")

    with tabs[2]:
        ga, xa = m.get("radiant_gold_adv"), m.get("radiant_xp_adv")
        if ga:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=ga, mode="lines", name="天辉经济领先", line=dict(color=GOLD, width=2.5)))
            if xa:
                fig.add_trace(go.Scatter(y=xa, mode="lines", name="天辉经验领先", line=dict(color="#5AA7E5", width=2)))
            fig.add_hline(y=0, line_color="rgba(255,255,255,0.3)")
            fig.update_layout(title="天辉视角 经济/经验领先曲线（正=天辉领先）",
                              xaxis_title="比赛分钟", yaxis_title="领先值")
            st.plotly_chart(plotly_layout(fig, height=440), width="stretch")
            flips = sum(1 for a, b in zip(ga, ga[1:]) if (a >= 0) != (b >= 0))
            lead = max(ga)
            trail = min(ga)
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
                '<div class="hero-sub">T1 比赛单场全解析：BP · 选手数据 · 经济曲线 · 目标物 — 优先实时接口，内置快照兜底</div>',
                unsafe_allow_html=True)

    matches, _ = load_t1()
    if not matches:
        st.error("比赛列表不可用。")
        return
    df = t1_df(matches)
    maps = hero_maps()

    def label(r):
        return f'{r["开始时间"]} · {r["天辉"]} vs {r["夜魇"]} ({r["比分"]}) · {r["联赛"]}'

    pick = st.selectbox("选择一场比赛", df.head(50).index, format_func=lambda i: label(df.loc[i]))
    row = df.loc[pick]
    match_id = int(row["match_id"])

    m = live_fetch(f"/matches/{match_id}")
    src = "OpenDota 实时接口"
    if not m:
        slim = [x for x in (load_snapshot("t1Details.json") or []) if x.get("match_id") == match_id]
        if slim:
            m, src = slim[0], "内置快照"
    if not m:
        st.warning("详情暂时不可用（实时接口故障且该场不在快照中）。")
        return
    st.caption(f"数据来源：{src}" + (" · 部分图表在快照模式下不可用" if src == "内置快照" else ""))
    render_match_detail(m, maps, row["联赛"])


# ----------------------------------------------------------------------------
# 页面 3：英雄风向
# ----------------------------------------------------------------------------
def page_heroes():
    st.markdown('<div class="hero-title">英雄风向</div>'
                '<div class="hero-sub">T1 赛场的英雄 BP 与表现统计 — 基于最近 60 场 T1 比赛的解析数据</div>',
                unsafe_allow_html=True)

    details = load_snapshot("t1Details.json") or []
    if not details:
        st.error("详情快照不可用。")
        return
    maps = hero_maps()

    # 聚合英雄出场/胜场/禁用
    pick, win, ban = {}, {}, {}
    n_bp = 0
    for m in details:
        for p in m.get("players") or []:
            hid = p.get("hero_id")
            pick[hid] = pick.get(hid, 0) + 1
            won = (p.get("player_slot", 0) < 100) == m.get("radiant_win")
            if won:
                win[hid] = win.get(hid, 0) + 1
        if m.get("picks_bans"):
            n_bp += 1
            for x in m["picks_bans"]:
                if not x["is_pick"]:
                    ban[x["hero_id"]] = ban.get(x["hero_id"], 0) + 1

    rows = []
    for hid, cnt in pick.items():
        cn, icon = hero_cn(hid, maps)
        rows.append({"英雄": cn, "图标": icon, "出场": cnt,
                     "胜率%": round(win.get(hid, 0) / cnt * 100, 1),
                     "被禁": ban.get(hid, 0)})
    hdf = pd.DataFrame(rows)

    kpi_row([("解析比赛场次", f"{len(details)}"),
             ("含 BP 数据", f"{n_bp}"),
             ("登场英雄数", f"{len(hdf)}"),
             ("登场英雄占比", f"{len(hdf)/127*100:.0f}%")])
    st.caption("注：BP 数据仅 OpenDota 已解析的比赛才有，样本量小于比赛总数。")

    tab1, tab2, tab3 = st.tabs(["🔥 出场热度", "✅ 胜率榜", "🏅 选手高光"])

    with tab1:
        top = hdf.nlargest(15, "出场")
        fig = go.Figure(go.Bar(y=top["英雄"][::-1], x=top["出场"][::-1], orientation="h",
                               marker_color=ACCENT, text=top["胜率%"][::-1],
                               texttemplate="%{x} 场 · 胜率 %{text}%", textposition="outside"))
        fig.update_layout(title="英雄出场次数 TOP 15", height=520)
        st.plotly_chart(plotly_layout(fig, height=520), width="stretch")

    with tab2:
        min_games = st.slider("最少出场次数", 1, 10, 3, 1)
        best = hdf[hdf["出场"] >= min_games].nlargest(15, "胜率%")
        trs = ""
        for i, (_, r) in enumerate(best.iterrows(), 1):
            trs += (f'<tr><td>{i}</td>'
                    f'<td><img src="{r["图标"]}" style="height:36px;border-radius:6px;vertical-align:middle;margin-right:8px">{r["英雄"]}</td>'
                    f'<td>{r["出场"]}</td><td>{r["被禁"]}</td>'
                    f'<td style="color:{GOLD};font-weight:700">{r["胜率%"]}%</td></tr>')
        st.markdown(f'<div class="panel"><table class="data-table">'
                    f'<tr><th>#</th><th>英雄</th><th>出场</th><th>被禁</th><th>胜率</th></tr>{trs}</table></div>',
                    unsafe_allow_html=True)

    with tab3:
        perf = []
        for m in details:
            dur_min = max(m.get("duration", 1) / 60, 1)
            for p in m.get("players") or []:
                perf.append({
                    "选手": p.get("name") or "匿名",
                    "hero_id": p.get("hero_id"),
                    "英雄": hero_cn(p.get("hero_id", 0), maps)[0],
                    "GPM": p.get("gold_per_min", 0) or 0,
                    "KDA": round(((p.get("kills", 0) or 0) + (p.get("assists", 0) or 0)) / max(p.get("deaths", 1) or 1, 1), 2),
                    "正补/分钟": round((p.get("last_hits", 0) or 0) / dur_min, 1),
                    "英雄伤害": p.get("hero_damage", 0) or 0,
                    "match_id": m.get("match_id"),
                })
        pdf = pd.DataFrame(perf)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**💨 GPM 最高单场 TOP 10**")
            g = pdf.nlargest(10, "GPM")[["选手", "英雄", "GPM", "match_id"]]
            trs = "".join(f'<tr><td>{i}</td><td>{r["选手"]}</td><td>{r["英雄"]}</td>'
                          f'<td style="color:{GOLD};font-weight:700">{r["GPM"]}</td><td>{r["match_id"]}</td></tr>'
                          for i, (_, r) in enumerate(g.iterrows(), 1))
            st.markdown(f'<table class="data-table"><tr><th>#</th><th>选手</th><th>英雄</th><th>GPM</th><th>MatchID</th></tr>{trs}</table>',
                        unsafe_allow_html=True)
        with c2:
            st.markdown("**⚔️ 英雄伤害最高单场 TOP 10**")
            g = pdf.nlargest(10, "英雄伤害")[["选手", "英雄", "英雄伤害", "match_id"]]
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
                '<div class="hero-sub">T1 赛场战队战绩、近期状态与联赛对比 — 全量聚合分析</div>',
                unsafe_allow_html=True)

    matches, fresh = load_t1()
    if not matches:
        st.error("数据不可用。")
        return
    if not fresh:
        st.info("当前展示打包快照数据（OpenDota 实时接口暂不可用）。")
    df = t1_df(matches)
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
        st.markdown("**近期状态**：统计每支战队最近 10 场 T1 比赛的胜负（左侧旧→右侧新）")
        options = sorted(teams.nlargest(12, "场次")["战队"])
        candidates = list(teams[teams["场次"] >= 5].nlargest(8, "胜率%")["战队"])
        default = [t for t in candidates if t in options][:8]
        sel = st.multiselect("选择战队（默认胜率榜前 8）", options, default=default)
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
        st.caption("时长/胜率差异能反映各联赛的版本环境与赛制强度。")

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
                        w = int(wins.loc[a, b])
                        h2h.loc[a, b] = f"{w}胜/{matrix.loc[a,b]:.0f}场"
            st.dataframe(h2h, width="stretch", height=460)
            st.caption("行=天辉方，列=夜魇方；单元格显示该对阵中天辉方的胜场/总场次。")
        else:
            st.caption("样本中没有 12 强之间的交手。")


def page_about():
    st.markdown('<div class="hero-title">关于本站</div>'
                '<div class="hero-sub">数据真实性声明与技术说明</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="panel">
<h4>📡 数据来源（全部真实）</h4>
<ul>
<li><b>OpenDota 官方公开 API</b>（<code>api.opendota.com</code>）</li>
<li><b>T1 联赛定义</b>：OpenDota 官方分级 <code>tier = premium</code>（TI 等最高级赛事）+ 主流顶级赛事白名单（电竞世界杯、BLAST Slam、利雅得大师赛、ESL One、DreamLeague、TI 区域预选赛等），过滤掉低级别刷分局</li>
<li>比赛列表：翻页抓取约 800 场近期 T1 对局（<code>/proMatches</code> 分页）</li>
<li>英雄风向：最近 60 场 T1 比赛的完整解析数据（<code>/matches/&#123;id&#125;</code>，含 BP、选手数据、经济曲线）</li>
<li>英雄官方中文译名：Dota2 官方 datafeed；头图：Steam 官方 CDN</li>
</ul>
<h4>🔄 数据更新机制</h4>
<ul>
<li>比赛库/战队联赛：内置真实快照 + 运行时自动合并最新一页实时数据</li>
<li>深度复盘：优先实时查询详情接口（1 小时缓存），快照兜底</li>
<li>英雄风向：基于打包的 60 场解析快照，保证加载速度</li>
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
    st.markdown("## ⚔️ Dota2 T1 数据站")
    st.caption("OpenDota premium 联赛 · Streamlit Demo")
    page = option_menu(
        menu_title=None,
        options=["T1 比赛库", "深度复盘", "英雄风向", "战队与联赛", "关于"],
        icons=["list-stars", "magnifying-glass-chart", "fire", "trophy", "info-circle"],
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

PAGES = {"T1 比赛库": page_matches, "深度复盘": page_match_detail,
         "英雄风向": page_heroes, "战队与联赛": page_teams, "关于": page_about}

st.markdown('<div class="hero-title" style="font-size:2.1rem">⚔️ Dota2 T1 比赛数据分析</div>'
            '<div class="hero-sub">仅收录 OpenDota premium 顶级联赛 · BP / 选手 / 经济曲线 / 战队生态全解析</div>',
            unsafe_allow_html=True)

PAGES[page]()
