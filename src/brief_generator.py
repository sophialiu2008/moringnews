from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from llm_client import LLMClient
from market_data import collect_optional_market_data
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
        self.deepseek_template = load_text(self.prompts_dir / "deepseek_refine_prompt.txt")
        self.wechat_template = load_text(self.prompts_dir / "wechat_summary_prompt.txt")
        self.llm_client = LLMClient(settings, self.deepseek_template, self.wechat_template)

    def build_morning_prompt(self, now: datetime) -> str:
        date_text = now.strftime("%Y-%m-%d")
        time_text = now.strftime("%Y-%m-%d %H:%M:%S %Z")
        market_data = collect_optional_market_data(self.settings, self.watchlist)

        return self.morning_template.format(
            date=date_text,
            time=time_text,
            research_context=self.research_context,
            watchlist=json.dumps(self.watchlist, ensure_ascii=False, indent=2),
            sources=json.dumps(self.sources, ensure_ascii=False, indent=2),
            market_data=json.dumps(market_data, ensure_ascii=False, indent=2),
        )

    def generate_brief(self, now: datetime) -> str:
        prompt = self.build_morning_prompt(now)
        self.logger.info("开始生成 A股盘前简报初稿。")
        return self.llm_client.generate_initial_brief(prompt)

    def refine_brief(self, brief: str) -> str:
        self.logger.info("开始执行可选 DeepSeek 二次优化。")
        return self.llm_client.refine_brief(brief)

    def build_wechat_summary(self, brief: str) -> str:
        self.logger.info("开始生成微信推送摘要。")
        return self.llm_client.summarize_for_wechat(brief)

    def run(self, now: datetime) -> tuple[str, str]:
        initial_brief = self.generate_brief(now)
        final_brief = self.refine_brief(initial_brief)
        wechat_summary = self.build_wechat_summary(final_brief)
        return final_brief, wechat_summary
