# 论文获取与质量管理

目标是积累去重后的合格论文和可核验覆盖，实时性不作为论文排序扣分项。
默认采集范围为能源系统、强化学习与自主控制、多智能体协同、电力市场与博弈。

## 渠道与认证

| 渠道 | 检索与元数据 | 认证 |
|---|---|---|
| OpenAlex | 主题、ISSN、参考文献、施引、还原摘要索引 | `.env` 中 `OPENALEX_API_KEY`，使用 Bearer header |
| Crossref | 独立主题与 ISSN 检索、DOI、发表信息、摘要和参考文献 | 无需密钥，可配置公开联系邮箱 `sources.crossref.mailto` |
| OpenAIRE Graph v3 | 主题检索、机构知识库摘要、版本链接 | 公共检索接口 |
| Semantic Scholar | bulk 检索、参考文献和施引分页 | `.env` 中 `SEMANTIC_SCHOLAR_API_KEY`；未配置时状态为 unavailable |
| 机构导入 | RIS、BibTeX、CSV、Web of Science 标记文本 | 由用户从现有授权数据库导出 |
| arXiv | 正式版本和摘要线索 | 预印本不直接准入 |

各独立来源在 `sources.<name>.enabled` 开关控制。共享检索式在
`paper_discovery.search_terms`；单来源 `search_terms` 可覆盖它。
每条检索式独立分页，优先执行已完成页数最少的检索式，避免第一条检索耗尽预算。
`paper_discovery.journal_issns` 选择要定向补采的相关期刊，但该列表本身不构成分区证据。

官方接口依据：[OpenAlex 认证](https://help.openalex.org/api/authentication/)、
[Crossref REST API](https://github.com/CrossRef/rest-api-doc)、
[OpenAIRE Graph](https://graph.openaire.eu/docs/11.3.0/apis/graph-api/quickstart/)、
[Semantic Scholar](https://webflow.semanticscholar.org/product/api/tutorial)。

## 分区证据

仅接受最新已核验版本的中科院**大类**一区、二区。JCR 的 Q1/Q2、影响因子、
出版社和引用量都不能替代此证据。旧名单移到 `paper_quality.pending_venues`。
记录要求如下（示例为虚构期刊，不应直接用于生产）：

```json
{
  "venues": [{
    "name": "Example Energy Journal",
    "issn_l": "1234-5678",
    "classification_system": "cas",
    "category_level": "major",
    "edition_year": 2025,
    "major_category": "工程技术",
    "partition": 1,
    "verified_at": "2026-09-29T00:00:00+00:00",
    "evidence_url": "https://example.edu/verified-cas-table"
  }]
}
```

本地文件证据用 `evidence_file`、`evidence_sha256`（64 位 SHA-256）和
`evidence_page` 替代 `evidence_url`。保留源文件以供核验。导入命令先校验全部记录，
再原子替换本地注册表，因此输入必须包含希望保留的全部期刊：

```powershell
python -m src.import_venues path/to/verified-venues.json
```

注册表默认位于 `data/private/cas_venues.json`，不随代码推送。2025 年计算机科学
Top 期刊 PDF 能证明其中 64 本期刊，不能据此推断其他学科的分区。
ISSN 优先匹配；只有缺失 ISSN 时，才按规范化期刊名称精确匹配。

## 采集、导入与恢复

在 Windows 使用项目虚拟环境，并设置 `PYTHONUTF8=1`。以下 `python` 指项目解释器。

```powershell
# 单月试采：预算是总分页请求数，不是论文数量上限
python -m src.backfill --date-from 2025-09-01 --date-to 2025-09-30 --max-requests 12 --no-enrich

# 明确起止日期的十年补采；相同命令续跑已有分页
python -m src.backfill --date-from 2016-09-29 --date-to 2026-09-29 --max-requests 120

# 使用某个渠道补采，同时执行默认两层参考文献、一层施引追溯
python -m src.backfill --date-from 2016-09-29 --date-to 2026-09-29 --sources openalex_search --max-requests 100 --trace-citations

# 同一文件重复导入不会增加论文数；数据库名称与文件哈希保留在原始记录中
python -m src.import_papers results.ris --database "Web of Science"
python -m src.import_papers results.bib results.csv savedrecs.txt --database "Campus export" --no-enrich
```

默认历史来源为四个独立索引，`--months 120` 可替代明确日期。
`--no-enrich` 跳过网络补证，不跳过准入。`--force` 从第一页重新扫描所选分片。
CSV 支持常见 WoS、Scopus、IEEE 列名；未知文献类型保留缓存，等待补证。

分页检查点位于 `data/state/paper_discovery/<source>/`，签名包含检索式、日期边界、
页大小和版本。每一页的记录与游标一起原子写入。429/503 等错误退避重试；
游标过期会重置为第一页并去重。只有来源明确结束分页，分片才标记 complete。
预算耗尽为 partial，缺少密钥为 unavailable；pending 表示尚未尝试。
新增期刊或检索式后会重新评估覆盖，已有页仍复用检查点。

Crossref 游标可能过期；重启扫描期间不会宣称完成。网络故障保留已经取得的记录。
同一工作目录应只运行一个写入采集进程，调度器使用进程内锁串行执行任务。

## 持久化与输出

处理顺序：原始记录 → 规范化 → DOI/来源标识去重 → 元数据补证 → 主题与质量准入。
不同 DOI 即使标题相似也不合并；无 DOI 时同时考虑标题、作者和年份。
跨来源保留字段来源、全部来源、版本链接和文献类型冲突信息；任何撤稿标记均拒收。
明确综述、社论、会议、预印本、勘误、撤稿或缺失分区证据的记录不进入合格库。

| 本地文件 | 用途 |
|---|---|
| `data/library/records.json` | 全部采集候选，含未通过准入的记录 |
| `data/library/admitted.json` | 累积合格论文，LLM 调用前持久化 |
| `data/library/enrichment.json` | DOI 补证缓存、时间及失败状态 |
| `data/library/summaries.json` | 按内容指纹复用的总结 |
| `data/library/coverage.json` | 来源、月份、检索式覆盖和错误 |
| `data/library/*citation_progress.json` | 引文队列、已完成任务、错误 |
| `data/library/quality_report.json` / `.md` | 渠道产出、合格数、摘要率、年份、主题、拒收原因和未完成分片 |
| `data/history/paper/` | 准入后的月度历史观测 |

跨来源 DOI 相同但缺失期刊、类型或摘要时，补查 Crossref 与 OpenAlex。
补证按预算轮转，缓存七天；失败与摘要仍缺失在质量报告中可见。
缺摘要的论文不会调用 LLM 生成内容总结。每次最多生成 50 篇新增或内容变化的
论文总结，可设置 `summarization.max_new_paper_summaries`；其他论文保持 pending。

网页 `/api/papers` 分页读取累积库，`/api/papers/quality` 返回详细质量报告。
卡片显示来源、2025 等分区版本和摘要完整状态。旧报告、分析的论文库标记失效时，
网页不会继续复用旧结论；研究报告按当前合格数据生成预览。

每周日 09:00 学术任务会增量采集，并按 `history_requests_per_run` 续跑历史，
再按 `citations.max_requests_per_run` 续跑引文队列。需要运行 `python scheduler.py`
或对应部署服务；仅修改配置不会启动后台服务。

## 验证

```powershell
python -m unittest discover -s test -p "test_*.py"
node --test test/web_workspace.test.cjs
python -m pip check
git diff --check
```

自动测试不使用真实凭据或外网，覆盖分页与恢复、重试、日期边界、跨源补证、分区缺失、
综述排除、重复导入、DOI 冲突、引文深度、摘要复用与网页接口。
实际新增数量必须另看质量报告。未配置的渠道和未核验的期刊不计作已完成覆盖。
