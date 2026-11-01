import html
import logging

import pandas as pd

from src.config import OPTIMAL_SCHEMA

# Подключаем стандартный регистратор событий (логгер) для записи хода очистки
log = logging.getLogger(__name__)


def merge_sources(df_reviews: pd.DataFrame, df_business: pd.DataFrame) -> pd.DataFrame:
    """
    Этап 1: Соединение таблицы отзывов со справочником заведений по ключу business_id.
    Проверяем число строк до и после, чтобы не допустить размножения записей.
    """
    rows_before = len(df_reviews)

    # Выбираем нужные столбцы из таблицы заведений и переименовываем конфликтующие имена
    cols_to_take = [
        "business_id",
        "name",
        "city",
        "state",
        "postal_code",
        "latitude",
        "longitude",
        "stars",
        "review_count",
        "is_open",
        "categories",
    ]
    biz_clean = df_business[cols_to_take].rename(
        columns={"name": "business_name", "stars": "business_stars"}
    )

    # На всякий случай убираем дубликаты ключа в справочнике перед соединением
    biz_clean = biz_clean.drop_duplicates(subset=["business_id"])

    # Выполняем левое соединение (LEFT JOIN) таблиц по идентификатору заведения
    merged_df = df_reviews.merge(biz_clean, on="business_id", how="left")

    # Считаем, сколько отзывов не нашли своё заведение в справочнике
    unmatched_count = merged_df["business_name"].isna().sum()

    log.info(
        "Этап 1 (Соединение таблиц): было %d строк, стало %d строк, не сопоставилось: %d",
        rows_before,
        len(merged_df),
        unmatched_count,
    )
    return merged_df


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Этап 2: Приведение названий всех столбцов к нижнему регистру и формату snake_case.
    """
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)
    log.info(
        "Этап 2 (Имена столбцов): приведено к единому виду %d столбцов", len(df.columns)
    )
    return df


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Этап 3: Выявление скрытых пропусков (пустых строк '', прочерков '-')
    и обработка отсутствующих значений.
    """
    df = df.copy()
    rows_before = len(df)

    # Список текстовых заменителей пустоты, которые нужно превратить в настоящий пропуск <NA>
    hidden_nulls = ["", "-", "none", "null", "n/a", "нет данных"]
    text_cols = ["text", "business_name", "city", "state", "postal_code", "categories"]

    for col in text_cols:
        if col in df.columns:
            # Находим ячейки, где после удаления пробелов стоит пустая строка или прочерк
            is_hidden_null = (
                df[col].astype(str).str.strip().str.lower().isin(hidden_nulls)
            )
            df.loc[is_hidden_null, col] = pd.NA

    # Удаляем единичные строки, где отсутствует категория заведения или сам текст отзыва
    df = df.dropna(
        subset=[
            "review_id",
            "user_id",
            "business_id",
            "text",
            "business_name",
            "categories",
        ]
    )

    # В столбце categories написано несколько рубрик через запятую ("Restaurants, Pizza").
    # Чтобы соблюсти 1-ю нормальную форму (атомарность ячейки), берём первую (главную) рубрику:
    df["main_category"] = (
        df["categories"].astype("string").str.split(",").str[0].str.strip()
    )

    # Если у заведения не указан почтовый индекс, ставим понятную заглушку 'UNKNOWN'
    df["postal_code"] = df["postal_code"].fillna("UNKNOWN")

    # Удаляем старый неатомарный столбец categories
    df = df.drop(columns=["categories"]).reset_index(drop=True)

    log.info(
        "Этап 3 (Пропуски): было %d строк, стало %d строк (удалено %d строк без категории)",
        rows_before,
        len(df),
        rows_before - len(df),
    )
    return df


def cast_types_and_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Этап 4: Преобразование столбца date к типу даты и назначение оптимальных типов из config.py.
    """
    df = df.copy()
    rows_before = len(df)

    # Переводим столбец date в формат datetime (если дата битая — превратится в NaT)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    # Применяем наш словарь оптимальных типов OPTIMAL_SCHEMA
    for col_name, target_type in OPTIMAL_SCHEMA.items():
        if col_name in df.columns:
            df[col_name] = df[col_name].astype(target_type)

    log.info(
        "Этап 4 (Типы и даты): было %d строк, стало %d строк", rows_before, len(df)
    )
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Этап 5: Удаление полных дубликатов и дубликатов по ключу review_id
    (с сохранением самой свежей записи по дате).
    """
    rows_before = len(df)

    # Сначала убираем 100% совпадающие строки
    df = df.drop_duplicates()

    # Сортируем по дате и оставляем последнюю запись для каждого review_id
    df = df.sort_values(["date", "review_id"]).drop_duplicates(
        subset=["review_id"], keep="last"
    )
    df = df.sort_values("review_id").reset_index(drop=True)

    log.info(
        "Этап 5 (Дубликаты): было %d строк, стало %d строк (удалено %d дублей)",
        rows_before,
        len(df),
        rows_before - len(df),
    )
    return df


def normalize_categories(df: pd.DataFrame) -> pd.DataFrame:
    """
    Этап 6: Очистка категориальных столбцов (city, state, main_category)
    от лишних пробелов, разного регистра и редких значений.
    """
    df = df.copy()

    # 1. Приводим города к формату 'С Заглавной Буквы' без краевых пробелов
    clean_city = df["city"].astype("string").str.strip().str.title()

    # Исправляем частые сокращения названий городов по словарю соответствий
    city_synonyms = {
        "St. Louis": "Saint Louis",
        "St Louis": "Saint Louis",
        "St. Petersburg": "Saint Petersburg",
        "St Petersburg": "Saint Petersburg",
        "Phila": "Philadelphia",
    }
    clean_city = clean_city.replace(city_synonyms)

    # Объединяем редкие города (встречающиеся реже 20 раз) в группу 'Other'
    city_counts = clean_city.value_counts()
    rare_cities = city_counts[city_counts < 20].index
    clean_city = clean_city.where(~clean_city.isin(rare_cities), "Other")
    df["city"] = clean_city.astype("category")

    # 2. Код штата переводим в верхний регистр (например, 'CA', 'PA')
    df["state"] = (
        df["state"].astype("string").str.strip().str.upper().astype("category")
    )

    # 3. Объединяем редкие рубрики заведений (реже 50 раз) в группу 'Other'
    clean_cat = df["main_category"].astype("string").str.strip()
    cat_counts = clean_cat.value_counts()
    rare_cats = cat_counts[cat_counts < 50].index
    df["main_category"] = clean_cat.where(~clean_cat.isin(rare_cats), "Other").astype(
        "category"
    )

    log.info(
        "Этап 6 (Нормализация категорий): уникальных городов=%d, категорий=%d",
        df["city"].nunique(),
        df["main_category"].nunique(),
    )
    return df


def clean_text_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Этап 7: Очистка текста отзыва (text) от HTML-символов, переносов строк
    и удаление пустых/слишком коротких неинформативных отзывов (< 15 символов).
    """
    df = df.copy()
    rows_before = len(df)

    text_series = df["text"].astype("string")
    # Превращаем HTML-коды вроде &amp; в обычные символы &
    text_series = text_series.map(lambda x: html.unescape(x) if pd.notna(x) else x)
    # Удаляем HTML-теги (если встречаются) и заменяем переносы строк и двойные пробелы на один пробел
    text_series = text_series.str.replace(r"<[^>]+>", " ", regex=True)
    text_series = text_series.str.replace(r"\s+", " ", regex=True).str.strip()
    df["text"] = text_series.astype("string")

    # Отбрасываем слишком короткие отзывы (короче 15 символов)
    df = df[df["text"].str.len() >= 15].reset_index(drop=True)

    log.info(
        "Этап 7 (Очистка текста): было %d строк, стало %d строк (удалено %d коротких строк)",
        rows_before,
        len(df),
        rows_before - len(df),
    )
    return df


def check_domain_rules(df: pd.DataFrame) -> pd.DataFrame:
    """
    Этап 8: Проверка бизнес-ограничений (неотрицательные голоса, оценки от 1 до 5,
    корректные координаты, дата не в будущем) и перевод оценки в 100-балльную шкалу.
    """
    df = df.copy()
    rows_before = len(df)

    # Если в счётчиках голосов встретились отрицательные числа (технический сбой) — заменяем их на 0
    for vote_col in ["useful", "funny", "cool"]:
        df[vote_col] = df[vote_col].clip(lower=0).astype("int16")

    # Проверяем, что оценки, координаты и даты находятся в разумных границах
    current_time = pd.Timestamp.now()
    valid_rows = (
        df["stars"].between(1, 5)
        & df["business_stars"].between(1.0, 5.0)
        & df["latitude"].between(-90.0, 90.0)
        & df["longitude"].between(-180.0, 180.0)
        & (df["date"] <= current_time)
    )
    df = df[valid_rows].reset_index(drop=True)

    # Добавляем столбец рейтинга по единой 100-балльной шкале (1 звезда = 20 баллов)
    df["stars_100"] = (df["stars"].astype("float32") * 20.0).astype("float32")

    log.info(
        "Этап 8 (Предметные правила): было %d строк, стало %d строк",
        rows_before,
        len(df),
    )
    return df


def handle_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Этап 9: Поиск выбросов в столбце useful двумя методами:
    1) Межквартильный размах (IQR)
    2) Правило трёх сигм (среднее + 3 стандартных отклонения)
    Спорные записи не удаляем, а помечаем флагом is_useful_outlier и ограничиваем сверху.
    """
    df = df.copy()
    useful_vals = df["useful"].astype("float64")

    # Способ 1: Межквартильный размах (IQR)
    q1 = useful_vals.quantile(0.25)
    q3 = useful_vals.quantile(0.75)
    iqr_limit = q3 + 1.5 * (q3 - q1)
    iqr_count = (useful_vals > iqr_limit).sum()

    # Способ 2: Правило трёх сигм
    sigma_limit = useful_vals.mean() + 3.0 * useful_vals.std()
    sigma_count = (useful_vals > sigma_limit).sum()

    # На скошенном распределении голосов правило IQR отсекает слишком много обычных отзывов (> 2.5 голосов).
    # Поэтому помечаем флагом выбросы по правилу 3 сигм, а сами значения мягко ограничиваем 99.9% квантилем:
    cap_value = int(useful_vals.quantile(0.999))
    df["is_useful_outlier"] = (df["useful"] > sigma_limit).astype("boolean")
    df["useful"] = df["useful"].clip(upper=cap_value).astype("int16")

    log.info(
        "Этап 9 (Выбросы useful): по IQR=%d (>%.1f), по 3-сигма=%d (>%.1f), порог усечения=%d",
        iqr_count,
        iqr_limit,
        sigma_count,
        sigma_limit,
        cap_value,
    )
    return df


def run_cleaning_pipeline(
    df_reviews: pd.DataFrame, df_business: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Главная функция: по очереди запускает все 9 шагов очистки
    и возвращает очищенную таблицу вместе со сводкой «Было — Стало».
    """
    steps = [
        ("1. Соединение таблиц (JOIN)", lambda d: merge_sources(d, df_business)),
        ("2. Нормализация имён столбцов", normalize_column_names),
        ("3. Обработка пропусков", handle_missing_values),
        ("4. Приведение типов и дат", cast_types_and_dates),
        ("5. Удаление дубликатов", remove_duplicates),
        ("6. Нормализация категорий и городов", normalize_categories),
        ("7. Очистка текста отзыва", clean_text_column),
        ("8. Проверка предметных ограничений", check_domain_rules),
        ("9. Обработка выбросов (IQR vs 3-sigma)", handle_outliers),
    ]

    current_df = df_reviews
    start_total = len(df_reviews)
    summary_rows = []

    for step_title, step_func in steps:
        before_cnt = len(current_df)
        current_df = step_func(current_df)
        after_cnt = len(current_df)
        removed_cnt = before_cnt - after_cnt

        summary_rows.append(
            {
                "Этап очистки": step_title,
                "Строк до": before_cnt,
                "Строк после": after_cnt,
                "Удалено строк": removed_cnt,
                "Доля потерь, %": round((removed_cnt / start_total) * 100, 3),
            }
        )

    summary_table = pd.DataFrame(summary_rows)
    return current_df, summary_table
