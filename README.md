# ⚔️ Dota2 比赛数据分析 (Dota2 Match Analytics)

基于 **真实数据** 的 Dota2 职业比赛数据分析演示应用，使用 Streamlit 构建。聚焦比赛数据：比赛库、单场深度复盘、赛场统计。

## 📡 数据来源（全部真实，无模拟数据）

| 数据 | 来源 |
|------|------|
| 职业比赛列表 | [OpenDota API](https://docs.opendota.com/) `/proMatches` |
| 单场完整详情（BP/选手数据/经济经验曲线/目标物） | OpenDota `/matches/{id}` |
| 英雄官方中文名 | [Dota2 官方 datafeed](https://www.dota2.com/datafeed/herolist?language=schinese) + OpenDota `/constants/heroes` |
| 英雄头图 | Steam 官方 CDN |

## 🔄 数据更新机制

- 仓库 `data/` 内附带真实数据快照（`fetch_data.py` 抓取），保证 OpenDota 临时故障时应用仍可用。
- 比赛列表：每次运行尝试实时刷新；单场深度复盘：实时查询详情接口（1 小时缓存）。

## 🚀 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 📋 页面结构

1. **比赛库** — 最近职业对局，支持战队/联赛搜索、阵营与时长筛选
2. **深度复盘** — 单场全解析：阵容/禁用 BP、双方选手 KDA/GPM/正补数据表、经济经验领先曲线、推塔与肉山控制
3. **赛场统计** — 时长与击杀分布、联赛活跃度、战队出场/胜场/胜率榜
4. **关于** — 数据来源与声明
