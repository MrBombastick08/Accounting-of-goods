# -*- coding: utf-8 -*-
"""
Слой работы с БД на CSV: загрузка/сохранение, индексы, представления (VIEW),
логика триггера при поставке, разграничение прав по ролям.
"""

import csv
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional

from config import DATA_DIR

# Роли (разграничение прав по ТЗ)
READER = "reader"
MANAGER = "manager"

_current_role: str = MANAGER


def set_role(role: str) -> None:
    """Установить текущую роль (reader или manager)."""
    global _current_role
    if role not in (READER, MANAGER):
        raise ValueError("Роль должна быть 'reader' или 'manager'")
    _current_role = role


def get_role() -> str:
    return _current_role


def _require_manager() -> None:
    if _current_role != MANAGER:
        raise PermissionError("Доступ запрещён: требуется роль manager.")


# Имена таблиц и файлов
TABLES = ("categories", "suppliers", "products", "deliveries")


def _table_path(name: str) -> Path:
    return DATA_DIR / f"{name}.csv"


def _cast_row(table: str, row: Dict[str, str]) -> Dict[str, Any]:
    """Приведение типов при чтении CSV."""
    if table == "categories":
        return {"id": int(row["id"]), "name": row["name"], "description": row.get("description", "")}
    if table == "suppliers":
        return {"id": int(row["id"]), "name": row["name"], "contact": row.get("contact", ""), "address": row.get("address", "")}
    if table == "products":
        return {
            "id": int(row["id"]),
            "name": row["name"],
            "category_id": int(row["category_id"]),
            "supplier_id": int(row["supplier_id"]),
            "price": Decimal(row["price"]),
            "quantity": int(row["quantity"]),
            "created_at": row.get("created_at", ""),
        }
    if table == "deliveries":
        return {
            "id": int(row["id"]),
            "product_id": int(row["product_id"]),
            "supplier_id": int(row["supplier_id"]),
            "quantity": int(row["quantity"]),
            "delivery_date": row.get("delivery_date", ""),
            "created_at": row.get("created_at", ""),
        }
    return dict(row)


def load_table(name: str) -> List[Dict[str, Any]]:
    """Загрузить таблицу из CSV. Возвращает список словарей."""
    path = _table_path(name)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [_cast_row(name, row) for row in reader]


def save_table(name: str, rows: List[Dict[str, Any]]) -> None:
    """Сохранить таблицу в CSV. Требуется роль manager."""
    _require_manager()
    path = _table_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: str(v) for k, v in row.items()})


# --- Индексы (в памяти для ускорения поиска) ---

def build_index_by_id(rows: List[Dict]) -> Dict[int, Dict]:
    """Индекс по полю id."""
    return {int(r["id"]): r for r in rows}


def build_index_by_key(rows: List[Dict], key: str) -> Dict[Any, List[Dict]]:
    """Индекс по произвольному полю (например category_id)."""
    idx: Dict[Any, List[Dict]] = {}
    for r in rows:
        k = r.get(key)
        if k not in idx:
            idx[k] = []
        idx[k].append(r)
    return idx


def get_next_id(name: str) -> int:
    """Следующий свободный id в таблице."""
    rows = load_table(name)
    if not rows:
        return 1
    return max(int(r["id"]) for r in rows) + 1


# --- Представления (VIEW) ---

def v_products_full(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Товары с названиями категории и поставщика (аналог VIEW)."""
    products = load_table("products")
    categories = build_index_by_id(load_table("categories"))
    suppliers = build_index_by_id(load_table("suppliers"))
    result = []
    for p in products:
        c = categories.get(p["category_id"], {})
        s = suppliers.get(p["supplier_id"], {})
        result.append({
            "id": p["id"],
            "product_name": p["name"],
            "price": p["price"],
            "quantity": p["quantity"],
            "created_at": p.get("created_at"),
            "category_name": c.get("name", ""),
            "category_description": c.get("description", ""),
            "supplier_name": s.get("name", ""),
            "supplier_contact": s.get("contact", ""),
        })
    if limit is not None:
        result = result[:limit]
    return result


def v_deliveries_full(days_back: Optional[int] = None) -> List[Dict[str, Any]]:
    """Поставки с названиями товара и поставщика (аналог VIEW)."""
    deliveries = load_table("deliveries")
    products = build_index_by_id(load_table("products"))
    suppliers = build_index_by_id(load_table("suppliers"))
    result = []
    for d in deliveries:
        p = products.get(d["product_id"], {})
        s = suppliers.get(d["supplier_id"], {})
        result.append({
            "id": d["id"],
            "quantity": d["quantity"],
            "delivery_date": d.get("delivery_date"),
            "created_at": d.get("created_at"),
            "product_name": p.get("name", ""),
            "price": p.get("price"),
            "supplier_name": s.get("name", ""),
        })
    result.sort(key=lambda x: (x.get("delivery_date") or ""), reverse=True)
    if days_back is not None:
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        result = [r for r in result if (r.get("delivery_date") or "") >= cutoff]
    return result


def v_stock_by_category() -> List[Dict[str, Any]]:
    """Остатки по категориям: название, кол-во товаров, суммарное кол-во, стоимость (аналог VIEW)."""
    categories = load_table("categories")
    products = load_table("products")
    by_cat = build_index_by_key(products, "category_id")
    result = []
    for c in categories:
        cid = c["id"]
        prods = by_cat.get(cid, [])
        total_qty = sum(p["quantity"] for p in prods)
        total_value = sum(float(p["price"]) * p["quantity"] for p in prods)
        result.append({
            "category_name": c["name"],
            "products_count": len(prods),
            "total_quantity": total_qty,
            "total_value": round(total_value, 2),
        })
    return result


# --- Запросы для анализа производительности ---

def query_products_by_category_name(category_name: str) -> List[Dict]:
    """Товары по имени категории (с использованием индекса по категории)."""
    categories = load_table("categories")
    cat_id = next((c["id"] for c in categories if c["name"] == category_name), None)
    if cat_id is None:
        return []
    products = load_table("products")
    by_cat = build_index_by_key(products, "category_id")
    return by_cat.get(cat_id, [])


def query_products_price_above(price_min: float) -> List[Dict]:
    """Товары с ценой выше заданной, по убыванию цены."""
    products = load_table("products")
    return sorted([p for p in products if float(p["price"]) > price_min], key=lambda p: float(p["price"]), reverse=True)


def query_suppliers_delivery_count() -> List[Dict[str, Any]]:
    """Поставщики с количеством поставок (агрегация)."""
    suppliers = load_table("suppliers")
    deliveries = load_table("deliveries")
    by_supplier = build_index_by_key(deliveries, "supplier_id")
    result = []
    for s in suppliers:
        sid = s["id"]
        result.append({"name": s["name"], "deliveries_count": len(by_supplier.get(sid, []))})
    return result


# --- Триггер: при добавлении поставки обновить остаток товара ---

def add_delivery(product_id: int, supplier_id: int, quantity: int, delivery_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Добавить поставку и автоматически увеличить остаток товара (логика триггера).
    Требуется роль manager.
    """
    _require_manager()
    if delivery_date is None:
        delivery_date = datetime.now().strftime("%Y-%m-%d")
    deliveries = load_table("deliveries")
    new_id = get_next_id("deliveries")
    new_row = {
        "id": new_id,
        "product_id": product_id,
        "supplier_id": supplier_id,
        "quantity": quantity,
        "delivery_date": delivery_date,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    deliveries.append(new_row)
    save_table("deliveries", deliveries)

    # Триггер: обновить quantity в products
    products = load_table("products")
    for p in products:
        if p["id"] == product_id:
            p["quantity"] = p["quantity"] + quantity
            break
    save_table("products", products)
    return new_row


# --- Редактирование и добавление записей (сохранение в CSV) ---

def get_row(table: str, row_id: int) -> Optional[Dict[str, Any]]:
    """Получить одну запись по id."""
    rows = load_table(table)
    for r in rows:
        if int(r["id"]) == row_id:
            return r
    return None


def update_row(table: str, row_id: int, updates: Dict[str, Any]) -> None:
    """Обновить запись в таблице. Изменения сохраняются в CSV. Требуется роль manager."""
    _require_manager()
    rows = load_table(table)
    for r in rows:
        if int(r["id"]) == row_id:
            for k, v in updates.items():
                if k in r:
                    if table == "products" and k == "price":
                        r[k] = Decimal(str(v))
                    else:
                        r[k] = v
            save_table(table, rows)
            return
    raise ValueError(f"Запись с id={row_id} не найдена в {table}")


def add_category(name: str, description: str = "") -> Dict[str, Any]:
    """Добавить категорию. Сохраняется в CSV."""
    _require_manager()
    rows = load_table("categories")
    new_id = get_next_id("categories")
    row = {"id": new_id, "name": name, "description": description}
    rows.append(row)
    save_table("categories", rows)
    return row


def add_supplier(name: str, contact: str = "", address: str = "") -> Dict[str, Any]:
    """Добавить поставщика. Сохраняется в CSV."""
    _require_manager()
    rows = load_table("suppliers")
    new_id = get_next_id("suppliers")
    row = {"id": new_id, "name": name, "contact": contact, "address": address}
    rows.append(row)
    save_table("suppliers", rows)
    return row


def add_product(name: str, category_id: int, supplier_id: int, price: float, quantity: int = 0) -> Dict[str, Any]:
    """Добавить товар. Сохраняется в CSV."""
    _require_manager()
    rows = load_table("products")
    new_id = get_next_id("products")
    row = {
        "id": new_id,
        "name": name,
        "category_id": category_id,
        "supplier_id": supplier_id,
        "price": Decimal(str(price)),
        "quantity": quantity,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    rows.append(row)
    save_table("products", rows)
    return row


def update_delivery(
    delivery_id: int,
    product_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    quantity: Optional[int] = None,
    delivery_date: Optional[str] = None,
) -> None:
    """
    Обновить поставку. При изменении количества или товара остатки пересчитываются.
    Сохраняется в CSV.
    """
    _require_manager()
    deliveries = load_table("deliveries")
    old_row = None
    for d in deliveries:
        if int(d["id"]) == delivery_id:
            old_row = dict(d)
            break
    if not old_row:
        raise ValueError(f"Поставка с id={delivery_id} не найдена")
    old_qty = int(old_row["quantity"])
    old_pid = int(old_row["product_id"])
    new_pid = int(product_id) if product_id is not None else old_pid
    new_qty = int(quantity) if quantity is not None else old_qty
    if product_id is not None:
        old_row["product_id"] = product_id
    if supplier_id is not None:
        old_row["supplier_id"] = supplier_id
    if quantity is not None:
        old_row["quantity"] = quantity
    if delivery_date is not None:
        old_row["delivery_date"] = delivery_date
    for d in deliveries:
        if int(d["id"]) == delivery_id:
            d.update(old_row)
            break
    save_table("deliveries", deliveries)
    products = load_table("products")
    if old_pid != new_pid or old_qty != new_qty:
        for p in products:
            if p["id"] == old_pid:
                p["quantity"] = p["quantity"] - old_qty
                break
        for p in products:
            if p["id"] == new_pid:
                p["quantity"] = p["quantity"] + new_qty
                break
        save_table("products", products)


# --- Хранимая процедура (отчёт по поставкам за период) ---

def sp_deliveries_report(date_from: Optional[str] = None, date_to: Optional[str] = None) -> List[Dict[str, Any]]:
    """Отчёт по поставкам за период (аналог хранимой процедуры)."""
    deliveries = v_deliveries_full()
    if date_from:
        deliveries = [d for d in deliveries if (d.get("delivery_date") or "") >= date_from]
    if date_to:
        deliveries = [d for d in deliveries if (d.get("delivery_date") or "") <= date_to]
    return deliveries
