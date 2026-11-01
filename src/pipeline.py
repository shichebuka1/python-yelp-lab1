import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from src.cleaning import run_cleaning_pipeline
from src.config import (
    CLEAN_DATA_PATH,
    LOGS_DIR,
    PROCESSED_DIR,
    RAW_FILES,
    REVIEW_SAMPLE_PATH,
)
from src.io_utils import create_sample_200k


def setup_logging() -> None:
    """Настраивает запись журнала одновременно в файл logs/cleaning.log и на экран терминала."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "cleaning.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    """Точка входа для запуска сквозной очистки одной командой из терминала."""
    parser = argparse.ArgumentParser(
        description="Сквозной конвейер очистки данных Yelp"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=REVIEW_SAMPLE_PATH,
        help="Путь к входному файлу отзывов",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=CLEAN_DATA_PATH,
        help="Путь для сохранения clean.parquet",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Работать на отладочном срезе 200 000 строк",
    )
    args = parser.parse_args()

    setup_logging()
    log = logging.getLogger("pipeline")

    # Если срез на 200 000 строк был удалён (например, при проверке воспроизводимости) — создаём его заново
    input_path = REVIEW_SAMPLE_PATH if args.sample else args.input
    if input_path == REVIEW_SAMPLE_PATH and not input_path.exists():
        log.info("Отладочный срез не найден. Создаём его заново из папки data/raw...")
        create_sample_200k()

    if not input_path.exists():
        log.error("Ошибка: входной файл не найден: %s", input_path)
        sys.exit(1)

    log.info(
        "Чтение входных файлов: %s и %s", input_path.name, RAW_FILES["business"].name
    )
    df_reviews = pd.read_json(input_path, lines=True)
    df_business = pd.read_json(RAW_FILES["business"], lines=True)

    # Запускаем общую процедуру очистки из модуля src/cleaning.py
    df_clean, _ = run_cleaning_pipeline(df_reviews, df_business)

    # Сохраняем итоговый очищенный файл в папку data/processed/clean.parquet
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df_clean.to_parquet(args.output, index=False)
    log.info(
        "Успешно! Очищенный набор (%d строк) сохранён в %s", len(df_clean), args.output
    )


if __name__ == "__main__":
    main()
