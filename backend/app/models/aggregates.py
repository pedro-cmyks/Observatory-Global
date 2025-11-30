from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base

class Country(Base):
    __tablename__ = "countries"

    country_code = Column(String, primary_key=True, index=True)
    country_name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    region = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

class ThemeAggregation1h(Base):
    __tablename__ = "theme_aggregations_1h"

    id = Column(Integer, primary_key=True, index=True)
    hour_bucket = Column(DateTime, index=True)
    country_code = Column(String, index=True)
    theme_code = Column(String, index=True)
    theme_label = Column(String, nullable=True)
    signal_count = Column(Integer, default=0)
    avg_tone = Column(Float, nullable=True)
    total_theme_mentions = Column(Integer, default=0)
