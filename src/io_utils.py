import json

from src.config import INTERIM_DIR, RAW_FILES, REVIEW_SAMPLE_PATH, SAMPLE_SIZE


def inspect_raw_dataset() -> None:
    """
    Определяет размер каждого исходного файла в мегабайтах
    и читает первые 100 строк, чтобы узнать названия столбцов без перегрузки памяти.
    """
    print("=== ПЕРВИЧНЫЙ ОСМОТР ИСХОДНЫХ ФАЙЛОВ (ПАПКА data/raw) ===")

    # Перебираем все 5 файлов из нашего словаря RAW_FILES
    for table_name, file_path in RAW_FILES.items():
        # Проверяем, лежит ли файл в папке data/raw
        if not file_path.exists():
            print(f"Файл не найден: {file_path.name}")
            continue

        # Вычисляем размер файла в мегабайтах (1 МБ = 1024 * 1024 байт)
        size_bytes = file_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)

        # Открываем файл в режиме чтения текста (кодировка UTF-8)
        column_names = []
        with open(file_path, mode="r", encoding="utf-8") as file:
            # Читаем только первые 100 строк
            for line_index in range(100):
                line = file.readline()
                if not line:
                    break
                # Превращаем одну JSON-строку в обычный словарь Python
                row_dict = json.loads(line)
                # На первой строке запоминаем названия всех ключей (столбцов таблицы)
                if line_index == 0:
                    column_names = list(row_dict.keys())

        # Выводим понятную сводку на экран
        print(f"\nТаблица: {table_name} ({file_path.name})")
        print(f" -> Размер файла: {size_mb:.2f} МБ | Кодировка: UTF-8")
        print(f" -> Количество столбцов: {len(column_names)}")
        print(f" -> Названия столбцов: {', '.join(column_names)}")


def create_sample_200k() -> None:
    """
    Шаг 6: Построчно копирует первые 200 000 строк из 5-гигабайтного файла отзывов
    в новый компактный файл data/interim/review_sample_200k.jsonl.
    """
    # Убеждаемся, что папка data/interim существует
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)

    source_file = RAW_FILES["review"]
    print(f"\nСоздаём отладочный срез на {SAMPLE_SIZE} строк из {source_file.name}...")

    # Открываем исходный файл для чтения (src), а новый файл в interim — для записи (dst)
    lines_written = 0
    with (
        open(source_file, mode="r", encoding="utf-8") as src,
        open(REVIEW_SAMPLE_PATH, mode="w", encoding="utf-8") as dst,
    ):
        for line in src:
            # Как только записали 200 000 строк — останавливаем цикл
            if lines_written >= SAMPLE_SIZE:
                break
            dst.write(line)
            lines_written += 1

    # Проверяем размер получившегося среза в мегабайтах
    sample_mb = REVIEW_SAMPLE_PATH.stat().st_size / (1024 * 1024)
    print(f"Готово! Записано строк: {lines_written}")
    print(f"Файл сохранён: {REVIEW_SAMPLE_PATH} (Размер: {sample_mb:.2f} МБ)")


# Этот блок запускается, когда мы вызываем файл напрямую из терминала
if __name__ == "__main__":
    inspect_raw_dataset()
    create_sample_200k()
