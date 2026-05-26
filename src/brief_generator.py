from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from llm_client import LLMClient
from market_data import collect_optional_market_data
from quality_checker import check_brief_quality
from utils import load_text, load_yaml


class BriefGenerator:
    def __init__(self, project_root: Path, settings: dict[str, Any]) -> None:
        self.project_root = project_root
        self.settings = settings
        self.logger = logging.getLogger("a_stock_morning_brief")

        self.config_dir = project_root / "config"
        self.prompts_dir = project_root / "prompts"

        self.research_context = load_text(self.config_dir / "research_context.md")
        self.watchlist = load_yaml(self.config_dir / "watchlist.yaml")
        self.sources = load_yaml(self.config_dir / "sources.yaml")

        self.morning_template = load_text(self.prompts_dir / "morning_brief_prompt.txt")
        self.research_collection_template = load_text(self.prompts_dir / "research_collection_prompt.txt")
        self.signal_filter_template = load_text(self.prompts_dir / "signal_filter_prompt.txt")
        self.deepseek_template = load_text(self.prompts_dir / "deepseek_refine_prompt.txt")
        self.wechat_template = load_text(self.prompts_dir / "wechat_summary_prompt.txt")
        self.quality_fix_template = load_text(self.prompts_dir / "quality_fix_prompt.txt")
        self.llm_client = LLMClient(settings, self.deepseek_template, self.wechat_template)

    def _common_prompt_values(self, now: datetime) -> dict[str, str]:
        date_text = now.strftime("%Y-%m-%d")
        time_text = now.strftime("%Y-%m-%d %H:%M:%S %Z")
        market_data = collect_optional_market_data(self.settings, self.watchlist)
        max_reading_minutes = self.settings.get("brief", {}).get("max_reading_minutes", 10)
        time_range_hours = self.settings.get("search", {}).get("time_range_hours", 24)

        return {
            "date": date_text,
            "time": time_text,
            "time_range_hours": str(time_range_hours),
            "max_reading_minutes": str(max_reading_minutes),
            "research_context": self.research_context,
            "watchlist": json.dumps(self.watchlist, ensure_ascii=False, indent=2),
            "sources": json.dumps(self.sources, ensure_ascii=False, indent=2),
            "market_data": json.dumps(market_data, ensure_ascii=False, indent=2),
        }

    def build_research_collection_prompt(self, now: datetime) -> str:
        return self.research_collection_template.format(**self._common_prompt_values(now))

    def build_signal_filter_prompt(self, research_notes: str) -> str:
        return self.signal_filter_template.format(
            research_context=self.research_context,
            watchlist=json.dumps(self.watchlist, ensure_ascii=False, indent=2),
            research_notes=research_notes,
        )

    def build_morning_prompt(self, now: datetime, filtered_signals: str = "") -> str:
        values = self._common_prompt_values(now)
        values["filtered_signals"] = filtered_signals or "未启用多阶段研究，请按研究上下文和联网搜索直接生成。"
        return self.morning_template.format(**values)

    def collect_research_notes(self, now: datetime) -> str:
        self.logger.info("开始分阶段研究：收集盘前资料。")
        return self.llm_client.collect_research_notes(self.build_research_collection_prompt(now))

    def filter_signals(self, research_notes: str) -> str:
        self.logger.info("开始分阶段研究：过滤有效信号。")
        return self.llm_client.filter_signals(self.build_signal_filter_prompt(research_notes))

    def generate_brief(self, now: datetime, filtered_signals: str = "") -> str:
        prompt = self.build_morning_prompt(now, filtered_signals)
        self.logger.info("开始生成 A股盘前简报初稿。")
        return self.llm_client.generate_initial_brief(prompt)

    def refine_brief(self, brief: str) -> str:
        self.logger.info("开始执行可选 DeepSeek 二次优化。")
        return self.llm_client.refine_brief(brief)

    def build_wechat_summary(self, brief: str) -> str:
        self.logger.info("开始生成微信推送摘要。")
        return self.llm_client.summarize_for_wechat(brief)

    def ensure_quality(self, brief: str, now: datetime, filtered_signals: str) -> str:
        quality_settings = self.settings.get("quality", {})
        if not quality_settings.get("enable_quality_check", True):
            self.logger.info("settings.yaml 已关闭简报质量检查。")
            return brief

        report = check_brief_quality(brief, self.watchlist, self.settings)
        if report.passed:
            self.logger.info("简报质量检查通过：%s", report.metrics)
            return brief

        self.logger.warning("简报质量检查未通过：%s", report.to_prompt_text())
        if not quality_settings.get("auto_fix", True):
            return brief

        max_attempts = int(quality_settings.get("max_fix_attempts", 1))
        fixed_brief = brief
        for attempt in range(max_attempts):
            self.logger.info("开始自动修订简报质量，第 %s 次。", attempt + 1)
            prompt = self.quality_fix_template.format(
                date=now.strftime("%Y-%m-%d"),
                quality_issues=report.to_prompt_text(),
                research_context=self.research_context,
                watchlist=json.dumps(self.watchlist, ensure_ascii=False, indent=2),
                filtered_signals=filtered_signals,
                brief=fixed_brief,
            )
            try:
                fixed_brief = self.llm_client.fix_brief_quality(prompt)
            except Exception as exc:
                self.logger.warning("自动修订简报失败，将保留当前版本。错误：%s", exc)
                return brief

            report = check_brief_quality(fixed_brief, self.watchlist, self.settings)
            if report.passed:
                self.logger.info("自动修订后质量检查通过：%s", report.metrics)
                return fixed_brief
            self.logger.warning("自动修订后仍未完全通过：%s", report.to_prompt_text())

        return fixed_brief

    def run(self, now: datetime) -> tuple[str, str]:
        filtered_signals = ""
        if self.settings.get("search", {}).get("enable_multistage_research", True):
            research_notes = self.collect_research_notes(now)
            filtered_signals = self.filter_signals(research_notes)

        initial_brief = self.generate_brief(now, filtered_signals)
        final_brief = self.refine_brief(initial_brief)
        final_brief = self.ensure_quality(final_brief, now, filtered_signals)
        wechat_summary = self.build_wechat_summary(final_brief)
        return final_brief, wechat_summary
