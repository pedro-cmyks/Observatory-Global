"""
Signals Repository

This module handles the persistence of GDELT signals to PostgreSQL.
It is the data access layer for the SignalsService.

Phase 4 Implementation Plan:
1. Initialize connection pool (psycopg2 or asyncpg)
2. Implement save_signals() using COPY or batch INSERT
3. Implement get_signals() with time window filtering
4. Implement aggregation queries for trends
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import psycopg2.extras
from app.models.gdelt_schemas import GDELTSignal

logger = logging.getLogger(__name__)

class SignalsRepository:
    """
    Repository for GDELT Signal persistence.
    
    Intended usage:
    - SignalsService calls save_signals() after fetching/generating data
    - SignalsService calls get_signals() to retrieve historical data
    """
    
    def __init__(self):
        from app.db.session import db_manager
        self.db = db_manager

    async def save_signals(self, signals: List[GDELTSignal]) -> int:
        """
        Persist a batch of signals to the database.
        
        Args:
            signals: List of GDELTSignal objects
            
        Returns:
            Count of successfully saved signals
        """
        if not signals:
            return 0

        count = 0
        try:
            # Use run_in_executor for blocking DB calls if running in async context
            # For now, assuming direct execution or thread pool handling by caller
            # But since this is an async method, we should ideally wrap it.
            # However, db_manager uses threaded pool, so it's thread-safe.
            # We'll execute synchronously here for simplicity, but in production
            # this should be offloaded to a thread if high volume.
            
            with self.db.get_cursor() as cur:
                for signal in signals:
                    # 1. Insert Signal
                    cur.execute("""
                        INSERT INTO gdelt_signals (
                            gkg_record_id, timestamp, bucket_15min, source_collection_id,
                            country_code, primary_location_lat, primary_location_lon,
                            primary_theme, sentiment_score, intensity,
                            url_hash, source_url, source_outlet
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s
                        ) ON CONFLICT (gkg_record_id) DO NOTHING
                        RETURNING id
                    """, (
                        signal.signal_id,
                        signal.timestamp,
                        signal.bucket_15min,
                        signal.source_collection_id,
                        signal.primary_location.country_code,
                        signal.primary_location.latitude,
                        signal.primary_location.longitude,
                        signal.primary_theme,
                        signal.tone.overall,
                        signal.intensity,
                        signal.url_hash,
                        signal.source_url,
                        signal.source_outlet
                    ))
                    
                    row = cur.fetchone()
                    if row:
                        signal_db_id = row['id']
                        count += 1
                        
                        # 2. Insert Themes (Batching would be better, but keeping it simple for now)
                        if signal.themes:
                            theme_values = [(signal_db_id, theme) for theme in signal.themes]
                            # Use execute_values for bulk insert if possible, or loop
                            # Standard psycopg2 execute_batch is good
                            psycopg2.extras.execute_batch(cur, """
                                INSERT INTO signal_themes (signal_id, theme)
                                VALUES (%s, %s)
                                ON CONFLICT DO NOTHING
                            """, theme_values)

                        # 3. Insert Persons
                        if signal.persons:
                            person_values = [(signal_db_id, 'person', p) for p in signal.persons]
                            psycopg2.extras.execute_batch(cur, """
                                INSERT INTO signal_entities (signal_id, entity_type, entity_value)
                                VALUES (%s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, person_values)

                        # 4. Insert Organizations
                        if signal.organizations:
                            org_values = [(signal_db_id, 'organization', o) for o in signal.organizations]
                            psycopg2.extras.execute_batch(cur, """
                                INSERT INTO signal_entities (signal_id, entity_type, entity_value)
                                VALUES (%s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, org_values)

            logger.info(f"SignalsRepository: Saved {count} new signals")
            return count

        except Exception as e:
            logger.error(f"SignalsRepository: Error saving signals: {e}")
            return 0

    async def get_signals(
        self, 
        countries: List[str], 
        start_time: datetime, 
        end_time: datetime
    ) -> Dict[str, List[GDELTSignal]]:
        """
        Retrieve signals for specified countries and time range.
        
        Args:
            countries: List of country codes
            start_time: Start of time window
            end_time: End of time window
            
        Returns:
            Dictionary mapping country code to list of signals
        """
        result = {c: [] for c in countries}
        
        try:
            with self.db.get_cursor() as cur:
                # Fetch signals with basic fields
                # Note: Reconstructing full GDELTSignal from DB is complex because of nested objects
                # For now, we'll fetch the core fields needed for visualization
                
                query = """
                    SELECT 
                        s.*,
                        array_agg(DISTINCT t.theme) as themes,
                        array_agg(DISTINCT e_per.entity_value) FILTER (WHERE e_per.entity_value IS NOT NULL) as persons,
                        array_agg(DISTINCT e_org.entity_value) FILTER (WHERE e_org.entity_value IS NOT NULL) as organizations
                    FROM gdelt_signals s
                    LEFT JOIN signal_themes t ON s.id = t.signal_id
                    LEFT JOIN signal_entities e_per ON s.id = e_per.signal_id AND e_per.entity_type = 'person'
                    LEFT JOIN signal_entities e_org ON s.id = e_org.signal_id AND e_org.entity_type = 'organization'
                    WHERE s.country_code = ANY(%s)
                    AND s.timestamp BETWEEN %s AND %s
                    GROUP BY s.id
                    ORDER BY s.timestamp DESC
                """
                
                cur.execute(query, (countries, start_time, end_time))
                rows = cur.fetchall()
                
                for row in rows:
                    # Reconstruct GDELTSignal object
                    # This is a simplified reconstruction - some fields might be default/missing if not stored
                    
                    # Reconstruct Location
                    location = {
                        "country_code": row['country_code'],
                        "country_name": "Unknown", # Would need lookup
                        "latitude": row['primary_location_lat'],
                        "longitude": row['primary_location_lon'],
                        "location_type": 1, # Default
                        "mention_count": 1
                    }
                    
                    # Reconstruct Tone
                    tone = {
                        "overall": row['sentiment_score'],
                        "positive_pct": 0, # Not stored individually
                        "negative_pct": 0,
                        "polarity": 0,
                        "activity_density": 0,
                        "self_reference": 0
                    }
                    
                    # Reconstruct Signal
                    signal = GDELTSignal(
                        signal_id=row['gkg_record_id'],
                        timestamp=row['timestamp'],
                        bucket_15min=row['bucket_15min'],
                        source_collection_id=row['source_collection_id'],
                        locations=[location],
                        primary_location=location,
                        themes=row['themes'] or [],
                        theme_labels=row['themes'] or [], # Placeholder
                        theme_counts={t: 1 for t in (row['themes'] or [])}, # Placeholder counts
                        primary_theme=row['primary_theme'],
                        tone=tone,
                        intensity=row['intensity'],
                        sentiment_label="neutral", # Auto-computed
                        geographic_precision="country", # Auto-computed
                        persons=row['persons'],
                        organizations=row['organizations'],
                        source_url=row['source_url'],
                        source_outlet=row['source_outlet'],
                        sources={"gdelt": True},
                        confidence=1.0,
                        url_hash=row['url_hash']
                    )
                    
                    if row['country_code'] in result:
                        result[row['country_code']].append(signal)
                        
            return result

        except Exception as e:
            logger.error(f"SignalsRepository: Error fetching signals: {e}")
            return result

    async def get_latest_timestamp(self) -> Optional[datetime]:
        """Get the timestamp of the most recent signal in the DB."""
        try:
            with self.db.get_cursor() as cur:
                cur.execute("SELECT MAX(timestamp) as max_ts FROM gdelt_signals")
                row = cur.fetchone()
                return row['max_ts'] if row else None
        except Exception as e:
            logger.error(f"SignalsRepository: Error getting latest timestamp: {e}")
            return None
