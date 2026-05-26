from __future__ import annotations

import logging
import os

from openai import OpenAI


class DeepSeekClient:
    def __init__(
        self,
        model: str = "deepseek-chat",
        api_key: str | None = None,
        base_url: str = "https://api.deepseek.com",
        timeout: float = 120.0,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = base_url
        self.timeout = timeout
        self.available = bool(self.api_key)
        self.logger = logging.getLogger("a_stock_morning_brief")
        self.client = (
            OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
            if self.available
            else None
        )

        if not self.available:
            self.logger.info("未配置 DEEPSEEK_API_KEY，将跳过 DeepSeek 二次分析。")

    def chat(self, prompt: str, system_prompt: str | None = None) -> str:
        if not self.available or self.client is None:
            raise RuntimeError("DeepSeek 未配置，无法调用。")

        messages = self._build_messages(prompt, system_prompt)
        try:
            self.logger.info("调用 DeepSeek 模型：%s", self.model)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
            )
        except Exception as exc:
            raise RuntimeError(f"DeepSeek 模型调用失败：{exc}") from exc

        content = response.choices[0].message.content if response.choices else ""
        if not content:
            raise RuntimeError("DeepSeek 返回内容为空。")
        return content.strip()

    @staticmethod
    def _build_messages(prompt: str, system_prompt: str | None = None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages
