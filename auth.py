# -*- coding: utf-8 -*-
"""
Авторизация: пользователи, роли, пароли и профиль.
Хранение в data/users.csv (логин, пароль, роль, ФИО, телефон).
ПИН-код для просмотра паролей админом: 1111
"""

import csv
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import DATA_DIR

USERS_FILE = DATA_DIR / "users.csv"
ADMIN_PIN = "1111"

ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
ROLE_VIEW = "view"


def _ensure_users_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        # Создаём пустой файл пользователей (без предустановленных логинов/паролей)
        with open(USERS_FILE, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["username", "password", "role", "full_name", "phone"])
            w.writeheader()


def _load_users() -> List[Dict[str, str]]:
    _ensure_users_file()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # Гарантируем наличие всех полей
    for u in rows:
        u.setdefault("username", "")
        u.setdefault("password", "")
        u.setdefault("role", ROLE_VIEW)
        u.setdefault("full_name", "")
        u.setdefault("phone", "")
    return rows


def _save_users(rows: List[Dict[str, str]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["username", "password", "role", "full_name", "phone"])
        w.writeheader()
        w.writerows(rows)


def check_pin(pin: str) -> bool:
    """Проверка ПИН-кода для просмотра паролей (только admin)."""
    return pin.strip() == ADMIN_PIN


def check_login(username: str, password: str) -> Optional[str]:
    """
    Проверка логина и пароля. Возвращает роль (admin, manager, view) или None.
    """
    users = _load_users()
    for u in users:
        if (u.get("username", "").strip().lower() == username.strip().lower() and
                u.get("password", "") == password):
            return u.get("role", ROLE_VIEW)
    return None


def get_all_users() -> List[Dict[str, str]]:
    """Список всех пользователей (логин, роль, ФИО, телефон, пароль)."""
    return _load_users()


def get_all_users_with_pin(pin: str) -> List[Dict[str, str]]:
    """Список пользователей с паролями только при верном ПИН-коде."""
    if not check_pin(pin):
        return []
    return _load_users()


def add_user(username: str, password: str, role: str) -> None:
    """Добавить пользователя (только admin)."""
    username = username.strip()
    if not username or not password:
        raise ValueError("Логин и пароль не могут быть пустыми")
    role = role.strip().lower()
    if role not in (ROLE_ADMIN, ROLE_MANAGER, ROLE_VIEW):
        raise ValueError("Роль должна быть: admin, manager, view")
    users = _load_users()
    for u in users:
        if u.get("username", "").strip().lower() == username.lower():
            raise ValueError("Пользователь с таким логином уже существует")
    users.append({"username": username, "password": password, "role": role, "full_name": "", "phone": ""})
    _save_users(users)


def update_password(username: str, old_password: str, new_password: str) -> None:
    """Сменить пароль (пользователь вводит старый и новый)."""
    if not new_password:
        raise ValueError("Новый пароль не может быть пустым")
    users = _load_users()
    for u in users:
        if u.get("username", "").strip().lower() == username.strip().lower():
            if u.get("password", "") != old_password:
                raise ValueError("Неверный текущий пароль")
            u["password"] = new_password
            _save_users(users)
            return
    raise ValueError("Пользователь не найден")


def admin_set_password(username: str, new_password: str) -> None:
    """Админ задаёт новый пароль пользователю (без проверки старого)."""
    if not new_password:
        raise ValueError("Пароль не может быть пустым")
    users = _load_users()
    for u in users:
        if u.get("username", "").strip().lower() == username.strip().lower():
            u["password"] = new_password
            _save_users(users)
            return
    raise ValueError("Пользователь не найден")


def delete_user(username: str) -> None:
    """Удалить пользователя (только admin). Нельзя удалить себя (admin)."""
    users = _load_users()
    users = [u for u in users if u.get("username", "").strip().lower() != username.strip().lower()]
    if len(users) == len(_load_users()):
        raise ValueError("Пользователь не найден")
    _save_users(users)


def update_profile(username: str, new_username: str, full_name: str, phone: str) -> None:
    """Обновить профиль пользователя: логин, ФИО, телефон (без смены пароля)."""
    new_username = new_username.strip()
    if not new_username:
        raise ValueError("Логин не может быть пустым")
    users = _load_users()
    # Проверка на конфликт логинов (если логин меняется)
    if new_username.lower() != username.strip().lower():
        for u in users:
            if u.get("username", "").strip().lower() == new_username.lower():
                raise ValueError("Пользователь с таким логином уже существует")
    found = False
    for u in users:
        if u.get("username", "").strip().lower() == username.strip().lower():
            u["username"] = new_username
            u["full_name"] = full_name.strip()
            u["phone"] = phone.strip()
            found = True
            break
    if not found:
        raise ValueError("Пользователь не найден")
    _save_users(users)
