from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base

class GdeltSignal(Base):
    __tablename__ = "gdelt_signals"

    id = Column(Integer, primary_key=True, index=True)
    gkg_record_id = Column(String, unique=True, index=True)
    timestamp = Column(DateTime, index=True)
    bucket_15min = Column(DateTime, index=True)
    bucket_1h = Column(DateTime, index=True)
    country_code = Column(String, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    tone_overall = Column(Float)
    primary_theme = Column(String, nullable=True)
    source_outlet = Column(String, nullable=True)
    source_url = Column(Text, nullable=True)
    url_hash = Column(String, index=True)
    all_locations = Column(JSONB, nullable=True)

    themes = relationship("SignalTheme", back_populates="signal", cascade="all, delete-orphan")
    entities = relationship("SignalEntity", back_populates="signal", cascade="all, delete-orphan")

class SignalTheme(Base):
    __tablename__ = "signal_themes"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("gdelt_signals.id"))
    theme_code = Column(String, index=True)
    theme_label = Column(String, nullable=True)
    theme_count = Column(Integer, default=1)

    signal = relationship("GdeltSignal", back_populates="themes")

class SignalEntity(Base):
    __tablename__ = "signal_entities"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("gdelt_signals.id"))
    entity_type = Column(String, index=True) # PERSON, ORG, LOC
    entity_name = Column(String, index=True)
    count = Column(Integer, default=1)

    signal = relationship("GdeltSignal", back_populates="entities")
