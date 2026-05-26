from __future__ import annotations

import logging
from typing import Any


def get_a_stock_calendar() -> dict[str, Any]:
    logger = logging.getLogger("a_stock_morning_brief")
    try:
        import akshare as ak  # type: ignore

        calendar = ak.tool_trade_date_hist_sina()
        return {"trade_calendar_tail": calendar.tail(5).to_dict(orient="records")}
    except ImportError:
        logger.info("未安装 AKShare，跳过 A股交易日历获取。")
    except Exception as exc:
        logger.warning("获取 A股交易日历失败：%s", exc)
    return {}


def get_market_snapshot() -> dict[str, Any]:
    logger = logging.getLogger("a_stock_morning_brief")
    try:
        import akshare as ak  # type: ignore

        spot = ak.stock_zh_index_spot_sina()
        important = spot[spot["名称"].isin(["上证指数", "深证成指", "创业板指"])]
        return {"a_stock_indexes": important.to_dict(orient="records")}
    except ImportError:
        logger.info("未安装 AKShare，跳过 A股行情快照获取。")
    except Exception as exc:
        logger.warning("获取 A股行情快照失败：%s", exc)
    return {}


def get_global_snapshot() -> dict[str, Any]:
    logger = logging.getLogger("a_stock_morning_brief")
    try:
        import akshare as ak  # type: ignore

        futures = ak.futures_global_commodity_name_url_map()
        return {"global_snapshot_hint": f"AKShare 可用，已识别全球期货映射数量：{len(futures)}"}
    except ImportError:
        logger.info("未安装 AKShare，跳过外围市场快照获取。")
    except Exception as exc:
        logger.warning("获取外围市场快照失败：%s", exc)
    return {}


def get_sector_snapshot() -> dict[str, Any]:
    logger = logging.getLogger("a_stock_morning_brief")
    try:
        import akshare as ak  # type: ignore

        sectors = ak.stock_board_industry_name_em()
        return {"sector_sample": sectors.head(20).to_dict(orient="records")}
    except ImportError:
        logger.info("未安装 AKShare，跳过板块快照获取。")
    except Exception as exc:
        logger.warning("获取板块快照失败：%s", exc)
    return {}


def get_watchlist_snapshot(watchlist: dict[str, Any]) -> dict[str, Any]:
    logger = logging.getLogger("a_stock_morning_brief")
    stocks = (watchlist.get("holdings") or []) + (watchlist.get("watch_stocks") or [])
    if not stocks:
        return {}

    try:
        import akshare as ak  # type: ignore

        spot = ak.stock_zh_a_spot_em()
        codes = {stock.get("code") for stock in stocks if stock.get("code")}
        filtered = spot[spot["代码"].isin(codes)]
        return {"watchlist_quotes": filtered.to_dict(orient="records")}
    except ImportError:
        logger.info("未安装 AKShare，跳过持仓和关注股行情获取。")
    except Exception as exc:
        logger.warning("获取持仓和关注股行情失败：%s", exc)
    return {}


def collect_optional_market_data(settings: dict[str, Any], watchlist: dict[str, Any]) -> dict[str, Any]:
    market_settings = settings.get("market", {})
    if not market_settings.get("enable_akshare", False):
        return {"status": "settings.yaml 未启用 AKShare，本地行情数据为空，由联网搜索补充。"}

    data: dict[str, Any] = {}
    data.update(get_a_stock_calendar())
    data.update(get_market_snapshot())
    data.update(get_global_snapshot())
    data.update(get_sector_snapshot())
    data.update(get_watchlist_snapshot(watchlist))
    return data
