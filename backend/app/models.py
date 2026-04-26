from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class CityListItem(BaseModel):
    metro_fips:    str
    name:          str
    lat:           Optional[float] = None
    lon:           Optional[float] = None
    median_income: Optional[int]   = None
    income_year:   Optional[int]   = None
    rpp:           Optional[float] = None
    rpp_year:      Optional[int]   = None
    walk_score:    Optional[int]   = None
    transit_score: Optional[int]   = None
    bike_score:    Optional[int]   = None
    updated_at:    Optional[datetime] = None
    class Config:
        from_attributes = True

class TrendPoint(BaseModel):
    date:              str
    median_rent:       Optional[int]   = None
    median_home_value: Optional[int]   = None
    rent_to_income:    Optional[float] = None
    class Config:
        from_attributes = True

class CityDetail(CityListItem):
    trends: list[TrendPoint] = []

class TrendSummary(BaseModel):
    latest_date:            Optional[str]   = None
    current_rent:           Optional[int]   = None
    current_home_value:     Optional[int]   = None
    current_rent_to_income: Optional[float] = None
    yoy_rent_change_pct:    Optional[float] = None
    yoy_home_change_pct:    Optional[float] = None

class TrendResponse(BaseModel):
    metro_fips:      str
    name:            str
    months_returned: int
    series:          list[TrendPoint]
    summary:         Optional[TrendSummary] = None

class CompareResponse(BaseModel):
    cities:   list[CityListItem]
    rankings: dict[str, Optional[str]]
    count:    int
