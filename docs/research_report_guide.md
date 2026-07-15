# 研究信息汇总报告指南

## 报告内容

报告以24个月事件定期资料、六类固定研究主题和预测分析为输入，首先回答未来1–3个月与6–12个月可能发生什么、证据是否充分、什么条件会推翻判断。默认周报覆盖最近7天的来源附录；趋势正文始终使用完整历史窗口。

```yaml
reporting:
  enabled: true
  default_type: "weekly"
  directory: "data/reports"
  max_items_per_section: 6
  weekly_days: 7
  stage_days: 180
```

执行 `python main.py` 后，`report_stage` 同时写入 JSON 和 Markdown；Web 的“研究报告”目录通过 `/api/reports/latest` 读取最新结果。正文依次为未来趋势总览、主题决策卡、跨来源传导、近期预测、战略情景、科研行动与监测清单；论文、中国政策、国内新闻和行业报告仅作为同级来源附录。

## 解读规则

- 跨来源传导要求每类来源至少两条事件定时证据；时间顺序不等同于因果关系。
- 定量预测至少需要12个可用月份、6个非零月份和12条主题材料，否则只输出低置信情景。
- 每项判断必须带证据ID、反证条件和监测指标；历史缺口不会按零值计算。
- 重要性评分只用于来源附录排序，不参与趋势、预测或战略情景生成。
- 研究边界以能源系统物理闭环为准；机器人或机械臂内容应被过滤，不应进入结论。

## 验证

运行 `python -m unittest test.test_research_report_generator test.test_web_reports test.test_temporal_trend_analyzer`。人工审查至少确认：报告周期正确；代表条目可回到原始链接；中国政策、国内新闻和行业报告的机构名称准确；JSON 与 Markdown 的章节计数一致；网页筛选后没有跨目录混入。

示例结构见 `docs/examples/sample_research_information.json`。真实报告和历史快照位于 `data/`，属于运行产物，不应提交。
