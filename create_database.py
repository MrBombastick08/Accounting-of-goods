# -*- coding: utf-8 -*-
"""
Инициализация БД учета товаров на CSV: создание каталога data/ и CSV-файлов
с тестовыми данными (Категории, Поставщики, Товары, Поставки).
Запуск: python create_database.py
"""

import sys
from config import DATA_DIR, BACKUP_DIR, REPORTS_DIR
from csv_db import set_role, save_table, TABLES, MANAGER, load_table


def generate_initial_data():
    """Сгенерировать начальные данные для всех таблиц."""
    categories = [
        {"id": 1, "name": "Электроника", "description": "Товары электроники"},
        {"id": 2, "name": "Одежда", "description": "Одежда и обувь"},
        {"id": 3, "name": "Продукты", "description": "Продовольственные товары"},
    ]
    suppliers = [
        {"id": 1, "name": "Поставщик А", "contact": "+7-999-111-11-11", "address": "Москва"},
        {"id": 2, "name": "Поставщик Б", "contact": "+7-999-222-22-22", "address": "Санкт-Петербург"},
        {"id": 3, "name": "Поставщик В", "contact": "+7-999-333-33-33", "address": "Казань"},
    ]
    products = [
        {"id": 1, "name": "Ноутбук", "category_id": 1, "supplier_id": 1, "price": "75000.00", "quantity": 10, "created_at": "2025-02-16 12:00:00"},
        {"id": 2, "name": "Телефон", "category_id": 1, "supplier_id": 1, "price": "25000.00", "quantity": 50, "created_at": "2025-02-16 12:00:00"},
        {"id": 3, "name": "Куртка", "category_id": 2, "supplier_id": 2, "price": "5000.00", "quantity": 30, "created_at": "2025-02-16 12:00:00"},
        {"id": 4, "name": "Хлеб", "category_id": 3, "supplier_id": 3, "price": "50.00", "quantity": 200, "created_at": "2025-02-16 12:00:00"},
        {"id": 5, "name": "Монитор", "category_id": 1, "supplier_id": 1, "price": "15000.00", "quantity": 25, "created_at": "2025-02-16 12:00:00"},
        {"id": 6, "name": "Кроссовки", "category_id": 2, "supplier_id": 2, "price": "3500.00", "quantity": 40, "created_at": "2025-02-16 12:00:00"},
        {"id": 7, "name": "Молоко", "category_id": 3, "supplier_id": 3, "price": "80.00", "quantity": 150, "created_at": "2025-02-16 12:00:00"},
    ]
    deliveries = [
        {"id": 1, "product_id": 1, "supplier_id": 1, "quantity": 5, "delivery_date": "2025-02-06", "created_at": "2025-02-06 10:00:00"},
        {"id": 2, "product_id": 2, "supplier_id": 1, "quantity": 20, "delivery_date": "2025-02-11", "created_at": "2025-02-11 14:00:00"},
        {"id": 3, "product_id": 4, "supplier_id": 3, "quantity": 100, "delivery_date": "2025-02-14", "created_at": "2025-02-14 09:00:00"},
        {"id": 4, "product_id": 5, "supplier_id": 1, "quantity": 10, "delivery_date": "2025-02-15", "created_at": "2025-02-15 11:00:00"},
    ]
    return {"categories": categories, "suppliers": suppliers, "products": products, "deliveries": deliveries}


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    set_role(MANAGER)

    data = generate_initial_data()
    for name in TABLES:
        existing = load_table(name)
        if existing:
            print(f"  Таблица {name} уже содержит данные ({len(existing)} записей), пропуск.")
            continue
        save_table(name, data[name])
        print(f"  Создан {name}.csv — {len(data[name])} записей.")

    print("Готово. БД на CSV инициализирована.")


if __name__ == "__main__":
    try:
        main()
    except PermissionError as e:
        print("Ошибка доступа:", e)
        sys.exit(1)
    except Exception as e:
        print("Ошибка:", e)
        sys.exit(1)
