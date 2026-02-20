# -*- coding: utf-8 -*-
"""
Главный файл для запуска приложения «БД учета товаров».
Запуск: python main.py
"""

import sys


def menu():
    print()
    print("  БД учета товаров (CSV)")
    print("  -----------------------")
    print("  1 — Инициализация БД (создать CSV с тестовыми данными)")
    print("  2 — Резервное копирование")
    print("  3 — Восстановление из копии")
    print("  4 — Анализ производительности (отчёт)")
    print("  5 — Показать данные (товары с категорией и поставщиком)")
    print("  0 — Выход")
    print()
    return input("  Выберите пункт: ").strip()


def run_init():
    from create_database import main as init_main
    init_main()


def run_backup():
    from backup_db import run_backup
    run_backup()


def run_restore():
    path = input("  Введите папку бэкапа (например backups/products_db_20250216_120000): ").strip()
    if not path:
        print("  Отменено.")
        return
    from restore_db import run_restore
    from pathlib import Path
    from config import PROJECT_DIR
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_DIR / p
    run_restore(p)


def run_performance():
    from performance_analysis import main as perf_main
    perf_main()


def run_show_data():
    from csv_db import v_products_full, set_role
    set_role("reader")
    rows = v_products_full(limit=20)
    print(f"\n  Товары (показано до 20): всего {len(rows)} записей\n")
    for r in rows:
        print(f"    {r.get('product_name')} | {r.get('category_name')} | {r.get('supplier_name')} | {r.get('price')} руб. | кол-во {r.get('quantity')}")
    print()


def main():
    while True:
        try:
            choice = menu()
        except (EOFError, KeyboardInterrupt):
            print("\n  Выход.")
            sys.exit(0)
        if choice == "0":
            print("  Выход.")
            break
        if choice == "1":
            run_init()
        elif choice == "2":
            run_backup()
        elif choice == "3":
            run_restore()
        elif choice == "4":
            run_performance()
        elif choice == "5":
            run_show_data()
        else:
            print("  Неизвестный пункт.")


if __name__ == "__main__":
    main()
