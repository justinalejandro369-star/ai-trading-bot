"""
APScheduler job: run alert checks after analysis_scan_job completes.

Fetches all alert rules, fetches candles for each unique symbol,
evaluates the engine, persists AlertEvents, dispatches notifications.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd
import pandas_ta_classic as ta
from sqlalchemy import select, text

from app.alerts.discord_notifier import send_discord
from app.alerts.engine import check_alerts
from app.alerts.telegram_notifier import send_telegram
from app.core.database import async_session_factory
from app.models.alert import AlertEvent, AlertRule

__all__ = ["alert_check_job"]

log = logging.getLogger(__name__)


async def alert_check_job() -> None:
    """Evaluate all alert rules and dispatch notifications for triggered ones."""
    try:
        async with async_session_factory() as session:
            # Load all rules
            result = await session.execute(select(AlertRule))
            rules: list[AlertRule] = list(result.scalars().all())
            if not rules:
                return

            # Group rules by symbol
            by_symbol: dict[str, list[AlertRule]] = {}
            for rule in rules:
                by_symbol.setdefault(rule.symbol, []).append(rule)

            for symbol, sym_rules in by_symbol.items():
                try:
                    rows_result = await session.execute(
                        text("""
                            SELECT timestamp, open, high, low, close, volume
                            FROM market_data
                            WHERE symbol = :symbol AND interval = '1D'
                            ORDER BY timestamp ASC
                            LIMIT 50
                        """),
                        {"symbol": symbol},
                    )
                    rows = rows_result.fetchall()
                    if len(rows) < 2:
                        continue

                    df = pd.DataFrame(
                        rows, columns=["timestamp", "open", "high", "low", "close", "volume"]
                    )
                    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
                    df = df.set_index("timestamp")

                    rsi_series = ta.rsi(df["close"], length=14)

                    triggers = check_alerts(df.reset_index(), sym_rules, rsi_series=rsi_series)

                    now = datetime.now(tz=timezone.utc)
                    for trigger in triggers:
                        event = AlertEvent(
                            rule_id=trigger.rule_id,
                            triggered_at=now,
                            message=trigger.message,
                        )
                        session.add(event)
                        # Dispatch notifications (best-effort)
                        await send_telegram(trigger.message)
                        await send_discord(trigger.message)
                        log.info("alert_check_job: triggered %s -> %s", trigger.symbol, trigger.threshold_type)

                    await session.commit()

                except Exception as exc:
                    log.error("alert_check_job: error processing symbol %s: %s", symbol, exc)

    except Exception as exc:
        log.error("alert_check_job: fatal error: %s", exc)
