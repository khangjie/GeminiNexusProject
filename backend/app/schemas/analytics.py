from typing import Any, Optional
from pydantic import BaseModel


class AnalyticsQuery(BaseModel):
    question: str


class ChartDataPoint(BaseModel):
    label: str
    value: float


class AnalyticsResponse(BaseModel):
    answer: str
    chart_type: Optional[str] = None  # "bar" | "line" | "pie" | None
    chart_data: Optional[list[ChartDataPoint]] = None
    chart_title: Optional[str] = None
