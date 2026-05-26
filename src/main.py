from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from brief_generator import BriefGenerator
from file_writer import save_brief
from notifier import send_notification
from utils import get_current_datetime, load_yaml, setup_logger


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")

    try:
        settings = load_yaml(PROJECT_ROOT / "config" / "settings.yaml")
        timezone = settings.get("app", {}).get("timezone", "Asia/Shanghai")
        log_dir = PROJECT_ROOT / settings.get("app", {}).get("log_dir", "logs")
        logger = setup_logger(log_dir, timezone)
    except Exception as exc:
        print(f"初始化失败：{exc}", file=sys.stderr)
        return 1

    try:
        now = get_current_datetime(timezone)
        date_text = now.strftime("%Y-%m-%d")
        logger.info("开始运行 A股每日盘前情报简报系统，日期：%s", date_text)

        generator = BriefGenerator(PROJECT_ROOT, settings)
        final_brief, wechat_summary = generator.run(now)

        output_dir = PROJECT_ROOT / settings.get("app", {}).get("output_dir", "briefings")
        filename_format = settings.get("brief", {}).get("filename_format", "{date}-A股盘前简报.md")
        brief_path = save_brief(final_brief, output_dir, date_text, filename_format)
        logger.info("简报已保存：%s", brief_path)

        notification_settings = settings.get("notification", {})
        push_full_text = notification_settings.get("push_full_text", False)
        push_content = final_brief if push_full_text else wechat_summary
        title = f"A股盘前简报｜{date_text}"
        pushed = send_notification(title, push_content, settings)
        logger.info("微信推送结果：%s", "成功" if pushed else "未推送或推送失败")

        logger.info("运行完成。简报路径：%s", brief_path)
        return 0
    except Exception as exc:
        logger.exception("主流程失败：%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
