from pathlib import Path

# Определяем путь к корневой папке нашего проекта (D:\Labs\Yelp_Lab1)
BASE_DIR = Path(__file__).resolve().parent.parent

# Прописываем пути к трём папкам с данными согласно методичке:
# raw — только для чтения исходников; interim — промежуточные файлы; processed — чистовик
RAW_DIR = BASE_DIR / "data" / "raw"
INTERIM_DIR = BASE_DIR / "data" / "interim"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# Пути к папкам с логами и SQL-скриптами
LOGS_DIR = BASE_DIR / "logs"
SQL_DIR = BASE_DIR / "sql"

# Словарь с путями к 5 исходным файлам датасета Yelp
RAW_FILES = {
    "business": RAW_DIR / "yelp_academic_dataset_business.json",
    "review": RAW_DIR / "yelp_academic_dataset_review.json",
    "user": RAW_DIR / "yelp_academic_dataset_user.json",
    "checkin": RAW_DIR / "yelp_academic_dataset_checkin.json",
    "tip": RAW_DIR / "yelp_academic_dataset_tip.json",
}

# Размер отладочного среза по методичке (200 000 строк) и путь для его сохранения
SAMPLE_SIZE = 200_000
REVIEW_SAMPLE_PATH = INTERIM_DIR / "review_sample_200k.jsonl"

# Путь к финальному очищенному файлу, который мы получим на Шаге 12
CLEAN_DATA_PATH = PROCESSED_DIR / "clean.parquet"

# Оптимальная схема типов данных для экономии памяти (Шаг 10 и Шаг 12)
OPTIMAL_SCHEMA = {
    "review_id": "string",
    "user_id": "string",
    "business_id": "string",
    "stars": "int8",
    "useful": "int16",
    "funny": "int16",
    "cool": "int16",
    "text": "string",
    "business_name": "string",
    "city": "category",
    "state": "category",
    "postal_code": "string",
    "latitude": "float32",
    "longitude": "float32",
    "business_stars": "float32",
    "review_count": "int32",
    "is_open": "boolean",
    "main_category": "category",
}
