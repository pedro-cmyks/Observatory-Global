import logging
from datetime import datetime, timedelta
from sqlalchemy import func, select, text
from app.db.base import SessionLocal
from app.models.gdelt import GdeltSignal, SignalTheme
from app.models.aggregates import ThemeAggregation1h

logger = logging.getLogger(__name__)

def run_aggregation():
    db = SessionLocal()
    try:
        # Aggregate last 7 days (168 hours)
        window_start = datetime.utcnow() - timedelta(hours=168)
        
        logger.info(f"Running aggregation from {window_start}")
        
        # Clear existing aggregations for this window (to allow re-aggregation)
        # In production, might want to be more selective, but for now this ensures consistency
        db.execute(
            text("DELETE FROM theme_aggregations_1h WHERE hour_bucket >= :start"),
            {"start": window_start}
        )
        db.commit()
        
        # Aggregate
        stmt = select(
            func.date_trunc('hour', GdeltSignal.timestamp).label('hour_bucket'),
            GdeltSignal.country_code,
            func.coalesce(SignalTheme.theme_code, 'GENERAL').label('theme_code'),
            func.count(GdeltSignal.id).label('signal_count'),
            func.avg(GdeltSignal.tone_overall).label('avg_tone'),
            func.sum(func.coalesce(SignalTheme.theme_count, 0)).label('total_theme_mentions')
        ).outerjoin(
            SignalTheme, GdeltSignal.id == SignalTheme.signal_id
        ).where(
            GdeltSignal.timestamp >= window_start
        ).group_by(
            func.date_trunc('hour', GdeltSignal.timestamp),
            GdeltSignal.country_code,
            func.coalesce(SignalTheme.theme_code, 'GENERAL')
        )
        
        results = db.execute(stmt).all()
        
        count = 0
        for row in results:
            agg = ThemeAggregation1h(
                hour_bucket=row.hour_bucket,
                country_code=row.country_code,
                theme_code=row.theme_code,
                signal_count=row.signal_count,
                avg_tone=row.avg_tone,
                total_theme_mentions=row.total_theme_mentions
            )
            db.add(agg)
            count += 1
            
        db.commit()
        logger.info(f"Aggregation complete. Created {count} records.")
        
    except Exception as e:
        logger.error(f"Aggregation failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_aggregation()
