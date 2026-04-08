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

CREATE TABLE IF NOT EXISTS seller_credits (
    id SERIAL PRIMARY KEY,
    api_key VARCHAR(128) UNIQUE NOT NULL,
    credits_remaining FLOAT NOT NULL DEFAULT 100,
    credits_total FLOAT NOT NULL DEFAULT 100,
    plan VARCHAR(50) NOT NULL DEFAULT 'free',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS usage_logs (
    id SERIAL PRIMARY KEY,
    api_key VARCHAR(128) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    credits_consumed FLOAT NOT NULL DEFAULT 1.0,
    response_status INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_logs_api_key ON usage_logs (api_key);
CREATE INDEX IF NOT EXISTS idx_usage_logs_timestamp ON usage_logs (timestamp);

-- Health check query for DB readiness
-- Usage: SELECT 1 FROM pincodes LIMIT 1;
