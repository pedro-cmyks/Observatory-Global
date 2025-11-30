import logging
from app.db.base import SessionLocal
from app.models.aggregates import Country

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COUNTRIES = [
    {"code": "US", "name": "United States", "lat": 37.0902, "lon": -95.7129, "region": "Americas"},
    {"code": "CN", "name": "China", "lat": 35.8617, "lon": 104.1954, "region": "Asia"},
    {"code": "RU", "name": "Russia", "lat": 61.5240, "lon": 105.3188, "region": "Europe"},
    {"code": "UA", "name": "Ukraine", "lat": 48.3794, "lon": 31.1656, "region": "Europe"},
    {"code": "GB", "name": "United Kingdom", "lat": 55.3781, "lon": -3.4360, "region": "Europe"},
    {"code": "FR", "name": "France", "lat": 46.2276, "lon": 2.2137, "region": "Europe"},
    {"code": "DE", "name": "Germany", "lat": 51.1657, "lon": 10.4515, "region": "Europe"},
    {"code": "IT", "name": "Italy", "lat": 41.8719, "lon": 12.5674, "region": "Europe"},
    {"code": "IL", "name": "Israel", "lat": 31.0461, "lon": 34.8516, "region": "Asia"},
    {"code": "PS", "name": "Palestine", "lat": 31.9522, "lon": 35.2332, "region": "Asia"},
    {"code": "IR", "name": "Iran", "lat": 32.4279, "lon": 53.6880, "region": "Asia"},
    {"code": "TR", "name": "Turkey", "lat": 38.9637, "lon": 35.2433, "region": "Asia"},
    {"code": "IN", "name": "India", "lat": 20.5937, "lon": 78.9629, "region": "Asia"},
    {"code": "JP", "name": "Japan", "lat": 36.2048, "lon": 138.2529, "region": "Asia"},
    {"code": "KR", "name": "South Korea", "lat": 35.9078, "lon": 127.7669, "region": "Asia"},
    {"code": "KP", "name": "North Korea", "lat": 40.3399, "lon": 127.5101, "region": "Asia"},
    {"code": "BR", "name": "Brazil", "lat": -14.2350, "lon": -51.9253, "region": "Americas"},
    {"code": "MX", "name": "Mexico", "lat": 23.6345, "lon": -102.5528, "region": "Americas"},
    {"code": "CA", "name": "Canada", "lat": 56.1304, "lon": -106.3468, "region": "Americas"},
    {"code": "AU", "name": "Australia", "lat": -25.2744, "lon": 133.7751, "region": "Oceania"},
    {"code": "ZA", "name": "South Africa", "lat": -30.5595, "lon": 22.9375, "region": "Africa"},
    {"code": "NG", "name": "Nigeria", "lat": 9.0820, "lon": 8.6753, "region": "Africa"},
    {"code": "EG", "name": "Egypt", "lat": 26.8206, "lon": 30.8025, "region": "Africa"},
    {"code": "SA", "name": "Saudi Arabia", "lat": 23.8859, "lon": 45.0792, "region": "Asia"},
    {"code": "AE", "name": "United Arab Emirates", "lat": 23.4241, "lon": 53.8478, "region": "Asia"},
    {"code": "QA", "name": "Qatar", "lat": 25.3548, "lon": 51.1839, "region": "Asia"},
    {"code": "SY", "name": "Syria", "lat": 34.8021, "lon": 38.9968, "region": "Asia"},
    {"code": "IQ", "name": "Iraq", "lat": 33.2232, "lon": 43.6793, "region": "Asia"},
    {"code": "AF", "name": "Afghanistan", "lat": 33.9391, "lon": 67.7100, "region": "Asia"},
    {"code": "PK", "name": "Pakistan", "lat": 30.3753, "lon": 69.3451, "region": "Asia"},
    {"code": "ID", "name": "Indonesia", "lat": -0.7893, "lon": 113.9213, "region": "Asia"},
    {"code": "MY", "name": "Malaysia", "lat": 4.2105, "lon": 101.9758, "region": "Asia"},
    {"code": "VN", "name": "Vietnam", "lat": 14.0583, "lon": 108.2772, "region": "Asia"},
    {"code": "TH", "name": "Thailand", "lat": 15.8700, "lon": 100.9925, "region": "Asia"},
    {"code": "PH", "name": "Philippines", "lat": 12.8797, "lon": 121.7740, "region": "Asia"},
    {"code": "PL", "name": "Poland", "lat": 51.9194, "lon": 19.1451, "region": "Europe"},
    {"code": "ES", "name": "Spain", "lat": 40.4637, "lon": -3.7492, "region": "Europe"},
    {"code": "NL", "name": "Netherlands", "lat": 52.1326, "lon": 5.2913, "region": "Europe"},
    {"code": "SE", "name": "Sweden", "lat": 60.1282, "lon": 18.6435, "region": "Europe"},
    {"code": "NO", "name": "Norway", "lat": 60.4720, "lon": 8.4689, "region": "Europe"},
    {"code": "FI", "name": "Finland", "lat": 61.9241, "lon": 25.7482, "region": "Europe"},
    {"code": "DK", "name": "Denmark", "lat": 56.2639, "lon": 9.5018, "region": "Europe"},
    {"code": "BE", "name": "Belgium", "lat": 50.5039, "lon": 4.4699, "region": "Europe"},
    {"code": "CH", "name": "Switzerland", "lat": 46.8182, "lon": 8.2275, "region": "Europe"},
    {"code": "AT", "name": "Austria", "lat": 47.5162, "lon": 14.5501, "region": "Europe"},
    {"code": "GR", "name": "Greece", "lat": 39.0742, "lon": 21.8243, "region": "Europe"},
    {"code": "HU", "name": "Hungary", "lat": 47.1625, "lon": 19.5033, "region": "Europe"},
    {"code": "CZ", "name": "Czech Republic", "lat": 49.8175, "lon": 15.4730, "region": "Europe"},
    {"code": "RO", "name": "Romania", "lat": 45.9432, "lon": 24.9668, "region": "Europe"},
    {"code": "VE", "name": "Venezuela", "lat": 6.4238, "lon": -66.5897, "region": "Americas"},
    {"code": "CO", "name": "Colombia", "lat": 4.5709, "lon": -74.2973, "region": "Americas"},
    {"code": "AR", "name": "Argentina", "lat": -38.4161, "lon": -63.6167, "region": "Americas"},
    {"code": "CL", "name": "Chile", "lat": -35.6751, "lon": -71.5430, "region": "Americas"},
    {"code": "PE", "name": "Peru", "lat": -9.1900, "lon": -75.0152, "region": "Americas"},
    {"code": "NZ", "name": "New Zealand", "lat": -40.9006, "lon": 174.8860, "region": "Oceania"},
]

def seed_countries():
    db = SessionLocal()
    try:
        count = 0
        for c_data in COUNTRIES:
            existing = db.query(Country).filter(Country.country_code == c_data["code"]).first()
            if not existing:
                country = Country(
                    country_code=c_data["code"],
                    country_name=c_data["name"],
                    latitude=c_data["lat"],
                    longitude=c_data["lon"],
                    region=c_data["region"],
                    is_active=True
                )
                db.add(country)
                count += 1
            else:
                # Update lat/lon just in case
                existing.latitude = c_data["lat"]
                existing.longitude = c_data["lon"]
                
        db.commit()
        logger.info(f"Seeded {count} new countries. Total processed: {len(COUNTRIES)}")
    except Exception as e:
        logger.error(f"Error seeding countries: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_countries()
