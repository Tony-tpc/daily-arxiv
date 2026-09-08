# 中国能源数据源配置指南

## 配置原则

所有来源位于 `config/config.yaml` 的 `sources` 下。学术层使用 arXiv/OpenAlex；政策、新闻和行业报告只配置中国官方机构、国内媒体或中国能源行业机构。`regional_focus: ["CN"]` 是排序与分析边界，不替代来源审核。标题过滤应排除“机械臂”“人形机器人”等非能源方向内容。

## 来源类型

| Key | 用途 | 关键配置 |
|---|---|---|
| `arxiv` | 能源系统与多智能体论文 | `categories`、`keyword_groups`、`days_back` |
| `openalex_search` | 主题检索与引用信息 | `topic_query`、`recent_days`、`max_results` |
| `rss` | 国内能源新闻 | `feeds`、关键词过滤、企业动态排除规则 |
| `policy` | 中国政策文件 | HTML selectors、`issuing_body`、`policy_level` |
| `industry_report` | 中国能源行业报告 | selectors、`institution`、标题白/黑名单 |

## 高影响力论文白名单

`paper_quality` 是论文的准入门槛，不是排序加分项。启用后，只有
`accepted_publication_types` 中的正式期刊论文，且期刊名或 ISSN 精确匹配
`approved_venues`，并且其登记分区不低于 `maximum_allowed_quartile`，才会进入
列表、报告和趋势分析。未知期刊、会议论文与预印本会被直接排除。

```yaml
paper_quality:
  enabled: true
  require_formal_journal_article: true
  accepted_publication_types: ["article", "journal-article"]
  maximum_allowed_quartile: "Q2"
  approved_venues:
    - id: ieee_tsg
      name: "IEEE Transactions on Smart Grid"
      issn_l: "1949-3053"
      quartile: "Q1"
```

不要用 `publisher: IEEE` 作为准入条件：它会误收录会议论文。系统优先使用
OpenAlex 的 ISSN；当来源没有 ISSN 时才回退到规范化后的精确期刊名匹配。OpenAlex
不提供可授权复用的 JCR 影响因子或分区，`quartile` 必须由本单位依据当前 JCR 或
中科院分区手工复核并至少每年更新；未登记、分区缺失、Q3/Q4 期刊均不会被放行。

若 OpenAlex 暂时返回 429 限流，`openalex_search.crossref_fallback` 可从 Crossref
补充 DOI、期刊名、ISSN 与发表日期；它不改变研究关键词或白名单规则。建议填写
可公开的联系邮箱到 `mailto` 以便礼貌访问；不填写也不会发送任何本地凭据。

HTML 列表来源的最小定义如下：

```yaml
sources:
  policy:
    enabled: true
    feeds:
      - name: "国家能源局"
        url: "https://www.nea.gov.cn/"
        format: "html"
        item_selector: ".index_list02 li"
        link_selector: "a[href]"
        date_selector: "span"
        detail_content_selector: ".article-content"
        issuing_body: "国家能源局"
        region: "CN"
```

`policy.title_keywords_any` 是政策目录的能源边界。国家发改委等综合栏目必须命中
能源、电力、电网、电价、储能、新能源、核电、节能降碳等词后才进入统一快照；
也可以在单个 feed 上追加 `title_keywords_any` 或 `title_keywords_exclude`。
过滤在抓取详情前执行，并在合并历史快照时再次执行，避免无关通用政策长期残留。

选择器变更会导致空结果而不是写入脏数据。修改后运行对应测试，例如 `python -m unittest test.test_policy_adapter`，并用临时 state 路径做一次小规模抓取。不要删除 `state_path`：它保存 ETag、Last-Modified 和已见条目，避免重复采集。

新闻源默认启用 `exclude_enterprise_updates`。`enterprise_strong_exclude_keywords`
直接排除上市、融资、业绩和产品发布；`enterprise_entity_keywords` 与
`enterprise_update_keywords` 同时命中时，排除公司发布、中标、签约等动态。
国家电网结构调整、电力负荷等系统级新闻不因出现企业名称而自动排除。
调整词表时同步运行 `python -m unittest test.test_rss_adapter
test.test_incremental_pipeline`，确保历史快照中的旧企业动态也会被清理。

## 调度与安全

`scheduler.jobs` 将论文、新闻、政策、报告隔离成独立任务。新闻间隔必须在 6–12 小时；默认 8 小时。政策每日、行业报告每周。每个任务有有界指数退避，状态写入 `data/state/scheduler_status.json`，事件写入 `logs/scheduler_jobs.jsonl`。

API Key 只放 `.env`。新增站点前确认公开访问条款、请求频率与 robots 规则；设置合理 timeout 和 `max_entries`，不得绕过登录、验证码或访问控制。

可从 `docs/examples/minimal_config.yaml` 起步；执行前备份 `config/config.yaml`，再将示例复制到该路径。
