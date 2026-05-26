from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class QualityReport:
    passed: bool
    issues: list[str] = field(default_factory=list)
    metrics: dict[str, int] = field(default_factory=dict)

    def to_prompt_text(self) -> str:
        if self.passed:
            return "质量检查通过。"
        lines = ["质量检查未通过："]
        lines.extend(f"- {issue}" for issue in self.issues)
        if self.metrics:
            lines.append("")
            lines.append("检测指标：")
            lines.extend(f"- {key}: {value}" for key, value in self.metrics.items())
        return "\n".join(lines)


def check_brief_quality(brief: str, watchlist: dict[str, Any], settings: dict[str, Any]) -> QualityReport:
    quality_settings = settings.get("quality", {})
    issues: list[str] = []
    metrics: dict[str, int] = {}

    min_sections = int(quality_settings.get("min_sections", 9))
    min_global_rows = int(quality_settings.get("min_global_market_rows", 8))
    min_sector_count = int(quality_settings.get("min_sector_count", 5))
    min_source_count = int(quality_settings.get("min_source_count", 5))
    forbidden_words = quality_settings.get("forbidden_words") or []

    section_count = len(re.findall(r"^##\s+\d+\.", brief, flags=re.MULTILINE))
    metrics["sections"] = section_count
    if section_count < min_sections:
        issues.append(f"固定栏目不足，当前 {section_count} 个，要求至少 {min_sections} 个。")

    global_rows = _count_markdown_table_rows(_extract_section(brief, "2"))
    metrics["global_market_rows"] = global_rows
    if global_rows < min_global_rows:
        issues.append(f"隔夜外围市场表格行数不足，当前 {global_rows} 行，要求至少 {min_global_rows} 行。")

    sector_count = _count_subheadings(_extract_section(brief, "4"))
    metrics["sector_count"] = sector_count
    if sector_count < min_sector_count:
        issues.append(f"今日板块催化数量不足，当前 {sector_count} 个，要求至少 {min_sector_count} 个。")

    missing_holdings = _missing_holdings(brief, watchlist)
    metrics["missing_holdings"] = len(missing_holdings)
    if missing_holdings:
        issues.append(f"持仓风险检查未覆盖：{'、'.join(missing_holdings)}。")

    source_count = _count_sources(_extract_section(brief, "9"))
    metrics["source_count"] = source_count
    if source_count < min_source_count:
        issues.append(f"信息来源数量不足，当前 {source_count} 条，要求至少 {min_source_count} 条。")

    found_forbidden = [word for word in forbidden_words if word and word in brief]
    metrics["forbidden_words"] = len(found_forbidden)
    if found_forbidden:
        issues.append(f"出现禁止投资表述：{'、'.join(found_forbidden)}。")

    if _watchlist_note_as_fact_risk(brief, watchlist):
        issues.append("疑似把 watchlist 备注当作公告事实，请改为风险检查线索或标注依据不足。")

    return QualityReport(passed=not issues, issues=issues, metrics=metrics)


def _extract_section(markdown: str, number: str) -> str:
    pattern = rf"^##\s+{re.escape(number)}\.\s+.*?(?=^##\s+\d+\.|\Z)"
    match = re.search(pattern, markdown, flags=re.MULTILINE | re.DOTALL)
    return match.group(0) if match else ""


def _count_markdown_table_rows(section: str) -> int:
    count = 0
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        if re.fullmatch(r"\|[\s:\-|\u2014]+\|", stripped):
            continue
        if "项目" in stripped and "最新表现" in stripped:
            continue
        count += 1
    return count


def _count_subheadings(section: str) -> int:
    return len(re.findall(r"^###\s+\S+", section, flags=re.MULTILINE))


def _missing_holdings(brief: str, watchlist: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for holding in watchlist.get("holdings", []) or []:
        name = str(holding.get("name") or "").strip()
        code = str(holding.get("code") or "").strip()
        if name and name not in brief and code not in brief:
            missing.append(name or code)
    return missing


def _count_sources(section: str) -> int:
    lines = [line.strip() for line in section.splitlines()]
    source_lines = [
        line
        for line in lines
        if line.startswith("-")
        and any(keyword in line for keyword in ("来源", "发布时间", "链接", "标题", "支持"))
    ]
    if source_lines:
        return len(source_lines)

    non_empty_lines = [
        line
        for line in lines
        if line and not line.startswith("##") and "暂未获取到可靠数据" not in line
    ]
    return len(non_empty_lines)


def _watchlist_note_as_fact_risk(brief: str, watchlist: dict[str, Any]) -> bool:
    for holding in watchlist.get("holdings", []) or []:
        note = str(holding.get("note") or "").strip()
        if note and note in brief:
            return True
    return False
