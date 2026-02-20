# -*- coding: utf-8 -*-
"""
Резервное копирование БД учета товаров (CSV).
Копирует каталог data/ в backups/products_db_YYYYMMDD_HHMMSS/.
Запуск: python backup_db.py [имя_папки]
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

from config import DATA_DIR, BACKUP_DIR


def run_backup(output_path: Path = None) -> Path:
    """Создать резервную копию папки data/. Возвращает путь к папке копии."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = BACKUP_DIR / f"products_db_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if not DATA_DIR.exists():
        print("Каталог data/ не найден. Сначала выполните: python create_database.py")
        sys.exit(1)
    if output_path.exists():
        shutil.rmtree(output_path)
    shutil.copytree(DATA_DIR, output_path)
    print(f"Резервная копия создана: {output_path}")
    return output_path


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else None
    path = Path(name) if name else None
    if path and not path.is_absolute():
        path = BACKUP_DIR / path
    run_backup(path)
