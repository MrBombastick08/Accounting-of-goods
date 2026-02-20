# -*- coding: utf-8 -*-
"""Настройки проекта: каталоги данных и отчётов."""

from pathlib import Path

# Каталог проекта
PROJECT_DIR = Path(__file__).resolve().parent
# Данные БД (CSV)
DATA_DIR = PROJECT_DIR / "data"
BACKUP_DIR = PROJECT_DIR / "backups"
REPORTS_DIR = PROJECT_DIR / "reports"
