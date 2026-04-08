"""
APScheduler job: records equity snapshots every 5 min for all paper accounts.

equity_snapshot_job() is a purely DB-internal job — it NEVER calls any
external API. All price data is read from the market_data table that is
already populated by the ingestion jobs.

Job design:
  - Opens a single async session for the entire run.
  - Fetches all PaperAccount rows.
  - For each account, fetches all PaperPosition rows.
  - If positions exist, batch-queries MarketData for the latest price per symbol
    using a single WHERE symbol IN (...) query.
  - Calls compute_equity() with the position list and last_prices dict.
  - Inserts one EquitySnapshot row per account.
  - Commits once at the end (minimises round-trips).
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.market_data import MarketData
from app.models.paper_trading import EquitySnapshot, PaperAccount, PaperPosition
from app.paper_trading.engine import compute_equity

__all__ = ["equity_snapshot_job"]

log = logging.getLogger(__name__)


async def equity_snapshot_job() -> None:
    """
    Record a point-in-time equity snapshot for every active paper account.

    Registered with max_instances=1 in the scheduler so that if a job run
    takes longer than the 5-minute interval, the next run is skipped rather
    than stacking duplicate snapshot rows.

    Never raises — exceptions are logged so the scheduler does not crash.
    """
    try:
        async with async_session_factory() as session:
            # Fetch all accounts
            account_result = await session.execute(select(PaperAccount))
            accounts = account_result.scalars().all()

            if not accounts:
                log.debug("equity_snapshot_job: no paper accounts found — nothing to snapshot")
                return

            snapshots: list[EquitySnapshot] = []
            now = datetime.now(timezone.utc)

            for account in accounts:
                # Fetch open positions for this account
                pos_result = await session.execute(
                    select(PaperPosition).where(PaperPosition.account_id == account.id)
                )
                positions = pos_result.scalars().all()

                if not positions:
                    equity = account.cash_balance
                    positions_value = 0.0
                else:
                    # Batch-query latest price for every symbol in one round-trip
                    symbols = list({p.symbol for p in positions})
                    price_result = await session.execute(
                        select(MarketData)
                        .where(MarketData.symbol.in_(symbols))
                        .order_by(MarketData.timestamp.desc())
                    )
                    all_price_rows = price_result.scalars().all()

                    # Keep only the most-recent row per symbol
                    last_prices: dict[str, float] = {}
                    for row in all_price_rows:
                        if row.symbol not in last_prices:
                            last_prices[row.symbol] = row.close

                    positions_dicts = [
                        {
                            "symbol": p.symbol,
                            "quantity": p.quantity,
                            "avg_entry_price": p.avg_entry_price,
                        }
                        for p in positions
                    ]
                    equity = compute_equity(account.cash_balance, positions_dicts, last_prices)
                    positions_value = equity - account.cash_balance

                snapshots.append(
                    EquitySnapshot(
                        account_id=account.id,
                        recorded_at=now,
                        equity_value=equity,
                        cash=account.cash_balance,
                        positions_value=positions_value,
                    )
                )

            for snap in snapshots:
                session.add(snap)

            await session.commit()
            log.info(
                "equity_snapshot_job: recorded %d snapshot(s) at %s",
                len(snapshots),
                now.isoformat(),
            )

    except Exception as exc:
        log.error("equity_snapshot_job failed: %s", exc, exc_info=True)
