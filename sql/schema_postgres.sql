DROP TABLE IF EXISTS records CASCADE;
    DROP TABLE IF EXISTS categories CASCADE;
    DROP TABLE IF EXISTS regions CASCADE;

    CREATE TABLE categories (
        category_id SERIAL PRIMARY KEY,
        category_name VARCHAR(128) UNIQUE NOT NULL
    );

    CREATE TABLE regions (
        region_id SERIAL PRIMARY KEY,
        city VARCHAR(64) NOT NULL,
        state VARCHAR(8) NOT NULL,
        UNIQUE(city, state)
    );

    CREATE TABLE records (
        review_id VARCHAR(64) PRIMARY KEY,
        user_id VARCHAR(64) NOT NULL,
        business_id VARCHAR(64) NOT NULL,
        business_name VARCHAR(255) NOT NULL,
        date TIMESTAMP NOT NULL,
        stars SMALLINT NOT NULL,
        stars_100 NUMERIC(5, 2) NOT NULL,
        useful SMALLINT NOT NULL,
        funny SMALLINT NOT NULL,
        cool SMALLINT NOT NULL,
        text TEXT NOT NULL,
        is_open BOOLEAN NOT NULL,
        region_id INTEGER REFERENCES regions(region_id),
        category_id INTEGER REFERENCES categories(category_id)
    );

    CREATE INDEX idx_records_date ON records(date);
    CREATE INDEX idx_records_region ON records(region_id);