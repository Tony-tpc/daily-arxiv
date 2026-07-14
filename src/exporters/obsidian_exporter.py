"""Vault-friendly Markdown export using standard Markdown links."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml


SOURCE_DIRECTORIES = {
    "paper": "papers",
    "policy": "policies",
    "news": "news",
    "industry_report": "industry_reports",
}


class ObsidianExporter:
    """Export canonical documents into an Obsidian-compatible vault tree."""

    def __init__(self, config: Dict[str, Any]):
        settings = config.get("outputs", {}).get("obsidian", {})
        self.vault_path = Path(settings.get("vault_path", "data/obsidian"))
        self.use_markdown_links = bool(settings.get("use_markdown_links", True))

    def export_documents(
        self,
        documents: List[Dict[str, Any]],
        export_date: str | None = None,
    ) -> Dict[str, Any]:
        """Export documents plus a daily index and return written paths."""
        export_date = export_date or date.today().isoformat()
        self._ensure_directories()
        path_index = {
            str(document.get("id") or ""): self.document_path(document)
            for document in documents
            if document.get("id")
        }
        document_paths = []
        for document in documents:
            target = self.document_path(document)
            target.write_text(
                self.render_document(document, target, path_index), encoding="utf-8"
            )
            document_paths.append(str(target))

        daily_path = self.vault_path / "daily" / f"{export_date}.md"
        daily_path.write_text(
            self._render_index("每日研究情报", export_date, documents, daily_path, path_index),
            encoding="utf-8",
        )
        return {
            "vault_path": str(self.vault_path),
            "document_paths": document_paths,
            "daily_path": str(daily_path),
            "count": len(document_paths),
        }

    def export_weekly(
        self,
        documents: List[Dict[str, Any]],
        period_label: str,
    ) -> str:
        """Write a weekly index that links to already exported document notes."""
        self._ensure_directories()
        path_index = {
            str(document.get("id") or ""): self.document_path(document)
            for document in documents
            if document.get("id")
        }
        for document in documents:
            target = self.document_path(document)
            if not target.exists():
                target.write_text(
                    self.render_document(document, target, path_index), encoding="utf-8"
                )
        weekly_path = self.vault_path / "weekly" / f"{safe_filename(period_label)}.md"
        weekly_path.write_text(
            self._render_index("每周研究情报", period_label, documents, weekly_path, path_index),
            encoding="utf-8",
        )
        return str(weekly_path)

    def document_path(self, document: Dict[str, Any]) -> Path:
        source_type = str(document.get("source_type") or "")
        if source_type not in SOURCE_DIRECTORIES:
            raise ValueError(f"Unsupported source_type for Obsidian export: {source_type}")
        document_id = str(document.get("id") or document.get("url") or document.get("title") or "")
        digest = hashlib.sha1(document_id.encode("utf-8")).hexdigest()[:8]
        filename = f"{safe_filename(document.get('title') or '未命名')}-{digest}.md"
        return self.vault_path / SOURCE_DIRECTORIES[source_type] / filename

    def render_document(
        self,
        document: Dict[str, Any],
        current_path: Path,
        path_index: Dict[str, Path] | None = None,
    ) -> str:
        """Render one note with searchable frontmatter and standard links."""
        suggestion = document.get("reading_suggestion") or {}
        tags = _unique([*(document.get("tags") or []), *(document.get("themes") or [])])
        related_topics = _unique(suggestion.get("related_topics", []))
        frontmatter = {
            "id": document.get("id"),
            "tags": tags,
            "source_type": document.get("source_type"),
            "priority": suggestion.get("read_priority", "medium"),
            "published_at": document.get("published_at") or "",
            "related_topics": related_topics,
            "source_name": document.get("source_name") or "",
            "url": document.get("url") or "",
        }
        lines = [
            "---",
            yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip(),
            "---",
            "",
            f"# {document.get('title') or '未命名文档'}",
            "",
        ]
        if document.get("url"):
            lines.extend([f"[查看原文]({document['url']})", ""])
        lines.extend(["## 摘要", "", str(document.get("summary") or "暂无摘要"), ""])

        viewpoints = document.get("core_viewpoints") or []
        if viewpoints:
            lines.extend(["## 核心观点", "", *[f"- {item}" for item in viewpoints], ""])
        if document.get("research_relevance"):
            lines.extend([
                "## 与研究方向的关系", "", str(document["research_relevance"]), "",
            ])
        lines.extend([
            "## 阅读建议", "",
            f"- 优先级：{suggestion.get('read_priority', 'medium')}",
            f"- 建议动作：{suggestion.get('recommended_action', '复核')}",
            f"- 推荐依据：{suggestion.get('why_relevant', '暂无')}",
            "",
        ])

        related = document.get("related_documents") or []
        if related:
            lines.extend(["## 关联情报", ""])
            for item in related:
                link = self._related_link(item, current_path, path_index or {})
                relation = item.get("relationship") or "related"
                reason = item.get("reason") or ""
                lines.append(f"- {link} · {relation}" + (f" · {reason}" if reason else ""))
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def _related_link(
        self, related: Dict[str, Any], current_path: Path, path_index: Dict[str, Path]
    ) -> str:
        title = escape_link_text(related.get("title") or "关联文档")
        target = path_index.get(str(related.get("id") or ""))
        if target is not None:
            relative = Path("..", target.parent.name, target.name).as_posix()
            return self._format_local_link(title, relative)
        return f"[{title}]({related.get('url') or '#'})"

    def _render_index(
        self,
        heading: str,
        period: str,
        documents: List[Dict[str, Any]],
        current_path: Path,
        path_index: Dict[str, Path],
    ) -> str:
        lines = [f"# {heading} · {period}", ""]
        for source_type, directory in SOURCE_DIRECTORIES.items():
            selected = [item for item in documents if item.get("source_type") == source_type]
            if not selected:
                continue
            lines.extend([f"## {directory}", ""])
            for document in selected:
                target = path_index.get(str(document.get("id") or ""))
                if target is None:
                    continue
                relative = Path("..", target.parent.name, target.name).as_posix()
                title = escape_link_text(document.get('title') or '未命名')
                lines.append(f"- {self._format_local_link(title, relative)}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def _ensure_directories(self) -> None:
        for directory in [*SOURCE_DIRECTORIES.values(), "daily", "weekly"]:
            (self.vault_path / directory).mkdir(parents=True, exist_ok=True)

    def _format_local_link(self, title: str, relative: str) -> str:
        if self.use_markdown_links:
            return f"[{title}]({relative})"
        return f"[[{relative.removesuffix('.md')}|{title}]]"


def safe_filename(value: Any) -> str:
    """Create a readable Windows-safe filename while retaining Chinese text."""
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text).strip(" .-")
    return (text[:80].rstrip(" .-") or "untitled")


def escape_link_text(value: Any) -> str:
    return str(value or "").replace("[", "\\[").replace("]", "\\]")


def _unique(values: Iterable[Any]) -> List[str]:
    return list(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))
