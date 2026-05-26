from __future__ import annotations

import logging
import os
from typing import Any

import requests


def send_by_serverchan(title: str, content: str) -> bool:
    logger = logging.getLogger("a_stock_morning_brief")
    sendkey = os.getenv("SERVERCHAN_SENDKEY")
    if not sendkey:
        logger.info("未配置 SERVERCHAN_SENDKEY，跳过 Server酱推送。")
        return False

    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    try:
        response = requests.post(url, data={"title": title, "desp": content}, timeout=20)
        response.raise_for_status()
        result = response.json()
        if result.get("code") in (0, "0"):
            logger.info("Server酱推送成功。")
            return True
        logger.warning("Server酱推送返回异常：%s", result)
    except Exception as exc:
        logger.warning("Server酱推送失败：%s", exc)
    return False


def send_by_wxpusher(title: str, content: str) -> bool:
    logger = logging.getLogger("a_stock_morning_brief")
    app_token = os.getenv("WXPUSHER_APP_TOKEN")
    uid = os.getenv("WXPUSHER_UID")
    if not app_token or not uid:
        logger.info("未配置 WXPUSHER_APP_TOKEN 或 WXPUSHER_UID，跳过 WxPusher 推送。")
        return False

    payload = {
        "appToken": app_token,
        "content": content,
        "summary": title[:96],
        "contentType": 3,
        "uids": [uid],
    }
    try:
        response = requests.post(
            "https://wxpusher.zjiecode.com/api/send/message",
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        result = response.json()
        if result.get("code") in (1000, "1000", 0, "0"):
            logger.info("WxPusher 推送成功。")
            return True
        logger.warning("WxPusher 推送返回异常：%s", result)
    except Exception as exc:
        logger.warning("WxPusher 推送失败：%s", exc)
    return False


def send_notification(title: str, content: str, settings: dict[str, Any]) -> bool:
    logger = logging.getLogger("a_stock_morning_brief")
    notification_settings = settings.get("notification", {})

    if not notification_settings.get("enable_wechat", True):
        logger.info("settings.yaml 已关闭微信推送。")
        return False

    providers = notification_settings.get("provider_priority") or ["serverchan", "wxpusher"]
    for provider in providers:
        provider_name = str(provider).lower()
        if provider_name == "serverchan" and send_by_serverchan(title, content):
            return True
        if provider_name == "wxpusher" and send_by_wxpusher(title, content):
            return True

    logger.warning("所有微信推送渠道均未成功，主流程继续。")
    return False
