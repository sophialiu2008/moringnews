from __future__ import annotations

import logging

from bailian_client import BailianClient
from deepseek_client import DeepSeekClient


class LLMClient:
    def __init__(
        self,
        settings: dict,
        deepseek_refine_template: str,
        wechat_summary_template: str,
    ) -> None:
        llm_settings = settings.get("llm", {})
        search_settings = settings.get("search", {})
        generation_settings = settings.get("generation", {})
        self.logger = logging.getLogger("a_stock_morning_brief")

        self.enable_web_search = bool(search_settings.get("enable_web_search", True))
        self.enable_deepseek_refine = bool(llm_settings.get("enable_deepseek_refine", True))
        self.deepseek_refine_template = deepseek_refine_template
        self.wechat_summary_template = wechat_summary_template
        self.primary_max_tokens = generation_settings.get("primary_max_tokens", 6000)
        self.secondary_max_tokens = generation_settings.get("secondary_max_tokens", 6000)
        self.summary_max_tokens = generation_settings.get("summary_max_tokens", 1800)
        self.research_max_tokens = generation_settings.get("research_max_tokens", 6000)
        self.filter_max_tokens = generation_settings.get("filter_max_tokens", 5000)
        self.quality_fix_max_tokens = generation_settings.get("quality_fix_max_tokens", 6000)

        primary_model = llm_settings.get("primary_model", "qwen-max")
        secondary_model = llm_settings.get("secondary_model", "deepseek-chat")

        self.bailian = BailianClient(model=primary_model, max_tokens=self.primary_max_tokens)
        self.deepseek = DeepSeekClient(model=secondary_model, max_tokens=self.secondary_max_tokens)

    def collect_research_notes(self, prompt: str) -> str:
        return self.bailian.chat(
            prompt,
            system_prompt="你是严谨的 A股盘前资料收集员。只收集事实和来源，不输出交易建议。",
            enable_search=self.enable_web_search,
            max_tokens=self.research_max_tokens,
        )

    def filter_signals(self, prompt: str) -> str:
        return self.bailian.chat(
            prompt,
            system_prompt="你是严谨的 A股盘前信号过滤员。只保留有来源、有时间、有交易意义的信息。",
            enable_search=False,
            max_tokens=self.filter_max_tokens,
        )

    def generate_initial_brief(self, prompt: str) -> str:
        return self.bailian.chat(
            prompt,
            system_prompt="你是严谨的 A股盘前研究助手。必须基于可靠来源，不编造数据，不给确定性投资建议。",
            enable_search=self.enable_web_search,
            max_tokens=self.primary_max_tokens,
        )

    def refine_brief(self, brief: str) -> str:
        if not self.enable_deepseek_refine:
            self.logger.info("settings.yaml 已关闭 DeepSeek 二次优化。")
            return brief

        if not self.deepseek.available:
            self.logger.info("DeepSeek 不可用，直接使用阿里百炼初稿。")
            return brief

        prompt = self.deepseek_refine_template.format(brief=brief)
        try:
            return self.deepseek.chat(
                prompt,
                system_prompt="你是严谨的 A股交易研究员，只做研究辅助和风险提示。",
                max_tokens=self.secondary_max_tokens,
            )
        except Exception as exc:
            self.logger.warning("DeepSeek 二次优化失败，将使用阿里百炼初稿。错误：%s", exc)
            return brief

    def fix_brief_quality(self, prompt: str) -> str:
        return self.bailian.chat(
            prompt,
            system_prompt="你是 A股盘前简报质检修订员。只修复结构和依据不足问题，不编造数据。",
            enable_search=False,
            max_tokens=self.quality_fix_max_tokens,
        )

    def summarize_for_wechat(self, brief: str) -> str:
        prompt = self.wechat_summary_template.format(brief=brief)

        if self.deepseek.available:
            try:
                return self.deepseek.chat(
                    prompt,
                    system_prompt="你是盘前简报摘要助手，输出简洁、克制、无确定性投资建议。",
                    max_tokens=self.summary_max_tokens,
                )
            except Exception as exc:
                self.logger.warning("DeepSeek 微信摘要生成失败，将改用阿里百炼。错误：%s", exc)

        try:
            return self.bailian.chat(
                prompt,
                system_prompt="你是盘前简报摘要助手，输出 1000 字以内微信摘要。",
                enable_search=False,
                max_tokens=self.summary_max_tokens,
            )
        except Exception as exc:
            self.logger.warning("微信摘要生成失败，将使用完整简报前 1000 字作为兜底。错误：%s", exc)
            return brief[:1000]
