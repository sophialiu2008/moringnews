from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml


def ensure_dir(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def load_yaml(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    try:
        with file_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        return data or {}
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"配置文件不存在：{file_path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML 解析失败：{file_path}，错误：{exc}") from exc
    except OSError as exc:
        raise OSError(f"读取 YAML 文件失败：{file_path}，错误：{exc}") from exc


def load_text(path: str | Path) -> str:
    file_path = Path(path)
    try:
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"文本文件不存在：{file_path}") from exc
    except OSError as exc:
        raise OSError(f"读取文本文件失败：{file_path}，错误：{exc}") from exc


def get_current_datetime(timezone: str) -> datetime:
    try:
        return datetime.now(ZoneInfo(timezone))
    except Exception as exc:
        raise ValueError(f"无效时区配置：{timezone}") from exc


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def setup_logger(log_dir: str | Path = "logs", timezone: str = "Asia/Shanghai") -> logging.Logger:
    ensure_dir(log_dir)
    logger = logging.getLogger("a_stock_morning_brief")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    now = get_current_datetime(timezone)
    log_path = Path(log_dir) / f"{now:%Y-%m-%d}.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger
