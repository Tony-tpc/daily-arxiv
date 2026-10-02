# 中国能源数据源配置指南

## 配置原则

所有来源位于 `config/config.yaml` 的 `sources` 下。学术层使用 OpenAlex、Crossref、OpenAIRE、Semantic Scholar 和机构导出文件；arXiv 提供正式版本与摘要线索；政策、新闻和行业报告只配置中国官方机构、国内媒体或中国能源行业机构。`regional_focus: ["CN"]` 是排序与分析边界，不替代来源审核。标题过滤应排除“机械臂”“人形机器人”等非能源方向内容。

## 来源类型

| Key | 用途 | 关键配置 |
|---|---|---|
| `arxiv` | 能源系统与多智能体论文 | `categories`、`keyword_groups`、`days_back` |
| `openalex_search` | 主题、ISSN 和引文检索 | `per_page`、`max_pages_per_run`、`recent_days` |
| `crossref` | 独立主题与 ISSN 检索 | `mailto`、`per_page`、`max_pages_per_run` |
| `openaire` | 聚合机构知识库与版本链接 | `per_page`、`max_pages_per_run` |
| `semantic_scholar` | 批量检索与双向引文 | `.env` 中 `SEMANTIC_SCHOLAR_API_KEY` |
| `rss` | 国内能源新闻 | `feeds`、关键词过滤、企业动态排除规则 |
| `policy` | 中国政策文件 | HTML selectors、`issuing_body`、`policy_level` |
| `industry_report` | 中国能源行业报告 | selectors、`institution`、标题白/黑名单 |

## 论文分区与采集

论文必须有可核验的中科院大类一区、二区证据，旧的 `quartile: Q1/Q2` 不构成准入依据。
分区记录包含版本年份、学科、ISSN、分区、核验时间，以及 HTTPS 出处或本地文件校验值与页码。
`paper_quality.venue_evidence_path` 指向本地证据 JSON；完整分区表不提交 Git。
仅使用已导入证据中的最新年份。ISSN 优先匹配，没有 ISSN 时才使用规范化期刊名精确匹配。

原始记录先写入缓存，补证和去重后执行主题与文献类型门槛。综述、会议、预印本、社论、
勘误、撤稿与证据不足的记录继续保存在采集缓存，不进入合格论文列表。
详细命令、分区 JSON 示例、分页与恢复语义见 [论文获取与质量管理](paper_acquisition.md)。

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

`scheduler.jobs` 将论文、新闻、政策、报告隔离成独立任务。新闻间隔必须在 6–12 小时；默认 8 小时。学术论文每周日 09:00 增量更新并续跑历史与引文任务，政策每日、行业报告每周。每个任务有有界指数退避，状态写入 `data/state/scheduler_status.json`，事件写入 `logs/scheduler_jobs.jsonl`。

API Key 只放 `.env`。新增站点前确认公开访问条款、请求频率与 robots 规则；设置合理 timeout 和 `max_entries`，不得绕过登录、验证码或访问控制。

可从 `docs/examples/minimal_config.yaml` 起步；执行前备份 `config/config.yaml`，再将示例复制到该路径。
# AIHOT-inspired incremental listings

RSS feeds now also accept `format: html` or `format: json`. HTML shares list-item
parsing with historical collection. `item_selector`, `link_selector`, and
`date_selector` identify original metadata; `fetch_detail` and
`detail_content_selector` optionally retrieve the article body. Empty HTML selector
results are errors, not successful empty fetches. Existing policy/report collectors
retain their specialized extraction.

Each feed may declare `source_id` (stable unique identifier), `owner_id` (publisher
institution shared by its feeds), `tier` (`T1`, `T1_5`, `T2`), and `first_party`.
Without an override, the configured feed URL supplies a stable identity; known
government/media subdomains share an owner. Unknown publishers fall back to the
hostname, never to an invented institution.

JSON feeds use an explicit dot-separated array path and field mapping:

```yaml
- name: Example energy feed
  enabled: false
  source_id: example-energy
  owner_id: example.org
  tier: T2
  first_party: false
  region: CN
  format: json
  url: https://example.org/energy.json
  items_path: data.items
  fields:
    title: title
    link: url
    published: published_at
    summary: summary
```

This is a disabled schema example, not a production source. Missing mapped fields
or non-array results fail the source independently. See [hotspots.md](hotspots.md)
for selection, caching, ranking windows and publication rules.

Incremental HTML/RSS feeds can set `max_age_days` to skip old dated entries before
fetching details (NEA market news uses 7 days). Missing dates are never invented.
Historical backfill remains a separate task. TLS verification remains enabled;
certificate/hostname failures are recorded and shown as failed sources.

`origin_owner_id` may identify the explicitly verified original institution for a
repost feed, or be stored in document provenance metadata by a targeted collector.
It must come from visible source credit, never a model guess. The host transporting
a repost does not count as another institution. Configure `owner_id` only after
verifying ownership; unrecognized bare hostnames are not treated as confirmed
independent institutions for industry publication.
