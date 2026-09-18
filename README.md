# ⚔️ Dota2 比赛数据分析 (Dota2 Match Analytics)

基于 **真实数据** 的 Dota2 职业比赛数据分析演示应用，使用 Streamlit 构建。聚焦比赛数据：比赛库、单场深度复盘、赛场统计。

## 📡 数据来源（全部真实，无模拟数据）

| 数据 | 来源 |
|------|------|
| T1 比赛列表（约 600 场） | [OpenDota API](https://docs.opendota.com/) `/proMatches` 翻页 |
| 单场完整详情（BP/选手数据/经济曲线，最近 60 场） | OpenDota `/matches/{id}` |
| 联赛分级（T1 判定依据） | OpenDota `/leagues` |
| 英雄官方中文名 | [Dota2 官方 datafeed](https://www.dota2.com/datafeed/herolist?language=schinese) + OpenDota `/constants/heroes` |
| 英雄头图 | Steam 官方 CDN |

**T1 定义**：OpenDota 官方分级 `premium`（TI 等最高级赛事）+ 主流顶级赛事白名单（电竞世界杯、BLAST Slam、利雅得大师赛、ESL One、DreamLeague、TI 区域预选赛等），过滤掉低级别刷分局。

## 🔄 数据更新机制

- 仓库 `data/` 内附带真实数据快照（`fetch_data.py` 抓取），保证 OpenDota 临时故障时应用仍可用。
- 比赛列表：每次运行尝试实时刷新；单场深度复盘：实时查询详情接口（1 小时缓存）。

## 🚀 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 📋 页面结构

> **全局联赛筛选**：侧边栏可限定联赛，所有页面（比赛库/复盘/英雄/战队/预测）同步生效。

1. **T1 比赛库** — 600+ 场顶级对局，支持战队/阵营/时长筛选、CSV 导出
2. **深度复盘** — 单场全解析：阵容/禁用 BP、双方选手数据表、经济经验领先曲线（含悬念指数）、推塔与肉山控制
3. **英雄风向** — 英雄出场/禁用、总胜率与天辉/夜魇分阵营胜率、BP 顺位分析（一选/末选信号）、同队双人组合胜率、选手单场高光 TOP10
4. **战队与联赛** — 战队出场/胜场/胜率榜、近 10 场状态趋势、各联赛场均时长/击杀/胜率对比、强队头对头矩阵
5. **对战预测** — Elo 实力评分（K=32）胜负预测、BO1/BO3/BO5 系列赛胜率、预测比分（场均击杀 + Elo 修正）、近期状态与历史交手、模型逐场回测准确率
6. **关于** — 数据来源与声明
