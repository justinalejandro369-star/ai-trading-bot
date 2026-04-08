"""
Paper trading REST API router.

Five endpoints covering all four PAPER-* requirements:
  PAPER-01: POST /paper/accounts — create account
  PAPER-01: GET  /paper/accounts/{account_id} — account summary (equity + open positions)
  PAPER-02: POST /paper/accounts/{account_id}/orders — place buy or sell order
  PAPER-03: GET  /paper/accounts/{account_id}/equity — equity curve time series
  PAPER-04: GET  /paper/accounts/{account_id}/compare — paper vs. backtest equity curves

No business logic lives in this file — all fill calculations are delegated to
app.paper_trading.engine (fill_order, compute_equity). The routes handle
DB access, request/response marshalling, and HTTP error translation only.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.market_data import get_session
from app.models.backtest import BacktestRun
from app.models.market_data import MarketData
from app.models.paper_trading import EquitySnapshot, PaperAccount, PaperPosition
from app.paper_trading.engine import compute_equity, fill_order
from app.paper_trading.models import CreateAccountRequest, PlaceOrderRequest

__all__ = ["router"]

log = logging.getLogger(__name__)

router = APIRouter(prefix="/paper", tags=["paper-trading"])


# ---------------------------------------------------------------------------
# Endpoint 1: POST /paper/accounts  (PAPER-01)
# ---------------------------------------------------------------------------


@router.post("/accounts", status_code=200)
async def create_account(
    body: CreateAccountRequest,
    session: AsyncSession = Depends(get_session),  # type: ignore[assignment]
) -> dict:
    """
    Create a new paper trading account.

    Args:
        body: CreateAccountRequest with name, starting_balance, slippage_std,
              commission, and optional backtest_run_id.
        session: Injected async DB session.

    Returns:
        Created account dict with id, name, cash_balance, and configuration.
    """
    account = PaperAccount(
        name=body.name,
        created_at=datetime.now(timezone.utc),
        starting_balance=body.starting_balance,
        cash_balance=body.starting_balance,
        slippage_std=body.slippage_std,
        commission=body.commission,
        backtest_run_id=body.backtest_run_id,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)

    log.info("Created paper account id=%d name=%r balance=%.2f", account.id, account.name, account.cash_balance)

    return {
        "id": account.id,
        "name": account.name,
        "cash_balance": account.cash_balance,
        "starting_balance": account.starting_balance,
        "slippage_std": account.slippage_std,
        "commission": account.commission,
        "backtest_run_id": account.backtest_run_id,
    }


# ---------------------------------------------------------------------------
# Endpoint 2: GET /paper/accounts/{account_id}  (PAPER-01)
# ---------------------------------------------------------------------------


@router.get("/accounts/{account_id}")
async def get_account_summary(
    account_id: int,
    session: AsyncSession = Depends(get_session),  # type: ignore[assignment]
) -> dict:
    """
    Return account summary including cash balance, open positions, and total equity.

    Args:
        account_id: ID of the paper trading account.
        session: Injected async DB session.

    Returns:
        Account dict with id, name, cash_balance, starting_balance, total_equity,
        slippage_std, commission, backtest_run_id, and open_positions list.

    Raises:
        HTTPException 404: If the account does not exist.
    """
    account = await session.get(PaperAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"Paper account {account_id} not found")

    # Load all open positions for this account
    pos_result = await session.execute(
        select(PaperPosition).where(PaperPosition.account_id == account_id)
    )
    positions = pos_result.scalars().all()

    # Build last_prices via a single batch query — avoids N+1 DB round-trips
    last_prices: dict[str, float] = {}
    if positions:
        symbols = list({p.symbol for p in positions})
        price_result = await session.execute(
            select(MarketData)
            .where(MarketData.symbol.in_(symbols))
            .order_by(MarketData.timestamp.desc())
        )
        all_rows = price_result.scalars().all()
        # Keep only the most-recent row per symbol
        for row in all_rows:
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
    total_equity = compute_equity(account.cash_balance, positions_dicts, last_prices)

    return {
        "id": account.id,
        "name": account.name,
        "cash_balance": account.cash_balance,
        "starting_balance": account.starting_balance,
        "total_equity": total_equity,
        "slippage_std": account.slippage_std,
        "commission": account.commission,
        "backtest_run_id": account.backtest_run_id,
        "open_positions": [
            {
                "symbol": p.symbol,
                "interval": p.interval,
                "quantity": p.quantity,
                "avg_entry_price": p.avg_entry_price,
            }
            for p in positions
        ],
    }


# ---------------------------------------------------------------------------
# Endpoint 3: POST /paper/accounts/{account_id}/orders  (PAPER-02)
# ---------------------------------------------------------------------------


@router.post("/accounts/{account_id}/orders", status_code=201)
async def place_order(
    account_id: int,
    body: PlaceOrderRequest,
    session: AsyncSession = Depends(get_session),  # type: ignore[assignment]
) -> dict:
    """
    Place a simulated BUY or SELL order for a paper trading account.

    Fetches the latest close price from market_data, applies slippage and
    commission via fill_order(), persists the updated position, and records
    an EquitySnapshot immediately after fill.

    Args:
        account_id: ID of the paper trading account.
        body: PlaceOrderRequest with symbol, interval, side, and quantity.
        session: Injected async DB session.

    Returns:
        201 response with fill_price, quantity, commission_paid, new_cash,
        realized_pnl, and account_id.

    Raises:
        HTTPException 404: If the account does not exist.
        HTTPException 422: If no market data exists for the symbol/interval.
        HTTPException 422: If fill_order() raises ValueError (e.g., insufficient cash).
    """
    account = await session.get(PaperAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"Paper account {account_id} not found")

    symbol = body.symbol.upper()

    # Fetch latest close price for the requested symbol/interval
    price_result = await session.execute(
        select(MarketData)
        .where(MarketData.symbol == symbol, MarketData.interval == body.interval)
        .order_by(MarketData.timestamp.desc())
        .limit(1)
    )
    price_row = price_result.scalars().first()
    if price_row is None:
        raise HTTPException(
            status_code=422,
            detail=f"No market data for {symbol}/{body.interval}",
        )

    last_price = price_row.close

    # Find existing position for this symbol (if any)
    pos_result = await session.execute(
        select(PaperPosition).where(
            PaperPosition.account_id == account_id,
            PaperPosition.symbol == symbol,
        )
    )
    existing_position = pos_result.scalars().first()
    existing_qty = existing_position.quantity if existing_position else 0.0
    existing_avg = existing_position.avg_entry_price if existing_position else 0.0

    # Simulate the fill
    try:
        fill_result = fill_order(
            side=body.side,
            symbol=symbol,
            quantity=body.quantity,
            last_price=last_price,
            cash_balance=account.cash_balance,
            position_qty=existing_qty,
            avg_entry_price=existing_avg,
            slippage_std=account.slippage_std,
            commission=account.commission,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Apply fill: update or create position, update account cash
    if body.side == "BUY":
        if existing_position is not None:
            # Weighted-average cost basis update
            new_qty = existing_qty + fill_result.quantity
            new_avg = (
                existing_qty * existing_avg + fill_result.quantity * fill_result.fill_price
            ) / new_qty
            existing_position.quantity = new_qty
            existing_position.avg_entry_price = new_avg
        else:
            new_pos = PaperPosition(
                account_id=account_id,
                symbol=symbol,
                interval=body.interval,
                quantity=fill_result.quantity,
                avg_entry_price=fill_result.fill_price,
                opened_at=datetime.now(timezone.utc),
            )
            session.add(new_pos)
    else:  # SELL
        if existing_position is not None:
            remaining = existing_qty - fill_result.quantity
            if remaining <= 0.0:
                await session.delete(existing_position)
            else:
                existing_position.quantity = remaining

    # Update account cash balance
    account.cash_balance = fill_result.new_cash

    # Immediately record an equity snapshot after every fill
    # (Build last_prices for snapshot — re-use price already fetched)
    pos_result2 = await session.execute(
        select(PaperPosition).where(PaperPosition.account_id == account_id)
    )
    all_positions = pos_result2.scalars().all()
    snapshot_prices: dict[str, float] = {}
    if all_positions:
        all_syms = list({p.symbol for p in all_positions})
        sp_result = await session.execute(
            select(MarketData)
            .where(MarketData.symbol.in_(all_syms))
            .order_by(MarketData.timestamp.desc())
        )
        sp_rows = sp_result.scalars().all()
        for row in sp_rows:
            if row.symbol not in snapshot_prices:
                snapshot_prices[row.symbol] = row.close

    positions_for_equity = [
        {"symbol": p.symbol, "quantity": p.quantity, "avg_entry_price": p.avg_entry_price}
        for p in all_positions
    ]
    total_equity = compute_equity(account.cash_balance, positions_for_equity, snapshot_prices)
    positions_value = total_equity - account.cash_balance

    snapshot = EquitySnapshot(
        account_id=account_id,
        recorded_at=datetime.now(timezone.utc),
        equity_value=total_equity,
        cash=account.cash_balance,
        positions_value=positions_value,
    )
    session.add(snapshot)

    await session.commit()

    log.info(
        "Order filled: account=%d %s %s x%.4f @ %.4f (commission=%.4f new_cash=%.2f)",
        account_id,
        body.side,
        symbol,
        fill_result.quantity,
        fill_result.fill_price,
        fill_result.commission_paid,
        fill_result.new_cash,
    )

    return {
        "fill_price": fill_result.fill_price,
        "quantity": fill_result.quantity,
        "commission_paid": fill_result.commission_paid,
        "new_cash": fill_result.new_cash,
        "realized_pnl": fill_result.realized_pnl,
        "account_id": account_id,
    }


# ---------------------------------------------------------------------------
# Endpoint 4: GET /paper/accounts/{account_id}/equity  (PAPER-03)
# ---------------------------------------------------------------------------


@router.get("/accounts/{account_id}/equity")
async def get_equity_curve(
    account_id: int,
    session: AsyncSession = Depends(get_session),  # type: ignore[assignment]
) -> dict:
    """
    Return a time-series equity curve for a paper trading account.

    Args:
        account_id: ID of the paper trading account.
        session: Injected async DB session.

    Returns:
        Dict with account_id and equity_curve: list of [iso_timestamp, equity_value] pairs.
        Returns an empty list if no snapshots have been recorded yet.
    """
    snap_result = await session.execute(
        select(EquitySnapshot)
        .where(EquitySnapshot.account_id == account_id)
        .order_by(EquitySnapshot.recorded_at.asc())
    )
    snapshots = snap_result.scalars().all()

    return {
        "account_id": account_id,
        "equity_curve": [
            [snap.recorded_at.isoformat(), snap.equity_value]
            for snap in snapshots
        ],
    }


# ---------------------------------------------------------------------------
# Endpoint 5: GET /paper/accounts/{account_id}/compare  (PAPER-04)
# ---------------------------------------------------------------------------


@router.get("/accounts/{account_id}/compare")
async def compare_paper_vs_backtest(
    account_id: int,
    session: AsyncSession = Depends(get_session),  # type: ignore[assignment]
) -> dict:
    """
    Compare paper trading equity curve against a linked backtest equity curve.

    Args:
        account_id: ID of the paper trading account.
        session: Injected async DB session.

    Returns:
        Dict with account_id, paper equity curve, backtest equity curve (or null),
        and backtest_run_id.

    Raises:
        HTTPException 404: If the account does not exist.
    """
    account = await session.get(PaperAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"Paper account {account_id} not found")

    # Paper equity curve
    snap_result = await session.execute(
        select(EquitySnapshot)
        .where(EquitySnapshot.account_id == account_id)
        .order_by(EquitySnapshot.recorded_at.asc())
    )
    snapshots = snap_result.scalars().all()
    paper_curve = [
        [snap.recorded_at.isoformat(), snap.equity_value]
        for snap in snapshots
    ]

    # Backtest curve — null when no backtest linked
    if account.backtest_run_id is None:
        return {
            "account_id": account_id,
            "paper": paper_curve,
            "backtest": None,
            "backtest_run_id": None,
        }

    backtest_run = await session.get(BacktestRun, account.backtest_run_id)
    backtest_curve = backtest_run.equity_curve_data() if backtest_run else []

    return {
        "account_id": account_id,
        "paper": paper_curve,
        "backtest": backtest_curve,
        "backtest_run_id": account.backtest_run_id,
    }
