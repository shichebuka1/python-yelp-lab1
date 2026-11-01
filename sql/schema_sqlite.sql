DROP TABLE IF EXISTS records;
    DROP TABLE IF EXISTS categories;
    DROP TABLE IF EXISTS regions;

    -- Справочник категорий заведений
    CREATE TABLE categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT UNIQUE NOT NULL
    );

    -- Справочник регионов (город + штат)
    CREATE TABLE regions (
        region_id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        UNIQUE(city, state)
    );

    -- Основная таблица отзывов со ссылками (FOREIGN KEY) на справочники
    CREATE TABLE records (
        review_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        business_id TEXT NOT NULL,
        business_name TEXT NOT NULL,
        date TIMESTAMP NOT NULL,
        stars INTEGER NOT NULL,
        stars_100 REAL NOT NULL,
        useful INTEGER NOT NULL,
        funny INTEGER NOT NULL,
        cool INTEGER NOT NULL,
        text TEXT NOT NULL,
        is_open BOOLEAN NOT NULL,
        region_id INTEGER,
        category_id INTEGER,
        FOREIGN KEY (region_id) REFERENCES regions(region_id),
        FOREIGN KEY (category_id) REFERENCES categories(category_id)
    );