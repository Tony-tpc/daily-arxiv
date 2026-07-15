# 多源科研情报原型完成审计

## 审计范围

本记录逐项核验 `docs/research_intelligence_todo.md`。该计划限定为论文、中国能源政策、国内能源新闻和行业报告；企业动态、融资、产品发布、通用机器人、机械臂和人形机器人均不在范围内。README 中的微信公众号以及旧调度指南的 Telegram、Webhook 等“未来功能”不是该计划的验收项。

## Todo 与 Git 版本

| 阶段 | 已交付内容 | 主要提交 |
|---|---|---|
| Phase 1 | 统一 Schema、Source Adapter/Registry、多源配置、Markdown/Web 字段规范 | `fed07ec`, `e515d9f`, `dc5fbb1`, `d787837` |
| Phase 2 | 阶段化 Pipeline、OpenAlex、RSS、政策、行业报告采集 | `e138d36`—`972294d`, `1561094`—`fd034b1`, `47c4c60`, `e23c174`, `e96d43d` |
| Phase 3 | Document Summarizer、标签实体、阅读排序、跨源去重关联 | `5173c5a`, `d5a4d88`, `8702d41`, `b494633` |
| Phase 4 | Obsidian、Zotero、JSON/SQLite、历史快照索引 | `23743a1`, `cf63ae1`, `93dd7d3`, `1ce9ac3` |
| Phase 5 | 7/30/60 天趋势、跨源分析、周报/阶段报告、研究方向对比 | `eaa9fe8`, `f7dc19b`, `9eabb81`, `703a390` |
| Phase 6 | 多源 Web 控件、来源独立目录、调度编排、测试与文档 | `c61ffc7`, `d96f984`, `f2424fd`, `213e2a2`, `a2c09b4` |

计划文件内不存在未勾选项。每个功能组均有独立 Conventional Commit，可按上表回溯或回滚。

计划规定的 20 步执行顺序也已逐项落版：

1. Schema `fed07ec`；2. Adapter 抽象 `e515d9f`；3. 配置 `dc5fbb1`；
4. Pipeline `e138d36`、`c05d281`、`41d094a`；5. arXiv Adapter `e515d9f`；
6. RSS `47c4c60`；7. 政策 `e23c174`；8. 行业报告 `e96d43d`；
9. Document Summarizer `5173c5a`；10. 标签/实体/建议 `d5a4d88`、`8702d41`；
11. 去重关联 `b494633`；12. Obsidian `23743a1`；13. Zotero `cf63ae1`；
14. Storage `93dd7d3`；15. 时序趋势 `eaa9fe8`；16. 跨源分析 `f7dc19b`；
17. 情报报告 `9eabb81`；18. Web/调度 `c61ffc7`、`f2424fd`；
19. 测试 `213e2a2`；20. 文档 `a2c09b4`。

## 数据与界面验收

- 当前快照 `2026-07-15__mixed__084015735466__9ced1a` 共 35 条：论文 19、政策 9、国内新闻 4、行业报告 3。
- 35/35 条可通过统一 Schema 必填项验证，且全部具备摘要和结构化阅读建议。
- 非论文来源全部标记为 `CN`；通用机器人/机械臂违规 0 条，企业新闻违规 0 条。
- Web 首页、论文目录以及同级“政策 / 新闻 / 行业报告”目录可直接查看、筛选和排序。实测首页 200，周报 200，阶段报告 200，调度任务 4 个。
- Obsidian 临时导出 35 篇 Markdown，生成 `papers/`、`policies/`、`news/`、`industry_reports/`、`daily/`、`weekly/`；Zotero 导出 19 条 CSL-JSON 和 19 条 BibTeX。
- 中文词云已使用 CJK 字体重新生成；API 返回带文件时间戳的 URL，避免浏览器复用旧方块图。

## CI 与 Linux 兼容性

`.github/workflows/ci.yml` 在 `ubuntu-latest`、Python 3.11、Node 20 上执行依赖安装、Python 编译、JavaScript 语法检查和全量回归。2026-07-15 本地复核结果：`pip check` 通过、Bash 三个部署脚本通过 `bash -n`、Node 语法通过、128 项 `unittest` 全部通过。

Linux 部署具备 systemd 脚本；快照路径统一保存为 POSIX `/`；默认关闭 Flask debug/reloader；运行期不下载 NLTK 数据；词云自动探测 Noto CJK/WenQuanYi，部署文档给出 `fonts-noto-cjk` 安装命令。相关修复为 `89ee2f7`, `8ccadf0`, `202b0ad`, `a1a7406`。

## 代码审查结论

最终审查发现并已关闭：论文目录读取旧数据（`4edc51d`）、企业新闻混入（`7191ba0`）、非能源政策混入（`956bfa7`）、论文标题 HTML/机器人偏题（`6896202`）、离线分析依赖网络或 LLM（`89ee2f7`, `09c6c13`）、混合来源报告误称“论文”（`5928bc5`）、中文词云字体与缓存（`8ccadf0`）、跨平台路径和生产调试模式（`202b0ad`, `a1a7406`）。未发现仍需阻断交付的代码问题。
