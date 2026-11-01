import time

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from src.config import CLEAN_DATA_PATH, PROCESSED_DIR, SQL_DIR

# Загружаем переменные окружения из файла .env
load_dotenv()

# Путь к файловой базе данных SQLite
SQLITE_DB_PATH = PROCESSED_DIR / "dataset.db"


def create_sql_schemas():
    """
    Шаги 14 и 15: Сохраняет SQL-скрипты создания таблиц в 3-й нормальной форме
    в папку sql/ (для SQLite и для PostgreSQL) и создаёт таблицы в базе SQLite.
    """
    SQL_DIR.mkdir(parents=True, exist_ok=True)

    # 1. SQL-схема для файловой СУБД SQLite (3 связанные таблицы в 3НФ)
    schema_sqlite = """
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
    """
    (SQL_DIR / "schema_sqlite.sql").write_text(schema_sqlite.strip(), encoding="utf-8")

    # 2. SQL-схема для серверной СУБД PostgreSQL
    schema_postgres = """
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
    """
    (SQL_DIR / "schema_postgres.sql").write_text(
        schema_postgres.strip(), encoding="utf-8"
    )

    # Подключаемся к файловой базе SQLite и создаём таблицы
    engine = create_engine(f"sqlite:///{SQLITE_DB_PATH}")
    with engine.begin() as conn:
        for sql_command in schema_sqlite.split(";"):
            if sql_command.strip():
                conn.execute(text(sql_command))

    print("✅ SQL-скрипты сохранены в папку sql/, таблицы в 3НФ успешно созданы!")
    return engine


def load_clean_data_to_db(engine) -> None:
    """
    Шаг 14: Читает очищенный файл clean.parquet и загружает данные в базу:
    сначала заполняет справочники categories и regions, затем основную таблицу records.
    """
    print("\nЧитаем очищенный набор данных из clean.parquet...")
    df = pd.read_parquet(CLEAN_DATA_PATH)

    t0 = time.perf_counter()
    with engine.begin() as conn:
        # 1. Заполняем справочник категорий (categories)
        unique_cats = pd.DataFrame(
            {"category_name": df["main_category"].dropna().unique()}
        )
        unique_cats.to_sql("categories", conn, if_exists="append", index=False)

        cat_table = pd.read_sql(
            "SELECT category_id, category_name FROM categories", conn
        )
        cat_map = dict(zip(cat_table["category_name"], cat_table["category_id"]))

        # 2. Заполняем справочник регионов (regions)
        unique_regions = df[["city", "state"]].drop_duplicates().dropna()
        unique_regions.to_sql("regions", conn, if_exists="append", index=False)

        reg_table = pd.read_sql("SELECT region_id, city, state FROM regions", conn)
        reg_map = {
            (row.city, row.state): row.region_id for row in reg_table.itertuples()
        }

        # 3. Заменяем текстовые города и категории в главной таблице на их числовые ID (3НФ)
        df_records = df.copy()
        df_records["category_id"] = df_records["main_category"].map(cat_map)
        city_state_pairs = list(zip(df_records["city"], df_records["state"]))
        df_records["region_id"] = [reg_map.get(pair) for pair in city_state_pairs]

        cols_for_records = [
            "review_id",
            "user_id",
            "business_id",
            "business_name",
            "date",
            "stars",
            "stars_100",
            "useful",
            "funny",
            "cool",
            "text",
            "is_open",
            "region_id",
            "category_id",
        ]
        df_records = df_records[cols_for_records]

        # Загружаем строки пакетами по 50 000 штук
        df_records.to_sql(
            "records", conn, if_exists="append", index=False, chunksize=50_000
        )

    elapsed = time.perf_counter() - t0
    db_size_mb = SQLITE_DB_PATH.stat().st_size / (1024 * 1024)
    print(
        f"✅ Загружено {len(df_records)} записей в БД за {elapsed:.2f} с (Объём БД: {db_size_mb:.2f} МБ)"
    )


def test_queries_and_indexes(engine) -> None:
    """
    Шаг 14: Выполняет 3 контрольных SQL-запроса ДО создания индексов и ПОСЛЕ создания индексов.
    """
    sql_count = "SELECT COUNT(*) FROM records;"
    sql_agg = """
        SELECT r.city, COUNT(*) AS reviews_cnt, ROUND(AVG(rec.stars_100), 1) AS avg_score
        FROM records rec
        JOIN regions r ON rec.region_id = r.region_id
        GROUP BY r.city
        ORDER BY reviews_cnt DESC
        LIMIT 5;
    """
    sql_date_filter = "SELECT COUNT(*) FROM records WHERE date >= '2018-01-01';"

    with engine.connect() as conn:
        # 1. Замеряем время выполнения БЕЗ индексов
        t0 = time.perf_counter()
        total_rows = conn.execute(text(sql_count)).scalar()
        t_count_before = time.perf_counter() - t0

        t0 = time.perf_counter()
        top_cities = conn.execute(text(sql_agg)).fetchall()
        t_agg_before = time.perf_counter() - t0

        t0 = time.perf_counter()
        conn.execute(text(sql_date_filter)).fetchall()
        t_date_before = time.perf_counter() - t0

        # 2. Создаём индексы на столбец даты и столбец региона
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_records_date ON records(date);")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_records_region ON records(region_id);")
        )
        conn.commit()

        # 3. Замеряем время выполнения ПОСЛЕ создания индексов
        t0 = time.perf_counter()
        conn.execute(text(sql_agg)).fetchall()
        t_agg_after = time.perf_counter() - t0

        t0 = time.perf_counter()
        conn.execute(text(sql_date_filter)).fetchall()
        t_date_after = time.perf_counter() - t0

    print("\n=== РЕЗУЛЬТАТЫ КОНТРОЛЬНЫХ ЗАПРОСОВ К БАЗЕ ДАННЫХ (Таблица 9) ===")
    print(
        f"1. Всего записей в таблице records: {total_rows} (время: {t_count_before:.4f} с)"
    )
    print(
        f"2. Запрос с JOIN и GROUP BY по городам: до индекса = {t_agg_before:.4f} с | после = {t_agg_after:.4f} с"
    )
    print("3. Выборка по диапазону дат (WHERE date >= '2018-01-01'):")
    print(f"   -> БЕЗ индекса:   {t_date_before:.4f} с")
    print(
        f"   -> ПОСЛЕ индекса: {t_date_after:.4f} с (Ускорение в {t_date_before / t_date_after:.1f} раза!)"
    )
    print("\nТоп-5 городов по числу отзывов из БД (результат SQL-запроса):")
    for city_name, cnt, avg_val in top_cities:
        print(
            f"   - {city_name}: {cnt} отзывов (средний рейтинг по 100-балльной шкале: {avg_val})"
        )


if __name__ == "__main__":
    db_engine = create_sql_schemas()
    load_clean_data_to_db(db_engine)
    test_queries_and_indexes(db_engine)
