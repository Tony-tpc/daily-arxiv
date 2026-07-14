# 科研情报多源跟踪系统开发 Todo List

> 本文档用于指导后续开发执行，范围限定为：**学术论文、政策文件、新闻报道、行业报告**。
>
> 不包含企业动态、公司新闻、融资信息、产品发布等企业信息采集与分析。

---

## 1. 文档目标

本 Todo List 的目标是将当前仓库从“单一 arXiv 论文跟踪工具”逐步升级为一个可运行的、轻量级的、多源科研情报跟踪与整理原型系统，用于：

1. 自动收集学术论文、政策文件、新闻报道、行业报告。
2. 使用大语言模型生成中文概括、标签和阅读建议。
3. 优先将多源信息展示在网页端，形成可直接浏览的研究情报界面。
4. 将多源信息统一保存为 Markdown / JSON / 本地知识库结构，作为持久化与导出层。
5. 对阶段性结果进行关键词统计、主题归纳与趋势分析。
6. 支持后续生成研究情报报告和研究方向对比分析。

---

## 1.1 研究方向边界

- 核心方向是**能源系统中的具身智能**：能源智能体对物理能源设备的感知、决策与控制，以及源网荷储协同、自主运行。
- 通用机器人操控、机械臂、机器人导航和人形机器人不作为目标研究方向；只有具备明确能源系统上下文时才判定为能源具身智能。
- 政策、新闻和行业信号默认优先中国国内来源与中国地区影响。

---

## 1.2 前端查看与启动命令

后续开发默认把 **网页端作为第一查看入口**，不要再假设使用者会主动阅读 `data/*.json` 或 `report_*.md`。

### 推荐启动命令（Windows，本仓库当前可用）

#### 运行主流程，生成最新数据

```powershell
venv\Scripts\python.exe main.py
```

#### 启动前端页面

```powershell
venv\Scripts\python.exe -X utf8 src/web/app.py
```

说明：

- `-X utf8` 是当前 Windows 环境下的重要参数，用于避免 `app.py` 启动时输出 emoji 日志触发 `gbk` 编码错误。
- 前端默认地址：`http://127.0.0.1:5000`
- 后续若修改 Web 启动逻辑，必须保证文档中的这条命令同步更新，避免重复试错。

---

## 2. 当前系统已实现能力基线

以下能力已在仓库中存在，可复用，不应重复建设：

- [x] arXiv 论文抓取
- [x] LLM 论文摘要生成
- [x] Markdown 摘要报告输出
- [x] 结构化知识抽取
- [x] 趋势分析（关键词 / LDA / 词云 / LLM 深度分析）
- [x] Web 展示接口
- [x] 调度执行与邮件通知

### 已有关键文件

- `main.py`
- `scheduler.py`
- `src/crawler/arxiv_fetcher.py`
- `src/summarizer/paper_summarizer.py`
- `src/summarizer/llm_factory.py`
- `src/extractor/knowledge_extractor.py`
- `src/analyzer/trend_analyzer.py`
- `src/web/app.py`
- `config/config.yaml`

---

## 3. 本次开发范围与边界

地域约束：默认优先采集和展示中国国内（`CN`）政策、行业与科研信息；海外来源仅作为显式启用的补充来源。

### 纳入范围

- 学术论文（arXiv 为第一优先级）
- 政策文件
- 新闻报道
- 行业报告
- 网页端优先展示
- Obsidian / Markdown / JSON 输出
- Zotero 集成（优先 Local API / 导出能力）
- 多源趋势分析
- 研究情报报告生成

### 明确排除

- 企业官网动态抓取
- 企业融资信息
- 产品发布监控
- 企业合作/落地案例跟踪
- 企业画像与企业竞争分析

---

## 4. 总体执行原则

后续开发必须遵循以下原则：

1. **先抽象、后扩展来源**：先统一数据模型和 source adapter，再接入新来源。
2. **先最小可运行，再增强智能分析**：优先确保多源采集可跑通，再做高级趋势分析。
3. **网页优先，文件其次**：能在网页展示的内容，优先通过 Web API 和前端界面呈现；Markdown / JSON 主要用于存储、导出和调试。
4. **先 Markdown / JSON，后复杂集成**：文件输出仍然保留，但角色是底层持久化与外部导出，不是主要阅读入口。
5. **复用现有模块，不重复造轮子**：LLM 工厂、知识抽取器、趋势分析器、历史快照模式优先复用。
6. **每个任务要可验证**：每项 Todo 必须有输出、文件落点或测试标准。

---

## 5. 统一目标架构

目标系统推荐采用如下流水线：

1. Source Fetch
2. Normalize
3. Summarize
4. Extract Tags / Entities / Reading Suggestions
5. Persist Snapshots
6. Serve Web API / Render Web UI
7. Export Markdown / JSON / Obsidian / Zotero
8. Analyze Trends
9. Generate Intelligence Reports

建议目录演进方向：

```text
src/
├── sources/
├── models/
├── pipeline/
├── summarizer/
├── extractor/
├── ranking/
├── linking/
├── storage/
├── exporters/
├── integrations/
├── analyzer/
└── reporting/
```

---

## 6. Phase 1：需求梳理与架构定型（2026 年 7 月上旬）

### 6.1 定义统一 Document Schema

状态：已完成

- [x] 新增文件：`src/models/document_schema.py`
- [x] 定义统一文档模型，覆盖四类来源：paper / policy / news / industry_report
- [x] 至少包含以下公共字段：
  - `id`
  - `source_type`
  - `source_name`
  - `title`
  - `summary`
  - `authors_or_orgs`
  - `published_at`
  - `collected_at`
  - `url`
  - `raw_text`
  - `keywords`
  - `tags`
  - `entities`
  - `research_direction`
  - `importance_score`
  - `reading_suggestion`
  - `provenance`
- [x] 定义各来源扩展字段：
  - paper：`doi`, `arxiv_id`, `categories`
  - policy：`issuing_body`, `policy_level`, `region`, `effective_date`
  - news：`media_name`, `region`, `event_type`
  - industry_report：`institution`, `report_type`, `region`
- [x] 为 schema 写最小单元测试

**验收标准**

- 任意来源都能规范映射到统一 schema。
- 后续模块不再依赖仅适用于论文的字段命名。

---

### 6.2 设计 Source Adapter 抽象层

状态：已完成

- [x] 新增文件：`src/sources/base.py`
- [x] 设计 `BaseSourceAdapter` 接口，至少包含：
  - `fetch()`
  - `normalize()`
  - `validate()`
  - `save_raw_snapshot()`
- [x] 新增文件：`src/sources/registry.py`
- [x] 将现有 `src/crawler/arxiv_fetcher.py` 迁移或包裹为 `ArxivSourceAdapter`
- [x] 使主流程通过 registry 加载来源，而不是写死调用 arXiv

**验收标准**

- 新来源可以不改主流程结构直接接入。
- arXiv 作为第一个 adapter 仍然能正常运行。

---

### 6.3 重构配置结构

状态：已完成

- [x] 更新 `config/config.yaml`
- [x] 从单一 `arxiv` 配置升级为：
  - `sources.arxiv`
  - `sources.openalex`
  - `sources.rss`
  - `sources.policy`
  - `sources.industry_report`
- [x] 新增研究方向配置：
  - `tracking_topics`
  - `keyword_groups`
  - `negative_keywords`
  - `priority_rules`
- [x] 新增输出配置：
  - `outputs.markdown`
  - `outputs.json`
  - `outputs.obsidian`
  - `outputs.zotero`
- [x] 新增分析配置：
  - `analysis.trend_window_days`
  - `analysis.compare_sources`
  - `analysis.entity_tracking`

**验收标准**

- 配置可以清楚表达“抓什么、从哪抓、如何输出、如何分析”。

---

### 6.4 定义输出模板与字段规范

状态：已完成

- [x] 设计统一 Markdown 模板：
  - 论文摘要卡片
  - 政策简报卡片
  - 新闻速览卡片
  - 行业报告卡片
- [x] 基于同一字段规范定义网页卡片展示结构（后续优先在网页展示）
- [x] 定义统一 YAML frontmatter 规范
- [x] 定义 JSON schema version 字段
- [x] 定义阅读建议结构：
  - `why_relevant`
  - `read_priority`
  - `recommended_action`
  - `related_topics`

**验收标准**

- 不同来源输出格式一致，可直接保存到知识库。
- 同一套字段规范未来可以直接映射到网页卡片展示，而不依赖用户阅读原始 JSON/Markdown。
- 当前网页列表与首页预览已优先消费标准化展示结构，而不是直接拼接原始 paper 字段。

---

## 7. Phase 2：多源采集 MVP（2026 年 7 月中旬）

### 7.1 拆分主流程为阶段化 Pipeline

状态：已完成

- [x] 新增目录：`src/pipeline/`
- [x] 将 `main.py` 拆为独立阶段模块：
  - `fetch_stage.py`
  - `normalize_stage.py`
  - `summarize_stage.py`
  - `extract_stage.py`
  - `analyze_stage.py`
  - `export_stage.py`
- [x] 引入 pipeline context 对象
- [x] 每个 stage 明确输入与输出职责（当前以 `PipelineContext` 为主，文件化阶段边界将在后续持久化增强中继续完善）

**验收标准**

- 每个阶段在代码结构上已独立封装，可被单独调用与组合；真正的按阶段文件化重跑能力将在后续 pipeline 持久化阶段继续增强。
- 整体流程可组合运行。

---

### 7.2 接入 OpenAlex 补充学术元数据

- 状态：已完成

- [x] 新增文件：`src/sources/openalex_adapter.py`
- [x] 支持按标题 / DOI / arXiv ID 做 enrichment
- [x] 补充信息至少包括：
  - citation counts
  - concepts / topics
  - institutions
  - referenced works
- [x] 为 enrichment 增加本地缓存逻辑
- [x] OpenAlex 配置支持通过环境变量提供 `api_key` / `email`
- [x] OpenAlex 关键信息已接入网页卡片展示结构，而不只是写入 enrichment 文件
- [x] OpenAlex 搜索默认共享顶层 `keyword_groups`，并已收敛到近 180 天的电力系统 / P2P 市场交易 / 强化学习方向

**验收标准**

- 学术记录不再只依赖 arXiv 原始字段。
- 原始 arXiv 抓取快照与 enriched 快照分离保存，避免语义混淆。
- 用户无需手动查看 json/md，即可在网页端看到引用次数、主主题、机构、参考文献数等 OpenAlex 信息。

---

### 7.3 新增 RSS / News 基础采集器

- 状态：已完成

- [x] 新增文件：`src/sources/rss_adapter.py`
- [x] 支持标准 RSS / Atom feed
- [x] 支持记录 ETag / Last-Modified
- [x] 支持 URL + title hash 去重
- [x] 先接入 3~5 个试点来源：
  - 政府部门官网
  - 行业协会网站
  - 技术媒体
  - 研究机构博客
  - 新闻媒体

**验收标准**

- 能稳定拉取非论文来源。
- 未更新的 feed 不重复处理。

---

### 7.4 新增政策文件采集器

- 状态：已完成

- [x] 新增文件：`src/sources/policy_adapter.py`
- [x] 支持政策来源配置列表
- [x] 定义政策标准字段提取：
  - 发布机构
  - 文种
  - 发布日期
  - 生效日期
  - 影响领域
  - 政策强度
- [x] 接入 LLM 提取：
  - 核心政策导向
  - 涉及技术方向
  - 潜在影响

**验收标准**

- 政策文档可进入统一 schema。
- 不再以纯文本形式散落存储。

---

### 7.5 新增行业报告采集器

- 状态：已完成

- [x] 新增文件：`src/sources/industry_report_adapter.py`
- [x] 支持配置行业报告来源
- [x] 支持行业报告统一字段：
  - 发布机构
  - 报告类型
  - 地区
  - 主题方向
  - 关键词
- [x] 接入 LLM 提取行业应用进展与趋势判断

**验收标准**

- 行业报告可与论文、政策、新闻一起进入统一流程。

---

## 8. Phase 3：摘要、标签与阅读建议升级（2026 年 7 月下旬）

### 8.1 将 Paper Summarizer 升级为 Document Summarizer

- [x] 新增文件：`src/summarizer/document_summarizer.py`
- [x] 将 `paper_summarizer.py` 的共性逻辑抽离复用
- [x] 为不同来源设计不同 prompt：
  - paper prompt
  - policy prompt
  - news prompt
  - industry_report prompt
- [x] 输出统一结构：
  - 中文概括
  - 核心观点
  - 与研究方向关系
  - 是否值得阅读
  - 后续建议
- [x] 为网页卡片预留直接展示字段，避免前端再二次拼接长文本

**验收标准**

- 摘要模块不再只适配 arXiv abstract。

---

### 8.2 增加显式 Tags / Entities / Themes 抽取层

- [x] 在现有 `knowledge_extractor.py` 基础上新增轻量标签抽取逻辑
- [x] 抽取下列信息：
  - 技术主题
  - 应用场景
  - 能源相关实体
  - 具身智能相关实体
  - 国家 / 地区 / 机构
- [x] 将结果写回统一 schema 字段：`tags`, `entities`, `research_direction`

**验收标准**

- 系统具备明确标签层，而不是只依赖 categories 或自由关键词。

---

### 8.3 增加阅读建议与优先级排序

- [x] 新增文件：`src/ranking/relevance_ranker.py`
- [x] 设计评分维度：
  - topic relevance
  - novelty
  - policy importance
  - industry relevance
  - source credibility
- [x] 输出优先级：
  - `high`
  - `medium`
  - `low`
- [x] 输出建议动作：
  - 精读
  - 略读
  - 存档
- [x] 在网页列表与详情页直接展示优先级与建议动作

**验收标准**

- 每条记录都有可解释的阅读建议。

---

### 8.4 加入去重与跨来源关联逻辑

状态：已完成

- [x] 新增文件：`src/linking/deduplicator.py`
- [x] 支持跨来源去重规则：
  - DOI
  - title similarity
  - canonical URL
- [x] 支持跨来源关联：
  - 论文 ↔ 政策
  - 论文 ↔ 新闻
  - 论文 ↔ 行业报告
  - 政策 ↔ 新闻
  - 政策 ↔ 行业报告
- [x] 生成 `related_documents`

**验收标准**

- 多源内容不会重复堆积。
- 同一方向的信息可以串联查看。

---

## 9. Phase 4：知识库与工具集成（2026 年 8 月上旬）

说明：本阶段的 Markdown / Zotero / Obsidian 工作是**导出层**，优先级低于网页展示层。默认阅读入口仍然是 Web 页面。

### 9.1 Obsidian 导出器

状态：已完成

- [x] 新增文件：`src/exporters/obsidian_exporter.py`
- [x] 输出 vault-friendly Markdown
- [x] 默认使用标准 Markdown links
- [x] 支持目录结构：
  - `papers/`
  - `policies/`
  - `news/`
  - `industry_reports/`
  - `daily/`
  - `weekly/`
- [x] 支持 frontmatter：
  - tags
  - source_type
  - priority
  - published_at
  - related_topics

**验收标准**

- 输出结果可直接进入 Obsidian 并可检索。

---

### 9.2 Zotero 集成

状态：已完成

- [x] 新增文件：`src/integrations/zotero_client.py`
- [x] 优先实现 Local API 只读集成
- [x] 支持 CSL-JSON / BibTeX 导出
- [x] 支持将论文记录映射为 Zotero item payload
- [x] 预留 citekey 字段

**验收标准**

- 论文元数据可与 Zotero 工作流衔接。

---

### 9.3 存储层抽象

状态：已完成

- [x] 新增文件：`src/storage/base.py`
- [x] 定义 JSON storage / SQLite storage 抽象
- [x] 封装当前 `latest.json + snapshot.json` 模式
- [x] 如果保留 sqlite 配置，则实现 SQLite backend；否则删除无效配置

**验收标准**

- 存储配置项与实际实现一致。

---

### 9.4 历史快照与索引规范

状态：已完成

- [x] 统一 snapshot 命名规范
- [x] 新增 manifest / index 文件
- [x] 支持按日期、来源类型、主题回查
- [x] 为长期趋势分析准备结构化历史数据

**验收标准**

- 历史数据可用于回溯分析，而不仅仅是 latest 展示。

---

## 10. Phase 5：趋势分析与结果展示（2026 年 8 月下旬—2026 年 9 月 10 日）

### 10.1 将 Trend Analyzer 升级为时序趋势分析器

- [ ] 重构 `src/analyzer/trend_analyzer.py`
- [ ] 新增能力：
  - topic momentum
  - entity frequency change
  - new topic emergence
  - topic decline
  - cross-source comparison
- [ ] 支持输出近 7 / 30 / 60 天趋势变化

**验收标准**

- 系统可以回答“趋势如何变化”，而不是只输出单次快照分析。

---

### 10.2 学术—政策—行业 关联分析

- [ ] 新增文件：`src/analyzer/cross_source_analyzer.py`
- [ ] 比较维度至少包括：
  - 论文热度
  - 政策支持力度
  - 行业关注度
- [ ] 生成方向判断：
  - 学术领先但政策/行业弱
  - 政策驱动增强
  - 行业高度关注
  - 三端共振

**验收标准**

- 可初步判断某个方向的研究价值与应用潜力。

---

### 10.3 研究情报报告生成器

- [ ] 新增文件：`src/reporting/intelligence_report_generator.py`
- [ ] 支持自动生成周报 / 阶段报告
- [ ] 固定章节建议包括：
  - 热点论文
  - 政策导向
  - 新闻与行业报告
  - 关键趋势
  - 研究启发
  - 后续建议
- [ ] 输出 Markdown + JSON
- [ ] 同时提供网页端报告视图，不要求用户手动打开 Markdown 文件

**验收标准**

- 报告可直接作为阶段性汇报草稿使用。

---

### 10.4 自身研究方向对比模块

- [ ] 支持用户配置“自身研究主题 / 技术路线”
- [ ] 将外部情报结果与自身研究方向对比
- [ ] 输出内容包括：
  - 已有优势
  - 存在差距
  - 值得补强的方向
  - 可跟进论文 / 政策 / 行业案例

**验收标准**

- 系统可输出与个人研究方向直接相关的建议。

---

## 11. Phase 6：原型稳定化与交付收尾

### 11.1 Web 界面升级

- [ ] 明确网页为默认阅读入口，数据文件仅作为底层存储和导出
- [ ] 在 `src/web/app.py` 中增加多源展示视图
- [ ] 增加筛选条件：
  - source_type
  - topic
  - priority
  - date range
- [ ] 增加趋势图表：
  - topic timeline
  - source comparison
  - entity trends
- [ ] 增加“今日建议阅读”面板
- [ ] 增加“研究情报首页”，集中展示摘要、政策、新闻、行业报告和趋势卡片
- [ ] 优先把摘要、阅读建议、热点判断、关联关系直接渲染到网页，不要求用户阅读 json/md 文件

**验收标准**

- Web 页面从论文看板升级为多源科研情报看板。
- 绝大多数核心信息都能直接在网页端完成阅读与筛选。

---

### 11.2 调度与任务编排升级

- [ ] 升级 `scheduler.py` 支持 source-specific jobs
- [ ] 允许不同抓取频率：
  - arXiv：daily
  - news：每 6~12 小时
  - policy：daily / weekly
  - industry_report：weekly
- [ ] 增加失败重试、任务日志、任务状态文件

**验收标准**

- 多源任务可以稳定自动运行。

---

### 11.3 测试补全

- [ ] 为每个 source adapter 编写单元测试
- [ ] 为统一 schema 编写验证测试
- [x] 为跨来源去重与关联编写测试
- [ ] 为导出器编写 golden-file 测试
- [ ] 为趋势分析编写历史快照测试

**验收标准**

- 核心模块具备自动化回归保障。

---

### 11.4 文档补全

- [ ] 更新 README / README_zh
- [ ] 新增文档：
  - `docs/multi_source_architecture.md`
  - `docs/source_config_guide.md`
  - `docs/obsidian_export_guide.md`
  - `docs/zotero_integration_guide.md`
  - `docs/intelligence_report_guide.md`
- [ ] 提供一个最小 demo 配置与样例输出

**验收标准**

- 新会话或新 agent 可以仅凭文档继续开发。

---

## 12. 推荐执行顺序（必须遵守）

建议严格按以下顺序推进，避免返工：

1. 统一 `DocumentSchema`
2. 抽象 `BaseSourceAdapter`
3. 重构 `config.yaml`
4. 拆分 pipeline stages
5. 迁移 arXiv 为新 adapter
6. 实现 `RSSAdapter`
7. 实现 `PolicyAdapter`
8. 实现 `IndustryReportAdapter`
9. 实现 `DocumentSummarizer`
10. 加入 tags / entities / reading suggestion
11. 加入跨来源 dedup / linking
12. 增加 Obsidian 导出
13. 增加 Zotero 集成
14. 抽象 storage backend
15. 升级趋势分析为时序版本
16. 增加 cross-source analyzer
17. 增加 intelligence report generator
18. 升级 Web 与 scheduler
19. 补测试
20. 补文档

---

## 13. 最高优先级可直接开工任务

如果下一步立即开始开发，建议先做以下 10 个任务：

- [x] Task 1：创建 `src/models/document_schema.py`
- [x] Task 2：创建 `src/sources/base.py` 与 `src/sources/registry.py`
- [x] Task 3：将 arXiv 获取逻辑迁移到 `ArxivSourceAdapter`
- [x] Task 4：重构 `config/config.yaml` 为多源结构
- [x] Task 5：拆分 `main.py` 为 stage-based pipeline
- [x] Task 6：实现 `src/sources/rss_adapter.py`
- [x] Task 7：实现 `src/sources/policy_adapter.py`
- [x] Task 8：实现 `src/sources/industry_report_adapter.py`
- [x] Task 9：实现 `src/summarizer/document_summarizer.py`
- [x] Task 10：实现 `src/ranking/relevance_ranker.py`

---

## 14. 完成定义（Definition of Done）

只有当满足以下条件时，才可认为该研究计划对应的原型基本完成：

- [ ] 学术论文、政策文件、新闻报道、行业报告四类来源可自动获取
- [ ] 四类来源都可映射到统一 schema
- [ ] 四类来源都可生成中文摘要与阅读建议
- [ ] 输出可稳定保存为 JSON 与 Markdown
- [ ] 主要摘要、阅读建议、趋势结论、关联信息都能在网页端直接查看
- [ ] Obsidian 导出可用
- [ ] Zotero 至少具备基础集成能力
- [ ] 趋势分析支持历史对比
- [ ] 能自动生成阶段性研究情报报告
- [ ] Web 页面可展示多源结果
- [ ] 调度可自动运行
- [ ] 关键路径有测试覆盖
- [ ] 文档足够让后续 agent 直接继续执行

---

## 15. 备注

1. 当前仓库最值得复用的模块是：
   - `LLMClientFactory`
   - `KnowledgeExtractor`
   - `TrendAnalyzer`
   - `latest.json + snapshot.json` 模式
   - `src/web/app.py` 的 read-side API 模式
2. Zotero 集成建议优先走 Local API + 导出，不建议一开始做复杂远程同步。
3. Obsidian 集成建议优先走 Markdown 文件导出，不建议一开始依赖插件 API。
4. 趋势分析必须基于多期快照，而不是单日静态结果。

---

**本文档用途：后续执行开发时，默认以此文档为准。**
