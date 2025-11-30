import logging
import requests
import zipfile
import io
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.base import SessionLocal
from app.models.gdelt import GdeltSignal, SignalTheme, SignalEntity
from app.models.aggregates import Country
from app.core.config import settings

logger = logging.getLogger(__name__)

class GdeltIngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.base_url = settings.GDELT_BASE

    def fetch_latest_files(self) -> List[str]:
        """Fetch the list of latest GDELT GKG files."""
        try:
            response = requests.get(f"{self.base_url}/lastupdate.txt")
            response.raise_for_status()
            files = []
            for line in response.text.splitlines():
                parts = line.split(" ")
                if len(parts) >= 3 and "gkg.csv.zip" in parts[2]:
                    files.append(parts[2])
            return files
        except Exception as e:
            logger.error(f"Failed to fetch GDELT file list: {e}")
            return []

    def ensure_country_exists(self, country_code: str):
        """
        Check if country exists, if not create it.
        This prevents FK constraint errors when inserting signals.
        """
        if not country_code or len(country_code) != 2:
            return

        # Check cache or DB
        existing = self.db.query(Country).filter(Country.country_code == country_code).first()
        
        if not existing:
            logger.info(f"Auto-creating new country: {country_code}")
            new_country = Country(
                country_code=country_code,
                country_name=country_code, # Placeholder name
                latitude=0.0, # Placeholder lat
                longitude=0.0, # Placeholder lon
                region="Unknown",
                is_active=True
            )
            try:
                self.db.add(new_country)
                self.db.commit()
            except IntegrityError:
                self.db.rollback()
                pass
            except Exception as e:
                logger.error(f"Failed to auto-create country {country_code}: {e}")
                self.db.rollback()

    def process_file(self, file_url: str):
        """Download and process a single GDELT GKG file."""
        logger.info(f"Processing GDELT file: {file_url}")
        try:
            response = requests.get(file_url)
            response.raise_for_status()
            
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                for filename in z.namelist():
                    with z.open(filename) as f:
                        content = f.read().decode('utf-8', errors='replace')
                        self._parse_and_store(content)
                        
        except Exception as e:
            logger.error(f"Error processing file {file_url}: {e}")

    def _parse_and_store(self, content: str):
        """Parse CSV content and store in DB."""
        reader = csv.reader(io.StringIO(content), delimiter='\t')
        
        for row in reader:
            try:
                if len(row) < 15:
                    continue
                    
                record_id = row[0]
                timestamp_str = row[1]
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                except ValueError:
                    continue
                
                source_name = row[3]
                source_url = row[4]
                v2_themes = row[8]
                v2_locations = row[10]
                v2_persons = row[11]
                v2_orgs = row[12]
                v2_tone = row[15]
                
                # Parse Tone
                tone_parts = v2_tone.split(",")
                tone_overall = float(tone_parts[0]) if tone_parts else 0.0
                
                # Parse Locations
                country_code = "XX"
                locations_json = []
                if v2_locations:
                    locs = v2_locations.split(";")
                    for loc in locs:
                        parts = loc.split("#")
                        if len(parts) >= 6:
                            cc = parts[2]
                            if cc and len(cc) == 2:
                                country_code = cc
                                try:
                                    lat = float(parts[4]) if parts[4] else None
                                    lon = float(parts[5]) if parts[5] else None
                                except ValueError:
                                    lat = None
                                    lon = None

                                locations_json.append({
                                    "country_code": cc,
                                    "name": parts[1],
                                    "lat": lat,
                                    "lon": lon
                                })
                                break 
                
                if country_code == "XX":
                    continue 
                
                self.ensure_country_exists(country_code)
                
                primary_theme = "UNKNOWN"
                if v2_themes:
                    themes = v2_themes.split(";")
                    if themes:
                        primary_theme = themes[0].split(",")[0]
                
                signal = GdeltSignal(
                    gkg_record_id=record_id,
                    timestamp=timestamp,
                    bucket_15min=timestamp,
                    bucket_1h=timestamp,
                    country_code=country_code,
                    tone_overall=tone_overall,
                    primary_theme=primary_theme,
                    source_outlet=source_name,
                    source_url=source_url,
                    url_hash=str(hash(source_url)),
                    all_locations=locations_json,
                    latitude=locations_json[0]['lat'] if locations_json else None,
                    longitude=locations_json[0]['lon'] if locations_json else None
                )
                
                self.db.add(signal)
                try:
                    self.db.commit()
                    
                    # Store Themes
                    if v2_themes:
                        theme_list = v2_themes.split(";")
                        for t_str in theme_list:
                            if not t_str: continue
                            t_parts = t_str.split(",")
                            t_code = t_parts[0]
                            t_count = int(t_parts[1]) if len(t_parts) > 1 and t_parts[1].isdigit() else 1
                            
                            if t_code:
                                theme_obj = SignalTheme(
                                    signal_id=signal.id,
                                    theme_code=t_code,
                                    theme_label=t_code,
                                    theme_count=t_count
                                )
                                self.db.add(theme_obj)
                    
                    # Store Persons
                    if v2_persons:
                        persons = v2_persons.split(";")
                        for p in persons:
                            if not p: continue
                            # GDELT doesn't provide counts for persons in GKG 2.0 CSV directly in this field usually,
                            # but sometimes it's just a list. We'll assume count=1.
                            entity_obj = SignalEntity(
                                signal_id=signal.id,
                                entity_type="PERSON",
                                entity_name=p,
                                count=1
                            )
                            self.db.add(entity_obj)

                    # Store Organizations
                    if v2_orgs:
                        orgs = v2_orgs.split(";")
                        for o in orgs:
                            if not o: continue
                            entity_obj = SignalEntity(
                                signal_id=signal.id,
                                entity_type="ORG",
                                entity_name=o,
                                count=1
                            )
                            self.db.add(entity_obj)

                    self.db.commit()

                except IntegrityError:
                    self.db.rollback()
                except Exception as e:
                    self.db.rollback()
                    logger.error(f"Error saving signal {record_id}: {e}")

            except Exception as e:
                logger.warning(f"Failed to parse row: {e}")
                continue
        
        logger.info("Finished processing GDELT file.")

def run_ingestion():
    db = SessionLocal()
    try:
        service = GdeltIngestionService(db)
        files = service.fetch_latest_files()
        if files:
            service.process_file(files[0])
    finally:
        db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_ingestion()
