# ⚔️ Dota2 数据分析站 (Dota2 Analytics Demo)

基于 **真实数据** 的 Dota2 天梯与职业赛场数据分析演示应用，使用 Streamlit 构建。

## 📡 数据来源（全部真实，无模拟数据）

| 数据 | 来源 |
|------|------|
| 英雄胜率 / 选取率（各天梯分段） | [OpenDota API](https://docs.opendota.com/) `/heroStats` |
| 职业比赛 | OpenDota `/proMatches` |
| 职业选手库 | OpenDota `/proPlayers` |
| 英雄绝活哥排行 | OpenDota `/heroRankings` |
| 天梯分分布 | OpenDota `/distributions` |
| 版本历史 | OpenDota `/patches` |
| 英雄官方中文名 / 属性 / 复杂度 | [Dota2 官方 datafeed](https://www.dota2.com/datafeed/herolist?language=schinese) |
| 英雄头图 | Steam 官方 CDN |

## 🔄 数据更新机制

- 仓库 `data/` 内附带真实数据快照（`fetch_data.py` 抓取），保证 OpenDota 临时故障时应用仍可用。
- 应用每次运行会尝试拉取 OpenDota 实时数据（带 1 小时缓存），成功则展示实时数据。
- 重新抓取快照：`python fetch_data.py`

## 🚀 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 📋 页面结构

1. **版本概览** — 当前版本、天梯分分布、段位分布、版本时间线
2. **天梯英雄梯度** — 各分段胜率×选取率散点图、胜率 TOP15、完整数据表
3. **职业比赛** — 最近职业对局、时长分布、联赛统计
4. **选手与绝活哥** — 职业选手库检索 + 各英雄天梯高分选手实时排行
5. **关于** — 数据来源与声明
