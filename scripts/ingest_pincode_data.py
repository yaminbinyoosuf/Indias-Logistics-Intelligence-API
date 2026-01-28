
import pandas as pd
import psycopg2
from geopy.geocoders import Nominatim
import logging
import os

CSV_PATH = "data/raw/all_india_pincode.csv"
PROCESSED_PATH = "data/processed/pincode_enriched.csv"
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/postgres")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def clean_and_enrich():
    df = pd.read_csv(CSV_PATH)
    # Validate columns
    required_cols = {'Pincode', 'OfficeName', 'District', 'StateName'}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Missing columns: {required_cols - set(df.columns)}")
    # Filter valid pincodes
    df = df[df['Pincode'].astype(str).str.match(r'^\d{6}$')]
    before = len(df)
    df = df.drop_duplicates(subset=['Pincode'])
    after = len(df)
    logging.info(f"Dropped {before - after} duplicate pincodes.")
    # Backfill missing lat/lon
    geolocator = Nominatim(user_agent="india-logistics-api")
    missing = 0
    for idx, row in df.iterrows():
        if pd.isnull(row.get('Latitude')) or pd.isnull(row.get('Longitude')):
            location = geolocator.geocode(f"{row['Pincode']}, India")
            if location:
                df.at[idx, 'Latitude'] = location.latitude
                df.at[idx, 'Longitude'] = location.longitude
                missing += 1
    logging.info(f"Backfilled {missing} missing lat/lon values.")
    # Fill missing tier as 'Rural'
    if 'Tier' not in df.columns:
        df['Tier'] = 'Rural'
    df['Tier'] = df['Tier'].fillna('Rural')
    df.to_csv(PROCESSED_PATH, index=False)
    logging.info(f"Saved cleaned data to {PROCESSED_PATH}.")

def load_to_postgres():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    df = pd.read_csv(PROCESSED_PATH)
    inserted, updated, skipped = 0, 0, 0
    for _, row in df.iterrows():
        # Try update first for idempotency
        cur.execute("""
            UPDATE pincodes SET office_name=%s, district=%s, state=%s, tier=%s, serviceable=%s, lat=%s, lon=%s, location=ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            WHERE pincode=%s
        """, (
            row.get('OfficeName', ''), row.get('District', ''), row.get('StateName', ''),
            row.get('Tier', 'Rural'), True, row['Latitude'], row['Longitude'],
            row['Longitude'], row['Latitude'], row['Pincode']
        ))
        if cur.rowcount == 0:
            try:
                cur.execute("""
                    INSERT INTO pincodes (pincode, office_name, district, state, tier, serviceable, lat, lon, location)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                """, (
                    row['Pincode'], row.get('OfficeName', ''), row.get('District', ''), row.get('StateName', ''),
                    row.get('Tier', 'Rural'), True, row['Latitude'], row['Longitude'],
                    row['Longitude'], row['Latitude']
                ))
                inserted += 1
            except Exception as e:
                logging.warning(f"Skipped {row['Pincode']}: {e}")
                skipped += 1
        else:
            updated += 1
    conn.commit()
    cur.close()
    conn.close()
    logging.info(f"Inserted: {inserted}, Updated: {updated}, Skipped: {skipped}")

if __name__ == "__main__":
    clean_and_enrich()
    load_to_postgres()
