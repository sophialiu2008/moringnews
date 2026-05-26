from __future__ import annotations

import logging
import os
from typing import Any

from openai import OpenAI


class BailianClient:
    def __init__(
        self,
        model: str = "qwen-max",
        api_key: str | None = None,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        timeout: float = 120.0,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.base_url = base_url
        self.timeout = timeout
        self.logger = logging.getLogger("a_stock_morning_brief")

        if not self.api_key:
            raise ValueError("缺少 DASHSCOPE_API_KEY，无法调用阿里云百炼。")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)

    def chat(self, prompt: str, system_prompt: str | None = None, enable_search: bool = True) -> str:
        messages = self._build_messages(prompt, system_prompt)

        if enable_search:
            try:
                self.logger.info("调用阿里百炼模型：%s，enable_search=True", self.model)
                return self._create_chat(messages, extra_body={"enable_search": True})
            except Exception as exc:
                self.logger.warning(
                    "阿里百炼 enable_search 调用失败，将降级为普通模型调用。错误：%s",
                    exc,
                )

        try:
            self.logger.info("调用阿里百炼模型：%s，普通模式", self.model)
            return self._create_chat(messages)
        except Exception as exc:
            raise RuntimeError(f"阿里百炼模型调用失败：{exc}") from exc

    def _create_chat(self, messages: list[dict[str, str]], extra_body: dict[str, Any] | None = None) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
            extra_body=extra_body,
        )
        content = response.choices[0].message.content if response.choices else ""
        if not content:
            raise RuntimeError("阿里百炼返回内容为空。")
        return content.strip()

    @staticmethod
    def _build_messages(prompt: str, system_prompt: str | None = None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages
