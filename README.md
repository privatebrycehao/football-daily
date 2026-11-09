# football-daily

欧洲足球日报：每天汇总过去 24 小时内欧冠、欧联和英超、西甲、德甲、意甲的已完赛结果和积分榜，加上 AI 分析，推送到 Discord 或飞书（Lark）。

本仓库从 [nba50](https://github.com/privatebrycehao/nba50) 拆分而来，保留了相关文件的提交历史。

## 运行

本地运行：

```bash
pip install -r requirements.txt
export DISCORD_WEBHOOK=...
export DEEPSEEK_KEY=...
python football_monitor.py
```

线上由 GitHub Actions（`.github/workflows/football_monitor.yml`）每天 UTC 23:00 自动运行，也可以在 Actions 页面手动触发。

运行测试：

```bash
ruff check .
python -m unittest discover -s tests
```

## Secrets

在仓库的 Settings → Secrets and variables → Actions 中配置：

| 名称 | 说明 |
| --- | --- |
| `DISCORD_WEBHOOK` | 接收日报的 webhook 地址，支持 Discord 和飞书（Lark） |
| `DEEPSEEK_KEY` | DeepSeek API Key，用于 AI 分析；未设置时退回简单统计分析 |
