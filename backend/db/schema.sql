CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS cities (
    metro_fips    TEXT         PRIMARY KEY,
    name          TEXT         NOT NULL,
    lat           NUMERIC(9,6),
    lon           NUMERIC(9,6),
    median_income INTEGER,
    income_year   SMALLINT,
    rpp           NUMERIC(6,2),
    rpp_year      SMALLINT,
    walk_score    SMALLINT,
    transit_score SMALLINT,
    bike_score    SMALLINT,
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cities_name          ON cities (name);
CREATE INDEX IF NOT EXISTS idx_cities_median_income ON cities (median_income DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_cities_rpp           ON cities (rpp);
CREATE INDEX IF NOT EXISTS idx_cities_walk_score    ON cities (walk_score DESC NULLS LAST);

CREATE TABLE IF NOT EXISTS trends (
    id                BIGSERIAL   PRIMARY KEY,
    metro_fips        TEXT        NOT NULL REFERENCES cities(metro_fips) ON DELETE CASCADE,
    date              TEXT        NOT NULL,
    median_rent       INTEGER,
    median_home_value INTEGER,
    rent_to_income    NUMERIC(5,1),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT trends_metro_date_unique UNIQUE (metro_fips, date)
);

CREATE INDEX IF NOT EXISTS idx_trends_metro_fips ON trends (metro_fips);
CREATE INDEX IF NOT EXISTS idx_trends_date       ON trends (date DESC);
CREATE INDEX IF NOT EXISTS idx_trends_metro_date ON trends (metro_fips, date DESC);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id               BIGSERIAL   PRIMARY KEY,
    source           TEXT        NOT NULL,
    success          BOOLEAN     NOT NULL,
    started_at       TIMESTAMPTZ NOT NULL,
    finished_at      TIMESTAMPTZ NOT NULL,
    duration_seconds NUMERIC(8,2) GENERATED ALWAYS AS (EXTRACT(EPOCH FROM (finished_at - started_at))) STORED,
    cities_upserted  INTEGER     NOT NULL DEFAULT 0,
    trends_upserted  INTEGER     NOT NULL DEFAULT 0,
    errors           TEXT[]      NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON pipeline_runs (started_at DESC);

CREATE TABLE IF NOT EXISTS listings_cache (
    id           BIGSERIAL   PRIMARY KEY,
    metro_fips   TEXT        NOT NULL,
    listing_type TEXT        NOT NULL,
    status       TEXT        NOT NULL,
    listings     JSONB       NOT NULL,
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT listings_cache_unique UNIQUE (metro_fips, listing_type, status)
);

CREATE INDEX IF NOT EXISTS idx_listings_cache_fips ON listings_cache (metro_fips);

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trg_cities_updated_at') THEN
        CREATE TRIGGER trg_cities_updated_at BEFORE UPDATE ON cities FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trg_trends_updated_at') THEN
        CREATE TRIGGER trg_trends_updated_at BEFORE UPDATE ON trends FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    END IF;
END; $$;
