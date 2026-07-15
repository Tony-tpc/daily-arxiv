# 研究信息汇总报告指南

## 报告内容

报告以统一文档、可解释排序、跨来源关联和历史趋势为输入，输出适合阶段复盘的中文信息汇总。默认周报覆盖最近 7 天；阶段报告可使用更长窗口。重点信号包括：新兴/下降主题、政策—学术—行业共振、代表文档、来源分布、与能源研究画像的匹配与缺口。

```yaml
reporting:
  enabled: true
  default_type: "weekly"
  directory: "data/reports"
  max_items_per_section: 6
  weekly_days: 7
  stage_days: 180
```

执行 `python main.py` 后，`report_stage` 同时写入 JSON 和 Markdown；Web 的“研究报告”目录通过 `/api/reports` 读取最新结果。首页“今日建议阅读”与四类同级目录展示同一批排序文档，因此报告中的评分、阅读建议和网页卡片应一致。

## 解读规则

- “共振”表示同一方向在多类来源出现，不等同于因果关系。
- “新兴主题”来自当前与上一时间窗的频次变化；历史不足时页面会明确提示。
- 政策重要性、行业相关性、来源可信度和新颖性会显示在评分拆解中。
- 研究边界以能源系统物理闭环为准；机器人或机械臂内容应被过滤，不应进入结论。

## 验证

运行 `python -m unittest test.test_research_report_generator test.test_web_reports test.test_temporal_trend_analyzer`。人工审查至少确认：报告周期正确；代表条目可回到原始链接；中国政策、国内新闻和行业报告的机构名称准确；JSON 与 Markdown 的章节计数一致；网页筛选后没有跨目录混入。

示例结构见 `docs/examples/sample_research_information.json`。真实报告和历史快照位于 `data/`，属于运行产物，不应提交。
