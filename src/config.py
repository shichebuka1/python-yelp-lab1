from pathlib import Path

# Определяем путь к корневой папке нашего проекта (D:\Yelp_Lab1)
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
