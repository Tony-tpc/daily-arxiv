# 趋势预测与历史回补指南

## 分析边界

趋势分析 v2 面向能源具身智能科研选题、方法与实验路线决策。论文可来自全球学术来源；政策、新闻和行业报告仅采用中国国内来源。通用机器人、机械臂、导航、人形机器人和企业营销材料会在进入历史语料前被过滤。

## 时间语义与历史语料

趋势只使用论文发表日、政策发布日期或新闻/报告发布日期作为 `event_date`。采集时间保存为 `first_seen_at`，不参与增长率。历史文件按 `data/history/<source_type>/<YYYY-MM>.json` 不可变保存，`data/history/coverage.json` 记录每月的 `complete`、`partial` 或 `unavailable` 状态。缺失月份不会被当作零关注度。

默认回补当前日期之前 24 个月：

```bash
python -m src.backfill --months 24
python -m src.backfill --months 24 --sources openalex_search policy
```

命令支持重复执行和断点续跑；已完成月份不会被重写。OpenAlex 使用日期过滤与游标分页，国内来源使用配置中的历史目录页。

## 六类固定主题与门槛

分析固定为：能源设备感知、自治决策与安全控制、源网荷储/虚拟电厂协同、电力市场与博弈、多智能体强化学习、数字孪生与工程验证。每类同时计算文档数、来源内占比、变化速度、加速度、持续性和来源多样性，重要性评分不进入趋势计算。

近期定量预测至少需要 12 个历史月份、6 个非空月份和 12 篇材料；战略定量判断还需 18 个月、24 篇材料和至少两类来源。未达门槛时返回 `scenario_only`，并显式列出数据缺口、假设、反证条件和监测指标。

## API 与网页

```text
GET /api/trends/forecast?horizon=near
GET /api/trends/forecast?horizon=strategic&topic=虚拟电厂
GET /api/trends/forecast?as_of=2026-07-15&confidence=low
```

响应版本为 `2.0`，主要字段包括 `data_quality`、`topic_series`、`forecasts`、`scenarios`、`lead_lag`、`evidence_ids`、`counter_signals` 和 `watch_indicators`。旧 `/api/analysis` 与 `/api/reports/latest` 保持兼容；旧产物缺少 v2 数据时由服务端生成只读降级预览。

网页“趋势分析”提供周期、主题和置信度筛选，历史实线、预测虚线、80% 区间阴影、来源传导时间轴、情景卡、证据抽屉和覆盖提示。论文、中国政策、国内新闻、行业报告是同级来源附录；重要性评分只在附录显示。

## 验证

```bash
python -m unittest discover -s test -p "test_*.py"
python -c "import subprocess, sys; raise SystemExit(subprocess.call([sys.executable, '-m', 'pyright', '--pythonpath', sys.executable]))"
node --check static/js/main.js
```

CI 在 Ubuntu 与 Windows 执行上述检查及 Flask API 冒烟测试。所有路径使用 `pathlib`，文件使用 UTF-8；Linux 浏览器字体栈包含 Noto Sans CJK SC 与 Source Han Sans SC。
