"""
Ticker-Genius Price Models
==========================
Wave 2: 주가 및 거래 신호 스키마.

Models:
- PricePoint: 단일 주가 데이터 포인트
- PriceHistory: 주가 이력
- PDUFAPriceWindow: PDUFA 이벤트 전후 주가 윈도우
- TradingSignal: 거래 신호
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Optional
from pydantic import Field, field_validator

from tickergenius.schemas.base import BaseSchema
from tickergenius.schemas.enums import TimingSignal, StrategyType


class PricePoint(BaseSchema):
    """단일 주가 데이터 포인트."""
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float] = None

    @property
    def change_pct(self) -> float:
        """일간 변동률."""
        if self.open > 0:
            return (self.close - self.open) / self.open
        return 0.0


class PriceHistory(BaseSchema):
    """주가 이력."""
    ticker: str
    prices: list[PricePoint] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = ""  # yfinance, alpha_vantage, etc.

    @property
    def latest_price(self) -> Optional[float]:
        """최신 종가."""
        if self.prices:
            return self.prices[-1].close
        return None

    @property
    def latest_date(self) -> Optional[date]:
        """최신 날짜."""
        if self.prices:
            return self.prices[-1].date
        return None

    def get_price_on_date(self, target_date: date) -> Optional[PricePoint]:
        """특정 날짜의 주가."""
        for p in self.prices:
            if p.date == target_date:
                return p
        return None

    def get_return(self, start_date: date, end_date: date) -> Optional[float]:
        """기간 수익률."""
        start_price = self.get_price_on_date(start_date)
        end_price = self.get_price_on_date(end_date)
        if start_price and end_price and start_price.close > 0:
            return (end_price.close - start_price.close) / start_price.close
        return None


class PDUFAPriceWindow(BaseSchema):
    """
    PDUFA 이벤트 전후 주가 윈도우.

    - pre_window: PDUFA 전 D-30 ~ D-1 (run-up 측정)
    - post_window: PDUFA 후 D+0 ~ D+5 (결과 반응 측정)
    """
    ticker: str
    pdufa_date: date
    event_id: Optional[str] = None

    # 기준 가격
    baseline_price: Optional[float] = None  # D-30 종가
    pre_pdufa_price: Optional[float] = None  # D-1 종가
    post_pdufa_price: Optional[float] = None  # D+1 종가

    # Run-up 분석
    run_up_pct: Optional[float] = None  # D-30 → D-1 변동률
    run_up_days: int = 0  # Run-up 기간

    # 결과 반응
    decision_day_return: Optional[float] = None  # D+0 수익률
    post_decision_return: Optional[float] = None  # D+1 ~ D+5 수익률

    # 거래량 분석
    avg_volume_pre: Optional[int] = None  # 평균 거래량 (pre)
    volume_on_decision: Optional[int] = None  # 결정일 거래량

    # 윈도우 데이터
    pre_window: list[PricePoint] = Field(default_factory=list)
    post_window: list[PricePoint] = Field(default_factory=list)

    def calculate_metrics(self):
        """윈도우 데이터에서 메트릭 계산."""
        if self.pre_window:
            self.baseline_price = self.pre_window[0].close
            self.pre_pdufa_price = self.pre_window[-1].close
            if self.baseline_price > 0:
                self.run_up_pct = (self.pre_pdufa_price - self.baseline_price) / self.baseline_price
            self.run_up_days = len(self.pre_window)
            volumes = [p.volume for p in self.pre_window]
            self.avg_volume_pre = sum(volumes) // len(volumes) if volumes else 0

        if self.post_window:
            self.post_pdufa_price = self.post_window[0].close if self.post_window else None
            if len(self.post_window) > 0:
                self.volume_on_decision = self.post_window[0].volume
                if self.pre_pdufa_price and self.pre_pdufa_price > 0:
                    self.decision_day_return = (
                        self.post_window[0].close - self.pre_pdufa_price
                    ) / self.pre_pdufa_price
            if len(self.post_window) > 1 and self.post_window[0].close > 0:
                self.post_decision_return = (
                    self.post_window[-1].close - self.post_window[0].close
                ) / self.post_window[0].close


class TradingSignal(BaseSchema):
    """
    PDUFA 거래 신호.

    분석 결과에 기반한 거래 추천.
    """
    ticker: str
    drug_name: str
    pdufa_date: date
    event_id: Optional[str] = None

    # 신호
    signal: TimingSignal = TimingSignal.HOLD
    strategy: StrategyType = StrategyType.AVOID
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)

    # 확률 기반 분석
    approval_probability: float = Field(ge=0.0, le=1.0, default=0.5)
    probability_tier: str = ""  # HIGH, MEDIUM, LOW

    # 가격 기반 분석
    current_price: Optional[float] = None
    run_up_pct: Optional[float] = None
    is_overextended: bool = False  # Run-up > 50%

    # 리스크 분석
    risk_score: float = Field(ge=0.0, le=1.0, default=0.5)
    risk_factors: list[str] = Field(default_factory=list)

    # 추천
    rationale: list[str] = Field(default_factory=list)
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None

    # 메타
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    days_to_pdufa: Optional[int] = None

    def get_risk_reward_ratio(self) -> Optional[float]:
        """리스크/보상 비율."""
        if self.entry_price and self.stop_loss and self.target_price:
            risk = self.entry_price - self.stop_loss
            reward = self.target_price - self.entry_price
            if risk > 0:
                return reward / risk
        return None


__all__ = [
    "PricePoint",
    "PriceHistory",
    "PDUFAPriceWindow",
    "TradingSignal",
]
