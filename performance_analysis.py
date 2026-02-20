# -*- coding: utf-8 -*-
"""
Анализ производительности запросов к БД на CSV.
Замеряет время выполнения представлений и запросов, формирует отчёт.
Запуск: python performance_analysis.py
"""

import time
from datetime import datetime
from pathlib import Path

from config import REPORTS_DIR
from csv_db import (
    v_products_full,
    v_deliveries_full,
    v_stock_by_category,
    query_products_by_category_name,
    query_products_price_above,
    query_suppliers_delivery_count,
    load_table,
    build_index_by_id,
    build_index_by_key,
)


def measure(name: str, func, *args, **kwargs):
    """Выполнить функцию и вернуть результат и время в секундах."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return result, elapsed


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    lines = []
    lines.append("=" * 60)
    lines.append("ОТЧЁТ ПО АНАЛИЗУ ПРОИЗВОДИТЕЛЬНОСТИ ЗАПРОСОВ")
    lines.append("БД: учёт товаров (CSV)")
    lines.append(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)

    queries = [
        ("Товары с категорией и поставщиком (VIEW v_products_full)", lambda: v_products_full(100)),
        ("Товары по категории «Электроника» (индекс по category_id)", lambda: query_products_by_category_name("Электроника")),
        ("Товары дороже 10000 (сортировка по цене)", lambda: query_products_price_above(10000)),
        ("Поставки за последние 30 дней (VIEW v_deliveries_full)", lambda: v_deliveries_full(days_back=30)),
        ("Остатки по категориям (VIEW v_stock_by_category)", v_stock_by_category),
        ("Поставщики с количеством поставок (агрегация)", query_suppliers_delivery_count),
    ]

    for name, func in queries:
        lines.append("")
        lines.append("-" * 60)
        lines.append(f"Запрос: {name}")
        lines.append("-" * 60)
        try:
            result, elapsed = measure(name, func)
            lines.append(f"Время: {elapsed:.4f} с")
            lines.append(f"Записей: {len(result)}")
            if result and len(result) <= 3:
                lines.append(f"Пример: {result[0]}")
            elif result:
                lines.append(f"Пример: {result[0]}")
        except Exception as e:
            lines.append(f"Ошибка: {e}")

    # Замер загрузки таблиц и построения индексов
    lines.append("")
    lines.append("-" * 60)
    lines.append("Загрузка таблиц и индексов")
    lines.append("-" * 60)
    for table in ("products", "categories", "suppliers", "deliveries"):
        rows, t_load = measure("load", load_table, table)
        _, t_idx = measure("index", build_index_by_id, rows)
        lines.append(f"  {table}: загрузка {t_load:.4f} с, индекс по id {t_idx:.4f} с, строк {len(rows)}")

    lines.append("")
    lines.append("=" * 60)
    lines.append("РЕКОМЕНДАЦИИ ПО ОПТИМИЗАЦИИ")
    lines.append("=" * 60)
    lines.append("""
1. Индексы: в csv_db используются индексы в памяти (build_index_by_id,
   build_index_by_key) для быстрого поиска по id, category_id, supplier_id.
   Запросы по категории/поставщику выполняются через индекс, без полного перебора.

2. Представления (VIEW): v_products_full и v_deliveries_full делают один проход
   по основной таблице и подстановку по индексам — аналог JOIN. При росте данных
   можно кэшировать загруженные таблицы в памяти на время сессии.

3. Резервное копирование: backup_db.py копирует папку data/ в backups/.
   Рекомендуется запускать по расписанию.

4. Для больших объёмов данных рассмотрите хранение в SQLite или PostgreSQL
   с индексами на диске.
""")
    report_text = "\n".join(lines)
    report_path.write_text(report_text, encoding="utf-8")
    print(f"Отчёт сохранён: {report_path}")
    print(report_text[:1800] + "\n... (см. файл полностью)")


if __name__ == "__main__":
    main()
