"""
Pure functions for paper trade simulation. No DB access, no FastAPI imports.

fill_order() simulates executing a BUY or SELL order against a last known
price, applying a Gaussian slippage model and a flat commission rate.

compute_equity() calculates total portfolio equity (cash + mark-to-market
positions) given a snapshot of last known prices.

Both functions are fully testable in isolation — no SQLAlchemy, no FastAPI.
"""
import random
from dataclasses import dataclass

__all__ = ["FillResult", "fill_order", "compute_equity"]


@dataclass
class FillResult:
    """
    Result of a single simulated order fill.

    Attributes:
        fill_price:      Actual execution price after slippage applied.
        quantity:        Number of units filled (same as requested).
        commission_paid: Total commission paid in dollars.
        new_cash:        Account cash balance after the fill.
        realized_pnl:    Realized profit/loss from this fill.
                         Always 0.0 for BUY; positive when SELL above avg_entry.
    """

    fill_price: float
    quantity: float
    commission_paid: float
    new_cash: float
    realized_pnl: float


def fill_order(
    side: str,
    symbol: str,
    quantity: float,
    last_price: float,
    cash_balance: float,
    position_qty: float,
    avg_entry_price: float,
    slippage_std: float = 0.001,
    commission: float = 0.001,
) -> FillResult:
    """
    Simulate filling a paper trade order at a price derived from last_price.

    Slippage model:
        offset = random.gauss(0, slippage_std) clipped to [-3*std, +3*std]
        BUY:  fill_price = last_price * (1 + abs(offset))   — fills above mid
        SELL: fill_price = last_price * (1 - abs(offset))   — fills below mid
        When slippage_std == 0.0: fill_price == last_price exactly.

    Commission:
        BUY:  total_debit  = fill_price * quantity * (1 + commission)
        SELL: gross_credit = fill_price * quantity * (1 - commission)

    Args:
        side:            "BUY" or "SELL"
        symbol:          Ticker symbol (used for error messages only).
        quantity:        Number of units to fill (must be > 0).
        last_price:      Most recent market price for the symbol.
        cash_balance:    Current account cash available.
        position_qty:    Units currently held (used to validate SELL qty).
        avg_entry_price: Weighted average cost basis of held units.
        slippage_std:    Gaussian standard deviation of the slippage offset.
                         0.0 disables slippage entirely.
        commission:      Per-fill commission as a fraction of trade value.

    Returns:
        FillResult dataclass with execution details and updated cash.

    Raises:
        ValueError: If BUY cost exceeds cash_balance.
        ValueError: If SELL quantity exceeds position_qty.
    """
    # --- Compute slippage offset ---
    if slippage_std == 0.0:
        offset = 0.0
    else:
        raw = random.gauss(0.0, slippage_std)
        # Clip to 3-sigma to avoid extreme outliers
        clip = 3.0 * slippage_std
        raw = max(-clip, min(clip, raw))
        offset = abs(raw)  # direction applied below

    if side == "BUY":
        fill_price = last_price * (1.0 + offset)
        total_debit = fill_price * quantity * (1.0 + commission)
        if total_debit > cash_balance:
            raise ValueError(
                f"Insufficient cash to BUY {quantity} {symbol}: "
                f"cost {total_debit:.2f} > balance {cash_balance:.2f}"
            )
        commission_paid = fill_price * quantity * commission
        new_cash = cash_balance - total_debit
        realized_pnl = 0.0

    elif side == "SELL":
        fill_price = last_price * (1.0 - offset)
        if quantity > position_qty:
            raise ValueError(
                f"Insufficient position to SELL {quantity} {symbol}: "
                f"held {position_qty}"
            )
        gross_credit = fill_price * quantity * (1.0 - commission)
        commission_paid = fill_price * quantity * commission
        realized_pnl = (fill_price - avg_entry_price) * quantity - (fill_price * quantity * commission)
        new_cash = cash_balance + gross_credit

    else:
        raise ValueError(f"Unknown order side: {side!r}. Expected 'BUY' or 'SELL'.")

    return FillResult(
        fill_price=fill_price,
        quantity=quantity,
        commission_paid=commission_paid,
        new_cash=new_cash,
        realized_pnl=realized_pnl,
    )


def compute_equity(
    cash: float,
    positions: list[dict],
    last_prices: dict[str, float],
) -> float:
    """
    Calculate total portfolio equity at a point in time.

    Marks each open position to market using last_prices. If a symbol is
    absent from last_prices (e.g. no fresh tick available), falls back to
    avg_entry_price so equity is never understated as zero.

    Args:
        cash:        Current cash balance in the account.
        positions:   List of position dicts with keys:
                       "symbol" (str), "quantity" (float), "avg_entry_price" (float)
        last_prices: Map of symbol → most recent market price.

    Returns:
        Total equity = cash + sum(quantity * mark_price) for all positions.
    """
    positions_value = sum(
        pos["quantity"] * last_prices.get(pos["symbol"], pos["avg_entry_price"])
        for pos in positions
    )
    return cash + positions_value
