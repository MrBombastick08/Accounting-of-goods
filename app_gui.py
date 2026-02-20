# -*- coding: utf-8 -*-
"""
Графический интерфейс приложения «БД учета товаров» на CustomTkinter.
Окно входа по ролям: admin, manager, view. Запуск: python app_gui.py
"""

import customtkinter as ctk
from tkinter import ttk
from pathlib import Path

from config import PROJECT_DIR, REPORTS_DIR
from csv_db import (
    set_role,
    MANAGER,
    READER,
    load_table,
    v_products_full,
    v_deliveries_full,
    v_stock_by_category,
    add_delivery,
    add_category,
    add_supplier,
    add_product,
    update_row,
    update_delivery,
    get_row,
)
from auth import (
    check_login,
    ROLE_ADMIN,
    ROLE_MANAGER,
    ROLE_VIEW,
    get_all_users,
    get_all_users_with_pin,
    check_pin,
    add_user,
    update_password,
    admin_set_password,
    delete_user,
    update_profile,
)


def run_init():
    from create_database import main as init_main
    init_main()


def run_backup():
    from backup_db import run_backup
    return run_backup()


def run_restore(backup_path: Path):
    from restore_db import run_restore
    run_restore(backup_path)


def run_performance():
    from performance_analysis import main as perf_main
    perf_main()
    # Последний отчёт
    reports = sorted(REPORTS_DIR.glob("performance_report_*.txt"), reverse=True)
    if reports:
        return reports[0]
    return None


class App(ctk.CTk):
    def __init__(self, current_username: str = "admin", current_role: str = ROLE_ADMIN):
        super().__init__()
        self.current_username = current_username
        self.current_role = current_role
        set_role(MANAGER if current_role in (ROLE_ADMIN, ROLE_MANAGER) else READER)

        self.title("БД учета товаров")
        self.geometry("920x640")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Верхняя строка: пользователь, профиль, выход; для admin — раздел пользователей
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=(10, 0))
        role_label = {"admin": "Администратор", "manager": "Менеджер", "view": "Просмотр"}.get(current_role, current_role)
        ctk.CTkLabel(top_bar, text=f"Пользователь: {current_username} ({role_label})").pack(side="left", padx=(0, 15))
        ctk.CTkButton(top_bar, text="Профиль", width=120, command=self._dialog_profile).pack(side="left", padx=(0, 8))
        if current_role == ROLE_ADMIN:
            ctk.CTkButton(top_bar, text="Пользователи", width=120, command=self._dialog_manage_users).pack(side="left", padx=(0, 8))
        ctk.CTkButton(top_bar, text="Выход", width=80, command=self._logout).pack(side="right")

        self.tabview = ctk.CTkTabview(self, width=880, height=560)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)
        self.tabview.add("Данные")
        self.tabview.add("Действия")
        self.tabview.add("Новая поставка")

        self._build_data_tab()
        self._build_actions_tab()
        self._build_delivery_tab()
        self._refresh_delivery_combos()
        self._apply_role()

    def _build_data_tab(self):
        tab = self.tabview.tab("Данные")
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", pady=(0, 5))
        self.data_combo = ctk.CTkComboBox(
            top,
            values=[
                "Товары (с категорией и поставщиком)",
                "Поставки",
                "Категории",
                "Поставщики",
                "Остатки по категориям",
            ],
            width=320,
            command=self._on_data_type_changed,
        )
        self.data_combo.pack(side="left", padx=(0, 10))
        self.btn_refresh = ctk.CTkButton(top, text="Обновить", width=100, command=self._refresh_data)
        self.btn_refresh.pack(side="left", padx=(0, 5))
        self.btn_edit = ctk.CTkButton(top, text="Изменить", width=90, command=self._edit_selected)
        self.btn_edit.pack(side="left", padx=(0, 5))
        self.btn_add = ctk.CTkButton(top, text="Добавить", width=90, command=self._add_new)
        self.btn_add.pack(side="left")
        # Таблица через Treeview
        frame = ctk.CTkFrame(tab, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(frame, show="headings", height=18)
        scroll_y = ttk.Scrollbar(frame)
        scroll_x = ttk.Scrollbar(frame, orient="horizontal")
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)
        self._refresh_data()

    def _on_data_type_changed(self, choice):
        self._refresh_data()

    def _get_selected_row_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        item = self.tree.item(sel[0])
        vals = item.get("values")
        if vals:
            return vals[0]  # first column is id
        return None

    def _edit_selected(self):
        choice = self.data_combo.get()
        row_id = self._get_selected_row_id()
        if row_id is None:
            self._show_message("Выберите запись в таблице.")
            return
        row_id = int(row_id)
        if "Товары" in choice:
            self._dialog_edit_product(row_id)
        elif "Поставки" in choice:
            self._dialog_edit_delivery(row_id)
        elif "Категории" in choice:
            self._dialog_edit_category(row_id)
        elif "Поставщики" in choice:
            self._dialog_edit_supplier(row_id)
        else:
            self._show_message("Редактирование для этого вида недоступно.")

    def _add_new(self):
        choice = self.data_combo.get()
        if "Товары" in choice:
            self._dialog_add_product()
        elif "Поставки" in choice:
            self.tabview.set("Новая поставка")
        elif "Категории" in choice:
            self._dialog_add_category()
        elif "Поставщики" in choice:
            self._dialog_add_supplier()
        else:
            self._show_message("Добавление для этого вида недоступно.")

    def _show_message(self, msg: str, title: str = "Сообщение"):
        win = ctk.CTkToplevel(self)
        win.title(title)
        win.geometry("400x100")
        ctk.CTkLabel(win, text=msg, wraplength=360).pack(pady=20, padx=20)
        ctk.CTkButton(win, text="OK", command=win.destroy).pack(pady=(0, 15))
        win.transient(self)
        win.grab_set()

    def _dialog_edit_category(self, row_id: int):
        row = get_row("categories", row_id)
        if not row:
            return
        win = ctk.CTkToplevel(self)
        win.title("Изменить категорию")
        win.geometry("400x180")
        ctk.CTkLabel(win, text="Название:").pack(anchor="w", padx=20, pady=(15, 0))
        e_name = ctk.CTkEntry(win, width=340)
        e_name.pack(padx=20, pady=5)
        e_name.insert(0, row.get("name", ""))
        ctk.CTkLabel(win, text="Описание:").pack(anchor="w", padx=20, pady=(10, 0))
        e_desc = ctk.CTkEntry(win, width=340)
        e_desc.pack(padx=20, pady=5)
        e_desc.insert(0, row.get("description", ""))

        def save():
            name = e_name.get().strip()
            if not name:
                return
            update_row("categories", row_id, {"name": name, "description": e_desc.get().strip()})
            self._refresh_data()
            win.destroy()

        ctk.CTkButton(win, text="Сохранить", command=save).pack(pady=15)
        win.transient(self)

    def _dialog_add_category(self):
        win = ctk.CTkToplevel(self)
        win.title("Добавить категорию")
        win.geometry("520x240")
        ctk.CTkLabel(win, text="Название:").pack(anchor="w", padx=20, pady=(15, 0))
        e_name = ctk.CTkEntry(win, width=340)
        e_name.pack(padx=20, pady=5)
        ctk.CTkLabel(win, text="Описание:").pack(anchor="w", padx=20, pady=(10, 0))
        e_desc = ctk.CTkEntry(win, width=340)
        e_desc.pack(padx=20, pady=5)

        def save():
            name = e_name.get().strip()
            if not name:
                return
            add_category(name, e_desc.get().strip())
            self._refresh_data()
            self._refresh_delivery_combos()
            win.destroy()

        ctk.CTkButton(win, text="Сохранить", command=save).pack(pady=15)
        win.transient(self)

    def _dialog_edit_supplier(self, row_id: int):
        row = get_row("suppliers", row_id)
        if not row:
            return
        win = ctk.CTkToplevel(self)
        win.title("Изменить поставщика")
        win.geometry("520x260")
        ctk.CTkLabel(win, text="Название:").pack(anchor="w", padx=20, pady=(15, 0))
        e_name = ctk.CTkEntry(win, width=340)
        e_name.pack(padx=20, pady=5)
        e_name.insert(0, row.get("name", ""))
        ctk.CTkLabel(win, text="Контакты:").pack(anchor="w", padx=20, pady=(10, 0))
        e_contact = ctk.CTkEntry(win, width=340)
        e_contact.pack(padx=20, pady=5)
        e_contact.insert(0, row.get("contact", ""))
        ctk.CTkLabel(win, text="Адрес:").pack(anchor="w", padx=20, pady=(10, 0))
        e_addr = ctk.CTkEntry(win, width=340)
        e_addr.pack(padx=20, pady=5)
        e_addr.insert(0, row.get("address", ""))

        def save():
            name = e_name.get().strip()
            if not name:
                return
            update_row("suppliers", row_id, {"name": name, "contact": e_contact.get().strip(), "address": e_addr.get().strip()})
            self._refresh_data()
            self._refresh_delivery_combos()
            win.destroy()

        ctk.CTkButton(win, text="Сохранить", command=save).pack(pady=15)
        win.transient(self)

    def _dialog_add_supplier(self):
        win = ctk.CTkToplevel(self)
        win.title("Добавить поставщика")
        win.geometry("520x260")
        ctk.CTkLabel(win, text="Название:").pack(anchor="w", padx=20, pady=(15, 0))
        e_name = ctk.CTkEntry(win, width=340)
        e_name.pack(padx=20, pady=5)
        ctk.CTkLabel(win, text="Контакты:").pack(anchor="w", padx=20, pady=(10, 0))
        e_contact = ctk.CTkEntry(win, width=340)
        e_contact.pack(padx=20, pady=5)
        ctk.CTkLabel(win, text="Адрес:").pack(anchor="w", padx=20, pady=(10, 0))
        e_addr = ctk.CTkEntry(win, width=340)
        e_addr.pack(padx=20, pady=5)

        def save():
            name = e_name.get().strip()
            if not name:
                return
            add_supplier(name, e_contact.get().strip(), e_addr.get().strip())
            self._refresh_data()
            self._refresh_delivery_combos()
            win.destroy()

        ctk.CTkButton(win, text="Сохранить", command=save).pack(pady=15)
        win.transient(self)

    def _dialog_edit_product(self, row_id: int):
        row = get_row("products", row_id)
        if not row:
            return
        categories = load_table("categories")
        suppliers = load_table("suppliers")
        win = ctk.CTkToplevel(self)
        win.title("Изменить товар")
        win.geometry("520x320")
        ctk.CTkLabel(win, text="Название:").pack(anchor="w", padx=20, pady=(15, 0))
        e_name = ctk.CTkEntry(win, width=380)
        e_name.pack(padx=20, pady=5)
        e_name.insert(0, row.get("name", ""))
        ctk.CTkLabel(win, text="Категория:").pack(anchor="w", padx=20, pady=(10, 0))
        cat_values = [f"{c['id']} — {c['name']}" for c in categories]
        combo_cat = ctk.CTkComboBox(win, width=380, values=cat_values)
        combo_cat.pack(padx=20, pady=5)
        for c in categories:
            if c["id"] == row["category_id"]:
                combo_cat.set(f"{c['id']} — {c['name']}")
                break
        ctk.CTkLabel(win, text="Поставщик:").pack(anchor="w", padx=20, pady=(10, 0))
        sup_values = [f"{s['id']} — {s['name']}" for s in suppliers]
        combo_sup = ctk.CTkComboBox(win, width=380, values=sup_values)
        combo_sup.pack(padx=20, pady=5)
        for s in suppliers:
            if s["id"] == row["supplier_id"]:
                combo_sup.set(f"{s['id']} — {s['name']}")
                break
        ctk.CTkLabel(win, text="Цена:").pack(anchor="w", padx=20, pady=(10, 0))
        e_price = ctk.CTkEntry(win, width=120)
        e_price.pack(padx=20, pady=5, anchor="w")
        e_price.insert(0, str(row.get("price", "")))
        ctk.CTkLabel(win, text="Количество:").pack(anchor="w", padx=20, pady=(10, 0))
        e_qty = ctk.CTkEntry(win, width=120)
        e_qty.pack(padx=20, pady=5, anchor="w")
        e_qty.insert(0, str(row.get("quantity", 0)))

        def save():
            name = e_name.get().strip()
            if not name:
                return
            cat_id = int(combo_cat.get().split("—")[0].strip())
            sup_id = int(combo_sup.get().split("—")[0].strip())
            price = float(e_price.get().strip().replace(",", "."))
            qty = int(e_qty.get().strip())
            update_row("products", row_id, {"name": name, "category_id": cat_id, "supplier_id": sup_id, "price": price, "quantity": qty})
            self._refresh_data()
            self._refresh_delivery_combos()
            win.destroy()

        ctk.CTkButton(win, text="Сохранить", command=save).pack(pady=15)
        win.transient(self)

    def _dialog_add_product(self):
        categories = load_table("categories")
        suppliers = load_table("suppliers")
        if not categories or not suppliers:
            self._show_message("Сначала добавьте категории и поставщиков.")
            return
        win = ctk.CTkToplevel(self)
        win.title("Добавить товар")
        win.geometry("520x320")
        ctk.CTkLabel(win, text="Название:").pack(anchor="w", padx=20, pady=(15, 0))
        e_name = ctk.CTkEntry(win, width=380)
        e_name.pack(padx=20, pady=5)
        ctk.CTkLabel(win, text="Категория:").pack(anchor="w", padx=20, pady=(10, 0))
        combo_cat = ctk.CTkComboBox(win, width=380, values=[f"{c['id']} — {c['name']}" for c in categories])
        combo_cat.pack(padx=20, pady=5)
        ctk.CTkLabel(win, text="Поставщик:").pack(anchor="w", padx=20, pady=(10, 0))
        combo_sup = ctk.CTkComboBox(win, width=380, values=[f"{s['id']} — {s['name']}" for s in suppliers])
        combo_sup.pack(padx=20, pady=5)
        ctk.CTkLabel(win, text="Цена:").pack(anchor="w", padx=20, pady=(10, 0))
        e_price = ctk.CTkEntry(win, width=120, placeholder_text="0")
        e_price.pack(padx=20, pady=5, anchor="w")
        ctk.CTkLabel(win, text="Количество:").pack(anchor="w", padx=20, pady=(10, 0))
        e_qty = ctk.CTkEntry(win, width=120, placeholder_text="0")
        e_qty.pack(padx=20, pady=5, anchor="w")

        def save():
            name = e_name.get().strip()
            if not name:
                return
            cat_id = int(combo_cat.get().split("—")[0].strip())
            sup_id = int(combo_sup.get().split("—")[0].strip())
            price = float(e_price.get().strip().replace(",", ".") or "0")
            qty = int(e_qty.get().strip() or "0")
            add_product(name, cat_id, sup_id, price, qty)
            self._refresh_data()
            self._refresh_delivery_combos()
            win.destroy()

        ctk.CTkButton(win, text="Сохранить", command=save).pack(pady=15)
        win.transient(self)

    def _dialog_edit_delivery(self, row_id: int):
        row = get_row("deliveries", row_id)
        if not row:
            return
        products = load_table("products")
        suppliers = load_table("suppliers")
        win = ctk.CTkToplevel(self)
        win.title("Изменить поставку")
        win.geometry("520x300")
        ctk.CTkLabel(win, text="Товар:").pack(anchor="w", padx=20, pady=(15, 0))
        combo_prod = ctk.CTkComboBox(win, width=380, values=[f"{p['id']} — {p['name']}" for p in products])
        combo_prod.pack(padx=20, pady=5)
        for p in products:
            if p["id"] == row["product_id"]:
                combo_prod.set(f"{p['id']} — {p['name']}")
                break
        ctk.CTkLabel(win, text="Поставщик:").pack(anchor="w", padx=20, pady=(10, 0))
        combo_sup = ctk.CTkComboBox(win, width=380, values=[f"{s['id']} — {s['name']}" for s in suppliers])
        combo_sup.pack(padx=20, pady=5)
        for s in suppliers:
            if s["id"] == row["supplier_id"]:
                combo_sup.set(f"{s['id']} — {s['name']}")
                break
        ctk.CTkLabel(win, text="Количество:").pack(anchor="w", padx=20, pady=(10, 0))
        e_qty = ctk.CTkEntry(win, width=120)
        e_qty.pack(padx=20, pady=5, anchor="w")
        e_qty.insert(0, str(row.get("quantity", "")))
        ctk.CTkLabel(win, text="Дата (ГГГГ-ММ-ДД):").pack(anchor="w", padx=20, pady=(10, 0))
        e_date = ctk.CTkEntry(win, width=120)
        e_date.pack(padx=20, pady=5, anchor="w")
        e_date.insert(0, row.get("delivery_date", ""))

        def save():
            prod_id = int(combo_prod.get().split("—")[0].strip())
            sup_id = int(combo_sup.get().split("—")[0].strip())
            qty = int(e_qty.get().strip())
            date_val = e_date.get().strip()
            if qty <= 0:
                return
            update_delivery(row_id, product_id=prod_id, supplier_id=sup_id, quantity=qty, delivery_date=date_val or None)
            self._refresh_data()
            win.destroy()

        ctk.CTkButton(win, text="Сохранить", command=save).pack(pady=15)
        win.transient(self)

    def _refresh_data(self):
        for c in self.tree.get_children():
            self.tree.delete(c)
        choice = self.data_combo.get()
        if "Товары" in choice:
            rows = v_products_full()
            cols = ("id", "product_name", "category_name", "supplier_name", "price", "quantity")
            self.tree["columns"] = cols
            headers = {"id": "ID", "product_name": "Товар", "category_name": "Категория", "supplier_name": "Поставщик", "price": "Цена", "quantity": "Кол-во"}
            for col in cols:
                self.tree.heading(col, text=headers.get(col, col))
                self.tree.column(col, width=100)
            for r in rows:
                self.tree.insert("", "end", values=(r.get("id"), r.get("product_name"), r.get("category_name"), r.get("supplier_name"), r.get("price"), r.get("quantity")))
        elif "Поставки" in choice:
            rows = v_deliveries_full()
            cols = ("id", "product_name", "supplier_name", "quantity", "delivery_date")
            self.tree["columns"] = cols
            headers = {"id": "ID", "product_name": "Товар", "supplier_name": "Поставщик", "quantity": "Кол-во", "delivery_date": "Дата"}
            for col in cols:
                self.tree.heading(col, text=headers.get(col, col))
                self.tree.column(col, width=120)
            for r in rows:
                self.tree.insert("", "end", values=(r.get("id"), r.get("product_name"), r.get("supplier_name"), r.get("quantity"), r.get("delivery_date")))
        elif "Категории" in choice:
            rows = load_table("categories")
            cols = ("id", "name", "description")
            self.tree["columns"] = cols
            headers = {"id": "ID", "name": "Название", "description": "Описание"}
            for col in cols:
                self.tree.heading(col, text=headers.get(col, col))
                self.tree.column(col, width=150)
            for r in rows:
                self.tree.insert("", "end", values=(r.get("id"), r.get("name"), r.get("description", "")))
        elif "Поставщики" in choice:
            rows = load_table("suppliers")
            cols = ("id", "name", "contact", "address")
            self.tree["columns"] = cols
            headers = {"id": "ID", "name": "Название", "contact": "Контакты", "address": "Адрес"}
            for col in cols:
                self.tree.heading(col, text=headers.get(col, col))
                self.tree.column(col, width=120)
            for r in rows:
                self.tree.insert("", "end", values=(r.get("id"), r.get("name"), r.get("contact", ""), r.get("address", "")))
        else:
            rows = v_stock_by_category()
            cols = ("category_name", "products_count", "total_quantity", "total_value")
            self.tree["columns"] = cols
            headers = {"category_name": "Категория", "products_count": "Товаров", "total_quantity": "Остаток", "total_value": "Стоимость"}
            for col in cols:
                self.tree.heading(col, text=headers.get(col, col))
                self.tree.column(col, width=120)
            for r in rows:
                self.tree.insert("", "end", values=(r.get("category_name"), r.get("products_count"), r.get("total_quantity"), r.get("total_value")))

    def _build_actions_tab(self):
        tab = self.tabview.tab("Действия")
        self.actions_log = ctk.CTkTextbox(tab, height=120, state="disabled")
        self.actions_log.pack(fill="x", pady=(0, 10))
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x")
        self.btn_init = ctk.CTkButton(btn_frame, text="Инициализировать БД", width=180, command=self._do_init)
        self.btn_init.pack(side="left", padx=(0, 10), pady=5)
        self.btn_backup = ctk.CTkButton(btn_frame, text="Резервная копия", width=180, command=self._do_backup)
        self.btn_backup.pack(side="left", padx=(0, 10), pady=5)
        self.btn_perf = ctk.CTkButton(btn_frame, text="Анализ производительности", width=180, command=self._do_performance)
        self.btn_perf.pack(side="left", padx=(0, 10), pady=5)
        rest_frame = ctk.CTkFrame(tab, fg_color="transparent")
        rest_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(rest_frame, text="Восстановление из папки:").pack(side="left", padx=(0, 5))
        self.restore_entry = ctk.CTkEntry(rest_frame, width=300, placeholder_text="backups/products_db_20250216_120000")
        self.restore_entry.pack(side="left", padx=(0, 10))
        self.btn_restore = ctk.CTkButton(rest_frame, text="Восстановить", width=120, command=self._do_restore)
        self.btn_restore.pack(side="left")

    def _log(self, msg: str):
        self.actions_log.configure(state="normal")
        self.actions_log.insert("end", msg + "\n")
        self.actions_log.see("end")
        self.actions_log.configure(state="disabled")

    def _do_init(self):
        try:
            run_init()
            self._log("БД инициализирована.")
            self._refresh_data()
        except Exception as e:
            self._log(f"Ошибка: {e}")

    def _do_backup(self):
        try:
            path = run_backup()
            self._log(f"Резервная копия: {path}")
        except Exception as e:
            self._log(f"Ошибка: {e}")

    def _do_restore(self):
        path_str = self.restore_entry.get().strip()
        if not path_str:
            self._log("Укажите папку бэкапа.")
            return
        p = Path(path_str)
        if not p.is_absolute():
            p = PROJECT_DIR / p
        try:
            run_restore(p)
            self._log(f"Восстановлено из {p}")
            self._refresh_data()
        except Exception as e:
            self._log(f"Ошибка: {e}")

    def _do_performance(self):
        try:
            report_path = run_performance()
            self._log("Отчёт создан." + (f" Файл: {report_path}" if report_path else ""))
        except Exception as e:
            self._log(f"Ошибка: {e}")

    def _build_delivery_tab(self):
        tab = self.tabview.tab("Новая поставка")
        form = ctk.CTkFrame(tab, fg_color="transparent")
        form.pack(pady=20, padx=20)
        ctk.CTkLabel(form, text="Товар:").grid(row=0, column=0, sticky="w", pady=5, padx=(0, 10))
        products = load_table("products")
        product_values = [f"{p['id']} — {p['name']}" for p in products] or ["— Сначала инициализируйте БД (вкладка Действия)"]
        self.delivery_product_combo = ctk.CTkComboBox(form, width=250, values=product_values)
        self.delivery_product_combo.grid(row=0, column=1, pady=5)
        ctk.CTkLabel(form, text="Поставщик:").grid(row=1, column=0, sticky="w", pady=5, padx=(0, 10))
        suppliers = load_table("suppliers")
        supplier_values = [f"{s['id']} — {s['name']}" for s in suppliers] or ["— Сначала инициализируйте БД"]
        self.delivery_supplier_combo = ctk.CTkComboBox(form, width=250, values=supplier_values)
        self.delivery_supplier_combo.grid(row=1, column=1, pady=5)
        ctk.CTkLabel(form, text="Количество:").grid(row=2, column=0, sticky="w", pady=5, padx=(0, 10))
        self.delivery_qty_entry = ctk.CTkEntry(form, width=120, placeholder_text="10")
        self.delivery_qty_entry.grid(row=2, column=1, sticky="w", pady=5)
        self.btn_delivery = ctk.CTkButton(form, text="Оформить поставку", width=180, command=self._do_add_delivery)
        self.btn_delivery.grid(row=3, column=1, sticky="w", pady=20)
        self.delivery_status = ctk.CTkLabel(tab, text="", text_color="green")
        self.delivery_status.pack(pady=10)

    def _refresh_delivery_combos(self):
        """Обновить списки товаров и поставщиков на вкладке «Новая поставка»."""
        products = load_table("products")
        suppliers = load_table("suppliers")
        self.delivery_product_combo.configure(values=[f"{p['id']} — {p['name']}" for p in products] or ["— Нет товаров"])
        self.delivery_supplier_combo.configure(values=[f"{s['id']} — {s['name']}" for s in suppliers] or ["— Нет поставщиков"])

    def _apply_role(self):
        """Ограничить интерфейс по роли: view — только просмотр."""
        if self.current_role != ROLE_VIEW:
            return
        self.btn_edit.configure(state="disabled")
        self.btn_add.configure(state="disabled")
        self.btn_init.configure(state="disabled")
        self.btn_backup.configure(state="disabled")
        self.btn_perf.configure(state="disabled")
        self.btn_restore.configure(state="disabled")
        self.restore_entry.configure(state="disabled")
        self.btn_delivery.configure(state="disabled")
        self.delivery_product_combo.configure(state="disabled")
        self.delivery_supplier_combo.configure(state="disabled")
        self.delivery_qty_entry.configure(state="disabled")

    def _logout(self):
        """Выход: закрыть приложение и открыть окно входа."""
        self.destroy()
        login = LoginWindow()
        login.mainloop()

    def _dialog_profile(self):
        """Профиль пользователя: логин, ФИО, телефон, смена пароля."""
        win = ctk.CTkToplevel(self)
        win.title("Профиль пользователя")
        win.geometry("520x320")
        # Текущие данные
        me = None
        for u in get_all_users():
            if u.get("username", "").strip().lower() == self.current_username.strip().lower():
                me = u
                break
        full_name = (me or {}).get("full_name", "")
        phone = (me or {}).get("phone", "")
        ctk.CTkLabel(win, text="Логин:").pack(anchor="w", padx=20, pady=(15, 0))
        e_login = ctk.CTkEntry(win, width=360)
        e_login.pack(padx=20, pady=5)
        e_login.insert(0, self.current_username)
        ctk.CTkLabel(win, text="ФИО:").pack(anchor="w", padx=20, pady=(10, 0))
        e_name = ctk.CTkEntry(win, width=360)
        e_name.pack(padx=20, pady=5)
        e_name.insert(0, full_name)
        ctk.CTkLabel(win, text="Телефон:").pack(anchor="w", padx=20, pady=(10, 0))
        e_phone = ctk.CTkEntry(win, width=360)
        e_phone.pack(padx=20, pady=5)
        e_phone.insert(0, phone)
        ctk.CTkLabel(win, text="Текущий пароль (для смены):").pack(anchor="w", padx=20, pady=(10, 0))
        e_old = ctk.CTkEntry(win, width=360, show="•")
        e_old.pack(padx=20, pady=5)
        ctk.CTkLabel(win, text="Новый пароль (необязательно):").pack(anchor="w", padx=20, pady=(10, 0))
        e_new = ctk.CTkEntry(win, width=360, show="•")
        e_new.pack(padx=20, pady=5)
        lbl = ctk.CTkLabel(win, text="", text_color="red")
        lbl.pack(pady=5)

        def save():
            try:
                new_login = e_login.get().strip()
                full_name_new = e_name.get().strip()
                phone_new = e_phone.get().strip()
                old_pass = e_old.get()
                new_pass = e_new.get()
                # Если введён новый пароль — сменить его
                if new_pass:
                    update_password(self.current_username, old_pass, new_pass)
                # Обновить профиль (логин, ФИО, телефон)
                update_profile(self.current_username, new_login, full_name_new, phone_new)
                self.current_username = new_login
                self._show_message("Профиль обновлён.")
                win.destroy()
            except Exception as ex:
                lbl.configure(text=str(ex))

        ctk.CTkButton(win, text="Сохранить", command=save).pack(pady=10)
        win.transient(self)

    def _dialog_manage_users(self):
        """Управление пользователями (только admin) с входом по ПИН-коду."""
        win = ctk.CTkToplevel(self)
        win.title("Пользователи (вход по ПИН)")
        win.geometry("720x520")
        ctk.CTkLabel(win, text="Для входа в раздел пользователей введите ПИН-код:", font=("", 13)).pack(anchor="w", padx=20, pady=(20, 5))
        pin_frame = ctk.CTkFrame(win, fg_color="transparent")
        pin_frame.pack(fill="x", padx=20)
        e_pin = ctk.CTkEntry(pin_frame, width=140, show="•")
        e_pin.pack(side="left")
        lbl_pin_err = ctk.CTkLabel(pin_frame, text="", text_color="red")
        lbl_pin_err.pack(side="left", padx=10)

        content_frame = ctk.CTkFrame(win, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=10, pady=(10, 10))

        def show_users_section():
            lbl_pin_err.configure(text="")
            if not check_pin(e_pin.get()):
                lbl_pin_err.configure(text="Неверный ПИН-код")
                return
            # Очищаем и строим контент
            for w in content_frame.winfo_children():
                w.destroy()
            users = get_all_users_with_pin(e_pin.get())
            ctk.CTkLabel(content_frame, text="Список пользователей (логин, роль, ФИО, телефон):", font=("", 12)).pack(anchor="w", padx=15, pady=(5, 5))
            frame = ctk.CTkScrollableFrame(content_frame, height=220)
            frame.pack(fill="x", padx=15, pady=5)
            for u in users:
                ctk.CTkLabel(frame, text=f"  {u['username']}  —  {u['role']};  {u.get('full_name','')}  {u.get('phone','')}").pack(anchor="w")

            ctk.CTkLabel(content_frame, text="Добавить пользователя:", font=("", 11)).pack(anchor="w", padx=15, pady=(15, 5))
            f_add = ctk.CTkFrame(content_frame, fg_color="transparent")
            f_add.pack(fill="x", padx=15)
            ctk.CTkLabel(f_add, text="Логин:").grid(row=0, column=0, padx=(0, 5), pady=2)
            e_login = ctk.CTkEntry(f_add, width=120)
            e_login.grid(row=0, column=1, padx=(0, 15), pady=2)
            ctk.CTkLabel(f_add, text="Пароль:").grid(row=0, column=2, padx=(0, 5), pady=2)
            e_pass = ctk.CTkEntry(f_add, width=120)
            e_pass.grid(row=0, column=3, padx=(0, 15), pady=2)
            ctk.CTkLabel(f_add, text="Роль:").grid(row=0, column=4, padx=(0, 5), pady=2)
            combo_role = ctk.CTkComboBox(f_add, width=100, values=["admin", "manager", "view"])
            combo_role.grid(row=0, column=5, padx=(0, 10), pady=2)
            lbl_add = ctk.CTkLabel(content_frame, text="", text_color="red")
            lbl_add.pack(anchor="w", padx=15)

            def do_add():
                try:
                    add_user(e_login.get().strip(), e_pass.get(), combo_role.get())
                    lbl_add.configure(text="Пользователь добавлен.", text_color="green")
                    show_users_section()
                except Exception as ex:
                    lbl_add.configure(text=str(ex), text_color="red")

            ctk.CTkButton(f_add, text="Добавить", width=90, command=do_add).grid(row=0, column=6, pady=2)
            ctk.CTkLabel(content_frame, text="Задать новый пароль пользователю:", font=("", 11)).pack(anchor="w", padx=15, pady=(15, 5))
            f_set = ctk.CTkFrame(content_frame, fg_color="transparent")
            f_set.pack(fill="x", padx=15)
            combo_user = ctk.CTkComboBox(f_set, width=150, values=[u["username"] for u in users])
            combo_user.pack(side="left", padx=(0, 10))
            ctk.CTkLabel(f_set, text="Новый пароль:").pack(side="left", padx=(0, 5))
            e_new = ctk.CTkEntry(f_set, width=120)
            e_new.pack(side="left", padx=(0, 10))
            lbl_set = ctk.CTkLabel(content_frame, text="", text_color="red")
            lbl_set.pack(anchor="w", padx=15)

            def do_set():
                try:
                    admin_set_password(combo_user.get(), e_new.get())
                    lbl_set.configure(text="Пароль обновлён.", text_color="green")
                except Exception as ex:
                    lbl_set.configure(text=str(ex), text_color="red")

            ctk.CTkButton(f_set, text="Задать пароль", width=110, command=do_set).pack(side="left")

        ctk.CTkButton(pin_frame, text="Войти в раздел", width=120, command=show_users_section).pack(side="left", padx=10)
        win.transient(self)

    def _do_add_delivery(self):
        self.delivery_status.configure(text="")
        try:
            p_str = self.delivery_product_combo.get()
            s_str = self.delivery_supplier_combo.get()
            qty_str = self.delivery_qty_entry.get().strip()
            if not p_str or not s_str or not qty_str or p_str.startswith("—") or s_str.startswith("—"):
                self.delivery_status.configure(text="Заполните все поля и инициализируйте БД при необходимости.", text_color="orange")
                return
            product_id = int(p_str.split("—")[0].strip())
            supplier_id = int(s_str.split("—")[0].strip())
            quantity = int(qty_str)
            if quantity <= 0:
                self.delivery_status.configure(text="Количество должно быть > 0.", text_color="orange")
                return
            add_delivery(product_id, supplier_id, quantity)
            self.delivery_status.configure(text="Поставка добавлена. Остаток товара обновлён.", text_color="green")
            self.delivery_qty_entry.delete(0, "end")
            self.tabview.set("Данные")
            self._refresh_data()
        except ValueError as e:
            self.delivery_status.configure(text=f"Ошибка ввода: {e}", text_color="orange")
        except Exception as e:
            self.delivery_status.configure(text=str(e), text_color="orange")


class LoginWindow(ctk.CTk):
    """Окно входа / первый запуск (создание администратора)."""

    def __init__(self):
        super().__init__()
        self.title("Вход в систему")
        self.geometry("400x260")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.resizable(False, False)

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        users = get_all_users()
        if not users:
            self._build_first_admin_ui()
        else:
            self._build_login_ui()

    def _build_login_ui(self):
        for w in self.main_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.main_frame, text="БД учета товаров", font=("", 16)).pack(pady=(0, 15))
        ctk.CTkLabel(self.main_frame, text="Логин:").pack(anchor="w")
        self.e_login = ctk.CTkEntry(self.main_frame, width=260)
        self.e_login.pack(pady=(0, 10))
        ctk.CTkLabel(self.main_frame, text="Пароль:").pack(anchor="w")
        self.e_password = ctk.CTkEntry(self.main_frame, width=260, show="•")
        self.e_password.pack(pady=(0, 15))
        self.lbl_error = ctk.CTkLabel(self.main_frame, text="", text_color="red")
        self.lbl_error.pack()
        ctk.CTkButton(self.main_frame, text="Войти", width=120, command=self._do_login).pack(pady=10)
        self.e_password.bind("<Return>", lambda e: self._do_login())

    def _build_first_admin_ui(self):
        """Первый запуск: создание учётной записи администратора (без жёстко зашитых логинов/паролей)."""
        for w in self.main_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.main_frame, text="Первый запуск: создайте администратора", font=("", 14)).pack(pady=(0, 10))
        ctk.CTkLabel(self.main_frame, text="Логин администратора:").pack(anchor="w")
        self.e_admin_login = ctk.CTkEntry(self.main_frame, width=260)
        self.e_admin_login.pack(pady=(0, 8))
        ctk.CTkLabel(self.main_frame, text="Пароль администратора:").pack(anchor="w")
        self.e_admin_pass = ctk.CTkEntry(self.main_frame, width=260, show="•")
        self.e_admin_pass.pack(pady=(0, 8))
        ctk.CTkLabel(self.main_frame, text="ФИО администратора:").pack(anchor="w")
        self.e_admin_name = ctk.CTkEntry(self.main_frame, width=260)
        self.e_admin_name.pack(pady=(0, 8))
        ctk.CTkLabel(self.main_frame, text="Телефон:").pack(anchor="w")
        self.e_admin_phone = ctk.CTkEntry(self.main_frame, width=260)
        self.e_admin_phone.pack(pady=(0, 8))
        self.lbl_admin_err = ctk.CTkLabel(self.main_frame, text="", text_color="red")
        self.lbl_admin_err.pack()
        ctk.CTkButton(self.main_frame, text="Создать администратора", width=180, command=self._do_create_admin).pack(pady=10)

    def _do_create_admin(self):
        from auth import add_user, update_profile, ROLE_ADMIN
        self.lbl_admin_err.configure(text="")
        login = self.e_admin_login.get().strip()
        password = self.e_admin_pass.get()
        full_name = self.e_admin_name.get().strip()
        phone = self.e_admin_phone.get().strip()
        try:
            add_user(login, password, ROLE_ADMIN)
            update_profile(login, login, full_name, phone)
        except Exception as ex:
            self.lbl_admin_err.configure(text=str(ex))
            return
        # После успешного создания сразу открываем главное окно под этим админом
        self.destroy()
        app = App(current_username=login, current_role=ROLE_ADMIN)
        app.mainloop()

    def _do_login(self):
        self.lbl_error.configure(text="")
        username = self.e_login.get().strip()
        password = self.e_password.get()
        if not username or not password:
            self.lbl_error.configure(text="Введите логин и пароль")
            return
        role = check_login(username, password)
        if role is None:
            self.lbl_error.configure(text="Неверный логин или пароль")
            return
        self.destroy()
        app = App(current_username=username, current_role=role)
        app.mainloop()


def main():
    login = LoginWindow()
    login.mainloop()


if __name__ == "__main__":
    main()
