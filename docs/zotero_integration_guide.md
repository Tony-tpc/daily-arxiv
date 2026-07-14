# Zotero 基础集成指南

## 能力范围

当前实现提供两条只读/可移植路径：读取 Zotero Desktop Local API，以及把规范化论文导出为 CSL-JSON 与 BibTeX。管线不会自动写入或修改 Zotero 文库；政策、新闻和行业报告不会伪装成论文条目。

```yaml
outputs:
  zotero:
    enabled: true
    mode: "local_api"
    base_url: "http://localhost:23119/api"
    user_id: 0
    timeout_seconds: 5
    export_directory: "data/zotero"
```

在 Zotero Desktop 设置中启用本地 API 并保持应用运行。执行 `python main.py` 后会生成：

- `data/zotero/papers.csl.json`：适合引用处理器和跨工具交换。
- `data/zotero/papers.bib`：适合 LaTeX/BibTeX 导入。

字段映射包括标题、作者、摘要、发布日期、DOI、URL、标签和确定性 citekey。作者采用 literal 形式，避免中英文姓名被错误拆分。citekey 由第一作者、年份和标题首词组成；相同输入应得到相同结果。

## 验证与故障处理

运行 `python -m unittest test.test_zotero_client`。导入前先在临时 Zotero 文库检查条目数、DOI 和作者；重复导入由 Zotero 端处理。403 通常表示 Local API 未启用，连接拒绝表示 Zotero 未运行或端口不同。不要在配置中保存远程 Zotero token，也不要把 `data/zotero/` 生成物提交到 Git。
