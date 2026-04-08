"""
Pydantic request and response models for the paper trading API.

Used by Wave 2 route handlers to validate incoming requests and
serialize outgoing responses. No SQLAlchemy dependencies — Pydantic only.
"""
from pydantic import BaseModel, Field

__all__ = ["CreateAccountRequest", "PlaceOrderRequest", "AccountSummaryResponse"]


class CreateAccountRequest(BaseModel):
    """Request body for POST /api/paper/accounts."""

    name: str = Field(..., min_length=1, max_length=100)
    starting_balance: float = Field(default=10_000.0, gt=0)
    slippage_std: float = Field(default=0.001, ge=0.0, le=0.05)
    commission: float = Field(default=0.001, ge=0.0, le=0.1)
    backtest_run_id: int | None = Field(default=None)


class PlaceOrderRequest(BaseModel):
    """Request body for POST /api/paper/accounts/{id}/orders."""

    symbol: str
    interval: str = Field(default="1D")
    side: str = Field(..., pattern="^(BUY|SELL)$")
    quantity: float = Field(..., gt=0)


class AccountSummaryResponse(BaseModel):
    """Response body for GET /api/paper/accounts/{id}."""

    id: int
    name: str
    cash_balance: float
    starting_balance: float
    total_equity: float
    open_positions: list[dict]
    slippage_std: float
    commission: float
    backtest_run_id: int | None
