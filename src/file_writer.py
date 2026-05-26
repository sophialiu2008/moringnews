from __future__ import annotations

from pathlib import Path

from utils import ensure_dir


def get_brief_path(output_dir: str | Path, date: str, filename_format: str = "{date}-A股盘前简报.md") -> Path:
    directory = ensure_dir(output_dir)
    filename = filename_format.format(date=date)
    return directory / filename


def save_brief(
    content: str,
    output_dir: str | Path,
    date: str,
    filename_format: str = "{date}-A股盘前简报.md",
) -> Path:
    path = get_brief_path(output_dir, date, filename_format)
    try:
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise OSError(f"保存简报失败：{path}，错误：{exc}") from exc
    return path
