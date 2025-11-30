import logging
from datetime import datetime, timedelta
from sqlalchemy import delete, func, select
from app.db.base import SessionLocal
from app.models.gdelt import GdeltSignal
from app.models.aggregates import ThemeAggregation1h, CountryAggregate

logger = logging.getLogger(__name__)

class RetentionService:
    def __init__(self, db=None):
        self.db = db or SessionLocal()

    def cleanup_raw_signals(self, days=7, dry_run=False):
        """Delete raw signals older than N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        logger.info(f"Cleaning up signals older than {cutoff_date}")
        
        try:
            # Count first
            count_stmt = select(func.count(GdeltSignal.id)).where(GdeltSignal.timestamp < cutoff_date)
            count = self.db.execute(count_stmt).scalar()
            
            if count == 0:
                logger.info("No signals to clean up.")
                return 0

            if dry_run:
                logger.info(f"[DRY RUN] Would delete {count} signals.")
                return count

            # Delete
            delete_stmt = delete(GdeltSignal).where(GdeltSignal.timestamp < cutoff_date)
            self.db.execute(delete_stmt)
            self.db.commit()
            logger.info(f"Deleted {count} signals.")
            return count
        except Exception as e:
            logger.error(f"Error cleaning up signals: {e}")
            self.db.rollback()
            return 0

    def aggregate_daily(self, target_date=None):
        """Roll up hourly aggregates to daily country aggregates."""
        if target_date is None:
            target_date = datetime.utcnow().date() - timedelta(days=1)
        
        start_time = datetime.combine(target_date, datetime.min.time())
        end_time = datetime.combine(target_date, datetime.max.time())
        
        logger.info(f"Aggregating daily stats for {target_date}")
        
        try:
            # Aggregate from ThemeAggregation1h
            stmt = select(
                ThemeAggregation1h.country_code,
                func.sum(ThemeAggregation1h.signal_count).label('total_events'),
                func.sum(ThemeAggregation1h.total_theme_mentions).label('total_mentions'),
                func.avg(ThemeAggregation1h.avg_tone).label('avg_tone')
            ).where(
                ThemeAggregation1h.hour_bucket >= start_time,
                ThemeAggregation1h.hour_bucket <= end_time
            ).group_by(
                ThemeAggregation1h.country_code
            )
            
            results = self.db.execute(stmt).all()
            
            count = 0
            for row in results:
                # Check if exists
                existing = self.db.query(CountryAggregate).filter(
                    CountryAggregate.country_code == row.country_code,
                    CountryAggregate.window_type == 'daily',
                    CountryAggregate.window_start == start_time
                ).first()
                
                if existing:
                    existing.total_events = row.total_events
                    existing.total_mentions = row.total_mentions
                    existing.avg_tone = row.avg_tone
                else:
                    agg = CountryAggregate(
                        country_code=row.country_code,
                        window_start=start_time,
                        window_end=end_time,
                        window_type='daily',
                        total_events=row.total_events,
                        total_mentions=row.total_mentions,
                        avg_tone=row.avg_tone
                    )
                    self.db.add(agg)
                count += 1
            
            self.db.commit()
            logger.info(f"Created/Updated {count} daily country aggregates.")
            return count
        except Exception as e:
            logger.error(f"Error aggregating daily stats: {e}")
            self.db.rollback()
            return 0

    def cleanup_hourly_aggregates(self, days=90, dry_run=False):
        """Delete hourly aggregates older than N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        logger.info(f"Cleaning up hourly aggregates older than {cutoff_date}")
        
        try:
            count_stmt = select(func.count(ThemeAggregation1h.id)).where(ThemeAggregation1h.hour_bucket < cutoff_date)
            count = self.db.execute(count_stmt).scalar()
            
            if count == 0:
                logger.info("No hourly aggregates to clean up.")
                return 0

            if dry_run:
                logger.info(f"[DRY RUN] Would delete {count} hourly aggregates.")
                return count

            delete_stmt = delete(ThemeAggregation1h).where(ThemeAggregation1h.hour_bucket < cutoff_date)
            self.db.execute(delete_stmt)
            self.db.commit()
            logger.info(f"Deleted {count} hourly aggregates.")
            return count
        except Exception as e:
            logger.error(f"Error cleaning up hourly aggregates: {e}")
            self.db.rollback()
            return 0

    def close(self):
        self.db.close()

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Run data retention jobs")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    args = parser.parse_args()
    
    service = RetentionService()
    try:
        if not args.dry_run:
            service.aggregate_daily()
        service.cleanup_raw_signals(days=7, dry_run=args.dry_run)
        service.cleanup_hourly_aggregates(days=90, dry_run=args.dry_run)
    finally:
        service.close()
