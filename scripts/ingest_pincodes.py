import os
import sys
import csv
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

REQUIRED_COLUMNS = [
    "pincode", "office_name", "district", "state", "tier", "serviceable", "lat", "lon"
]

CSV_PATH = os.environ.get("PINCODE_CSV", "data/raw/all_india_pincode.csv")
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/postgres"
)

def validate_row(row):
    for col in REQUIRED_COLUMNS:
        if col not in row or not row[col]:
            return False
    try:
        float(row["lat"])
        float(row["lon"])
    except Exception:
        return False
    return True

def main():
    logging.basicConfig(level=logging.INFO)
    if not os.path.exists(CSV_PATH):
        logging.error(f"CSV file not found: {CSV_PATH}")
        sys.exit(1)
    engine = create_engine(DB_URL)
    inserted, updated, skipped = 0, 0, 0
    with engine.begin() as conn:
        with open(CSV_PATH, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if not validate_row(row):
                    skipped += 1
                    continue
                try:
                    # UPSERT logic
                    stmt = text('''
                        INSERT INTO pincodes (pincode, office_name, district, state, tier, serviceable, lat, lon, location)
                        VALUES (:pincode, :office_name, :district, :state, :tier, :serviceable, :lat, :lon, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography)
                        ON CONFLICT (pincode) DO UPDATE SET
                            office_name=EXCLUDED.office_name,
                            district=EXCLUDED.district,
                            state=EXCLUDED.state,
                            tier=EXCLUDED.tier,
                            serviceable=EXCLUDED.serviceable,
                            lat=EXCLUDED.lat,
                            lon=EXCLUDED.lon,
                            location=EXCLUDED.location
                    ''')
                    conn.execute(stmt, {
                        "pincode": row["pincode"],
                        "office_name": row["office_name"],
                        "district": row["district"],
                        "state": row["state"],
                        "tier": row["tier"],
                        "serviceable": row["serviceable"].lower() in ("true", "1", "yes"),
                        "lat": float(row["lat"]),
                        "lon": float(row["lon"]),
                    })
                    inserted += 1
                except SQLAlchemyError as e:
                    logging.error(f"DB error for pincode {row['pincode']}: {e}")
                    skipped += 1
    logging.info(f"Inserted/Updated: {inserted}, Skipped: {skipped}")

if __name__ == "__main__":
    main()
