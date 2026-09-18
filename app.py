"""Dota2 数据分析 Demo — 数据来源: OpenDota 官方公开 API + Dota2 官方 datafeed（真实数据）"""
import json
import os
import time
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
st.set_page_config(page_title="Dota2 数据分析站", page_icon="⚔️", layout="wide", initial_sidebar_state="expanded")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CST = timezone(timedelta(hours=8))

ATTR_CN = {0: "力量", 1: "敏捷", 2: "智力", 3: "全能"}
ATTR_EN = {0: "str", 1: "agi", 2: "int", 3: "univ"}
BRACKETS = {1: "先锋", 2: "卫士", 3: "中军", 4: "统帅", 5: "传奇", 6: "万古流芳", 7: "超凡入圣", 8: "冠绝一世"}

ACCENT = "#C23C2A"   # Dota2 红
GOLD = "#C9A227"
BG = "#0F1116"
PANEL = "#1A1D24"


def hero_icon(name: str) -> str:
    short = name.replace("npc_dota_hero_", "")
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
        req = urllib.request.Request("https://api.opendota.com/api/patches",
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
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


def get_data(fname: str, api_path: str):
    """快照优先，然后尝试在线刷新（失败则用快照兜底）。"""
    snap = load_snapshot(fname)
    live = live_fetch(api_path)
    return live if live is not None else snap, (live is not None)


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

    /* 侧边栏 */
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
    section[data-testid="stSidebar"] [data-baseweb="popover"] *,
    div[data-baseweb="popover"] * { color: #1A1D24 !important; }

    /* 标题 */
    h1, h2, h3 { font-family: 'Noto Serif SC', serif !important; color: #F5F2EC !important; }
    .hero-title {
        font-family: 'Noto Serif SC', serif; font-weight: 800;
        font-size: 2.6rem; line-height: 1.15;
        background: linear-gradient(90deg, #F5F2EC 20%%, #C9A227 65%%, #C23C2A 100%%);
        -webkit-background-clip: text; background-clip: text; color: transparent !important;
        margin-bottom: 0.2rem;
    }
    .hero-sub { color: #9AA3B2; font-size: 1.02rem; margin-bottom: 1.4rem; }

    /* KPI 卡片 */
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

    /* 面板卡 */
    .panel {
        background: linear-gradient(145deg, #1A1D24, #14161C);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 14px; padding: 18px 20px; margin-bottom: 12px;
    }
    .badge { display:inline-block; padding:2px 10px; border-radius:999px; font-size:.78rem;
             border:1px solid rgba(201,162,39,.5); color:#E8C766; margin-right:6px; }

    table.data-table { width: 100%%; border-collapse: collapse; }
    table.data-table th { color: #C9A227; text-align: left; font-weight: 700; padding: 8px 10px;
                          border-bottom: 1px solid rgba(201,162,39,.35); }
    table.data-table td { padding: 8px 10px; border-bottom: 1px solid rgba(255,255,255,.06); }

    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] { color: #9AA3B2 !important; border-radius: 10px 10px 0 0; }
    .stTabs [aria-selected="true"] { color: #E8C766 !important; }

    div[data-testid="stDataFrame"], div[data-testid="stTable"] { color: #E8E6E3; }
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
# 页面
# ----------------------------------------------------------------------------
def page_overview():
    st.markdown('<div class="hero-title">版本概览</div>'
                '<div class="hero-sub">天梯环境、天梯分分布与版本时间线 — 数据来自 OpenDota 官方公开 API</div>',
                unsafe_allow_html=True)

    patches, live1 = get_data("patches.json", "/patches")
    dist, live2 = get_data("distributions.json", "/distributions")
    heroes = load_snapshot("heroes_official.json")
    hero_stats, live3 = get_data("heroStats.json", "/heroStats")

    if not live1 or not live2 or not live3:
        st.info("当前 OpenDota 实时接口暂时不可用，正在展示随应用打包的真实数据快照。")

    n_heroes = len(hero_stats) if hero_stats else len(heroes["result"]["data"]["heroes"])
    kpis = [("当前版本", patches[0]["name"] if patches else "—")]
    if dist and "legacy" in dist:
        total_mmr = sum(r["cumulative_count"] for r in dist["legacy"]["rows"][:1])
        kpis.append(("天梯玩家样本(最近一次统计)", f"{dist['legacy']['rows'][-1]['cumulative_count']:,}"))
    kpis += [("收录英雄数", f"{n_heroes}"),
             ("快照生成时间", datetime.fromtimestamp(os.path.getmtime(os.path.join(DATA_DIR, 'heroes_official.json'))).strftime("%m-%d %H:%M"))]
    kpi_row(kpis)

    left, right = st.columns([3, 2])

    with left:
        st.markdown("##### 📈 天梯分分布")
        if dist and "legacy" in dist:
            rows = [{"分段": r["bin_name"], "人数": r["count"]} for r in dist["legacy"]["rows"]]
            df = pd.DataFrame(rows)
            fig = go.Figure(go.Bar(x=df["分段"], y=df["人数"], marker_color=ACCENT,
                                   marker_line_width=0))
            fig.update_layout(xaxis_tickangle=-45, title="MMR 分段人数分布（官方匹配池统计）")
            st.plotly_chart(plotly_layout(fig), use_container_width=True)

    with right:
        st.markdown("##### 🏅 竞技天梯段位分布")
        if dist and "competitive" in dist:
            rows = [{"段位": r["bin_name"], "占比": r["count"]} for r in dist["competitive"]["rows"]]
            df = pd.DataFrame(rows).head(15)
            fig = go.Figure(go.Bar(y=df["段位"][::-1], x=df["占比"][::-1], orientation="h",
                                   marker_color=GOLD, marker_line_width=0))
            st.plotly_chart(plotly_layout(fig, height=420), use_container_width=True)

    st.markdown("##### 🗓️ 版本时间线（近 10 个版本）")
    if patches:
        rows = [{"版本": p["name"], "发布日期": datetime.fromtimestamp(p["date"], CST).strftime("%Y-%m-%d"),
                 "游戏性更新天数": p.get("gameplay_patches", 0) if isinstance(p, dict) else None}
                for p in patches[:10]]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def hero_df_from_stats(hero_stats, heroes_official, bracket):
    if not hero_stats:
        return None
    name_cn = {}
    complexity = {}
    attr_idx = {}
    if heroes_official:
        for h in heroes_official["result"]["data"]["heroes"]:
            name_cn[h["id"]] = h["name_loc"]
            complexity[h["id"]] = h.get("complexity", 1)
            attr_idx[h["id"]] = h.get("primary_attr", 0)
    rows = []
    for h in hero_stats:
        pick, win = h.get(f"{bracket}_pick", 0), h.get(f"{bracket}_win", 0)
        if not pick:
            continue
        rows.append({
            "hero_id": h["id"], "英雄": h.get("localized_name", h["name"]),
            "图标": hero_icon(h["name"]),
            "中文名": name_cn.get(h["id"], h.get("localized_name", "")),
            "属性": ATTR_CN.get(attr_idx.get(h["id"], 3), "全能"),
            "属性En": ATTR_EN.get(attr_idx.get(h["id"], 3), "univ"),
            "复杂度": complexity.get(h["id"], 1),
            "选取次数": pick,
            "胜场": win,
            "胜率%": round(win / pick * 100, 2),
            "选取率%": None,  # 占位，调用方填
        })
    df = pd.DataFrame(rows)
    if len(df):
        total = df["选取次数"].sum()
        df["选取率%"] = (df["选取次数"] / total * 100).round(2)
    return df


def page_hero_meta():
    st.markdown('<div class="hero-title">天梯英雄梯度</div>'
                '<div class="hero-sub">胜率 × 选取率 × 强度梯度 — 按天梯分段筛选，OpenDota 全量对局统计</div>',
                unsafe_allow_html=True)

    hero_stats, live = get_data("heroStats.json", "/heroStats")
    heroes_official = load_snapshot("heroes_official.json")
    if not hero_stats:
        st.error("英雄统计数据不可用（OpenDota 接口故障且无快照）。")
        return
    if not live:
        st.info("当前展示打包快照数据（OpenDota 实时接口暂不可用）。")

    c1, c2, c3 = st.columns([2, 2, 3])
    bracket = c1.selectbox("天梯分段", list(BRACKETS.keys()),
                           format_func=lambda x: BRACKETS[x], index=7)
    attr_filter = c2.multiselect("主属性", ["力量", "敏捷", "智力", "全能"], default=None)
    min_pick_rate = c3.slider("最低选取率 %", 0.0, 20.0, 2.0, 0.5)

    df = hero_df_from_stats(hero_stats, heroes_official, bracket)
    if df is None or not len(df):
        st.error("无数据")
        return
    view = df[(df["选取率%"] >= min_pick_rate)]
    if attr_filter:
        view = view[view["属性"].isin(attr_filter)]

    kpi_row([("样本对局数", f"{view['选取次数'].sum():,}"),
             ("英雄总数", f"{len(df)}"),
             ("筛选后英雄", f"{len(view)}"),
             ("平均胜率", f"{view['胜率%'].mean():.2f}%")])

    tab1, tab2, tab3 = st.tabs(["🎯 强度散点图", "🏆 胜率 TOP 15", "📋 完整数据表"])

    with tab1:
        fig = px.scatter(view, x="选取率%", y="胜率%", size="选取次数", color="属性En",
                         hover_name="中文名", text="中文名",
                         color_discrete_map={"str": "#E54545", "agi": "#5AD35A", "int": "#5AA7E5", "univ": "#C9A227"},
                         size_max=34)
        fig.update_traces(textposition="top center", textfont_size=9, textfont_color="#9AA3B2")
        mean_x, mean_y = view["选取率%"].mean(), view["胜率%"].mean()
        fig.add_vline(x=mean_x, line_dash="dot", line_color="rgba(255,255,255,0.25)")
        fig.add_hline(y=mean_y, line_dash="dot", line_color="rgba(255,255,255,0.25)")
        fig.update_layout(title=f"{BRACKETS[bracket]}分段 · 选取率 vs 胜率（气泡大小=选取次数）")
        st.plotly_chart(plotly_layout(fig, height=560), use_container_width=True)

    with tab2:
        top = view.nlargest(15, "胜率%")
        rows = ""
        for i, (_, r) in enumerate(top.iterrows(), 1):
            rows += (f'<tr><td>{i}</td>'
                     f'<td><img src="{r["图标"]}" style="height:38px;border-radius:6px;vertical-align:middle;margin-right:8px;">'
                     f'{r["中文名"]} <span style="color:#9AA3B2;font-size:.85rem">{r["英雄"]}</span></td>'
                     f'<td>{r["属性"]}</td><td>{r["选取次数"]:,}</td>'
                     f'<td style="color:{"#E54545" if r["胜率%"]>=50 else "#5AD35A"};font-weight:700">{r["胜率%"]}%</td>'
                     f'<td>{r["选取率%"]}%</td></tr>')
        st.markdown(f'<div class="panel"><table class="data-table">'
                    f'<tr><th>#</th><th>英雄</th><th>属性</th><th>选取次数</th><th>胜率</th><th>选取率</th></tr>'
                    f'{rows}</table></div>', unsafe_allow_html=True)

    with tab3:
        st.dataframe(
            view[["中文名", "英雄", "属性", "复杂度", "胜率%", "选取率%", "选取次数"]]
            .sort_values("胜率%", ascending=False),
            use_container_width=True, hide_index=True, height=560,
            column_config={
                "中文名": st.column_config.TextColumn("英雄(中文)", width="small"),
                "英雄": st.column_config.TextColumn("Hero", width="small"),
                "选取次数": st.column_config.NumberColumn(format="%,d"),
            })


def page_pro_matches():
    st.markdown('<div class="hero-title">职业比赛</div>'
                '<div class="hero-sub">全球职业赛场最近对局 — OpenDota 实时职业比赛库</div>',
                unsafe_allow_html=True)

    matches, live = get_data("proMatches.json", "/proMatches")
    if not matches:
        st.error("职业比赛数据不可用。")
        return
    if not live:
        st.info("当前展示打包快照数据（OpenDota 实时接口暂不可用）。")

    df = pd.DataFrame(matches)
    df["radiant_win"] = df["radiant_win"].astype(bool)
    df["开始时间"] = pd.to_datetime(df["start_time"], unit="s", utc=True).dt.tz_convert(CST).dt.strftime("%m-%d %H:%M")
    df["时长"] = df["duration"].apply(fmt_dur)
    df["比分"] = df["radiant_score"].astype(str) + " : " + df["dire_score"].astype(str)
    df["获胜方"] = df.apply(lambda r: r["radiant_name"] if r["radiant_win"] else r["dire_name"], axis=1)
    df["天辉"] = df["radiant_name"].fillna("TBD")
    df["夜魇"] = df["dire_name"].fillna("TBD")
    df["联赛"] = df["league_name"].fillna("—")

    kpi_row([("对局数量", f"{len(df)}"),
             ("平均时长", fmt_dur(df["duration"].mean())),
             ("天辉胜率", f"{df['radiant_win'].mean()*100:.1f}%"),
             ("平均击杀(双方)", f"{(df['radiant_score']+df['dire_score']).mean():.0f}")])

    tab1, tab2, tab3 = st.tabs(["⚔️ 最近对局", "⏱️ 时长分布", "🏛️ 联赛统计"])

    with tab1:
        show = df[["开始时间", "联赛", "天辉", "夜魇", "获胜方", "比分", "时长"]].head(50)
        st.dataframe(show, use_container_width=True, hide_index=True, height=520)

    with tab2:
        fig = px.histogram(df, x="duration", nbins=30, color_discrete_sequence=[ACCENT])
        fig.update_layout(title="比赛时长分布（秒）", xaxis_title="时长(秒)", yaxis_title="场次")
        st.plotly_chart(plotly_layout(fig), use_container_width=True)

    with tab3:
        league = df.groupby("联赛").agg(场次=("match_id", "count"),
                                        平均时长秒=("duration", "mean")).reset_index()
        league = league[league["联赛"] != "—"].nlargest(10, "场次")
        fig = go.Figure(go.Bar(y=league["联赛"][::-1], x=league["场次"][::-1], orientation="h",
                               marker_color=GOLD))
        fig.update_layout(title="各联赛比赛场次 TOP 10")
        st.plotly_chart(plotly_layout(fig), use_container_width=True)


def page_pro_players():
    st.markdown('<div class="hero-title">职业选手与英雄绝活哥</div>'
                '<div class="hero-sub">职业选手库 + 各英雄天梯高分选手排行 — OpenDota</div>',
                unsafe_allow_html=True)

    players, live1 = get_data("proPlayers.json", "/proPlayers")
    heroes_official = load_snapshot("heroes_official.json")
    hero_list = []
    if heroes_official:
        for h in heroes_official["result"]["data"]["heroes"]:
            hero_list.append({"id": h["id"], "cn": h["name_loc"], "en": h["name_english_loc"],
                              "icon": hero_icon(h["name"])})

    if not live1 and players is not None:
        st.info("当前展示打包快照数据（OpenDota 实时接口暂不可用）。")

    tab1, tab2 = st.tabs(["🌍 职业选手库", "🗡️ 英雄绝活哥排行"])

    with tab1:
        if not players:
            st.error("选手数据不可用。")
        else:
            pdf = pd.DataFrame(players)
            kpi_row([("注册职业选手", f"{len(pdf)}"),
                     ("涉及国家/地区", f"{pdf['country_code'].nunique()}"),
                     ("涉及战队", f"{pdf['team_name'].dropna().nunique()}")])
            c1, c2 = st.columns(2)
            with c1:
                cc = pdf["country_code"].value_counts().head(10)
                fig = go.Figure(go.Bar(x=cc.index, y=cc.values, marker_color=ACCENT))
                fig.update_layout(title="选手数量 TOP 10 国家/地区")
                st.plotly_chart(plotly_layout(fig), use_container_width=True)
            with c2:
                teams = pdf["team_name"].dropna().value_counts().head(10)
                fig = go.Figure(go.Bar(y=teams.index[::-1], x=teams.values[::-1], orientation="h",
                                       marker_color=GOLD))
                fig.update_layout(title="现役选手数 TOP 10 战队")
                st.plotly_chart(plotly_layout(fig), use_container_width=True)
            st.markdown("**选手检索**（输入姓名或战队名）")
            q = st.text_input("搜索", placeholder="如: Ame, Team Liquid, N0tail", label_visibility="collapsed")
            view = pdf[["name", "team_name", "country_code", "fantasy_role", "steam_id"]]
            view.columns = ["选手", "战队", "地区", "位置(1-5)", "SteamID"]
            if q:
                ql = q.lower()
                view = view[view["选手"].str.lower().str.contains(ql, na=False) |
                            view["战队"].str.lower().str.contains(ql, na=False)]
            st.dataframe(view.head(100), use_container_width=True, hide_index=True, height=420)

    with tab2:
        if not hero_list:
            st.error("英雄列表不可用。")
        else:
            hero_names = {h["cn"]: h for h in hero_list}
            sel = st.selectbox("选择英雄（查看其天梯高分绝活哥）", list(hero_names.keys()),
                               index=list(hero_names.keys()).index("帕克") if "帕克" in hero_names else 0)
            h = hero_names[sel]
            with st.spinner("从 OpenDota 拉取该英雄高分选手排行..."):
                rankings = live_fetch(f"/heroRankings?hero_id={h['id']}")
            if not rankings:
                st.warning("实时接口不可用，无法获取该英雄排行（此项为实时查询）。")
            else:
                rows_html = ""
                for i, r in enumerate(rankings["rankings"], 1):
                    rows_html += (f'<tr><td>{i}</td>'
                                  f'<td><img src="{r.get("avatar", "")}" style="height:30px;border-radius:50%;vertical-align:middle;margin-right:8px;">'
                                  f'{r.get("personaname", "匿名")}</td>'
                                  f'<td>{r.get("team_name", "—")}</td>'
                                  f'<td>{r.get("country_code", "—")}</td>'
                                  f'<td style="color:#E8C766;font-weight:700">{r.get("score", 0):.0f}</td></tr>')
                st.markdown(f'<div class="panel"><table class="data-table">'
                            f'<tr><th>#</th><th>选手</th><th>战队</th><th>地区</th><th>绝活评分</th></tr>'
                            f'{rows_html}</table></div>', unsafe_allow_html=True)
                st.caption("绝活评分为 OpenDota 基于该选手使用该英雄的天梯表现综合计算。")


def page_about():
    st.markdown('<div class="hero-title">关于本站</div>'
                '<div class="hero-sub">数据真实性声明与技术说明</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="panel">
<h4>📡 数据来源（全部真实）</h4>
<ul>
<li><b>OpenDota 官方公开 API</b>（<code>api.opendota.com</code>）——英雄天梯胜率/选取率、职业比赛、职业选手库、天梯分分布、版本历史</li>
<li><b>Dota2 官方 datafeed</b>（<code>dota2.com/datafeed</code>）——英雄名单、官方中文译名、属性与复杂度</li>
<li>英雄头图来自 Steam 官方 CDN</li>
</ul>
<h4>🔄 数据更新机制</h4>
<ul>
<li>应用随包附带一份<b>真实数据快照</b>（抓取时间见版本概览页），保证离线/接口故障时仍可访问</li>
<li>每次刷新页面会尝试拉取 OpenDota 实时数据，成功则覆盖展示实时数据</li>
<li>英雄绝活哥排行为实时查询，带 1 小时缓存</li>
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
    st.markdown("## ⚔️ Dota2 数据站")
    st.caption("OpenDota 真实数据 · Streamlit Demo")
    page = option_menu(
        menu_title=None,
        options=["版本概览", "天梯英雄梯度", "职业比赛", "选手与绝活哥", "关于"],
        icons=["graph-up-arrow", "trophy", "controller", "people", "info-circle"],
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

PAGES = {"版本概览": page_overview, "天梯英雄梯度": page_hero_meta,
         "职业比赛": page_pro_matches, "选手与绝活哥": page_pro_players, "关于": page_about}

st.markdown('<div class="hero-title" style="font-size:2.1rem">⚔️ Dota2 数据分析站</div>'
            '<div class="hero-sub">基于 OpenDota 官方公开 API 的天梯环境与职业赛场数据分析 Demo</div>',
            unsafe_allow_html=True)

PAGES[page]()
