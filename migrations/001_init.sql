CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS pincodes (
    id SERIAL PRIMARY KEY,
    pincode VARCHAR(6) UNIQUE NOT NULL,
    office_name TEXT NOT NULL,
    district TEXT NOT NULL,
    state TEXT NOT NULL,
    tier VARCHAR(10) NOT NULL DEFAULT 'Rural',
    serviceable BOOLEAN NOT NULL DEFAULT TRUE,
    location GEOGRAPHY(Point, 4326) NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pincode_location ON pincodes USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_pincode_trgm ON pincodes USING GIN (pincode gin_trgm_ops);

-- Health check query for DB readiness
-- Usage: SELECT 1 FROM pincodes LIMIT 1;
