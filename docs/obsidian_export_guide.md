# Obsidian 导出指南

## 启用导出

Obsidian 集成只写 Markdown 文件，不依赖插件 API。推荐先输出到独立目录，确认结构后再把 `vault_path` 指向现有 vault。

```yaml
outputs:
  obsidian:
    enabled: true
    vault_path: "data/obsidian"
    use_markdown_links: true
```

执行 `python main.py` 后，导出器按来源生成：

```text
data/obsidian/
├── papers/
├── policies/
├── news/
├── industry_reports/
├── daily/
└── weekly/
```

每篇文档包含 YAML frontmatter、中文摘要、来源元数据、阅读优先级和相关主题。跨来源关联使用标准相对 Markdown 链接；`use_markdown_links: true` 可避免依赖 Obsidian 专有 wikilink 语法。文件名会替换 Windows 禁止字符。

## 验证

运行 `python -m unittest test.test_obsidian_exporter test.test_exporter_golden`。然后检查 `daily/YYYY-MM-DD.md` 是否包含四类目录索引，随机打开一篇政策和一篇论文，确认 frontmatter 可解析、外链可访问、关联链接能跳转。

若未生成文件，先确认管线已有规范化文档且 `outputs.obsidian.enabled` 为 `true`。若链接失效，不要手工改导出文件；应修复文档 `id/title/source_type` 或导出器路径规则并重新生成。
