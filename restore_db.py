# -*- coding: utf-8 -*-
"""
Восстановление БД из резервной копии (CSV).
Восстанавливает файлы из указанной папки бэкапа в data/.
Запуск: python restore_db.py <папка_бэкапа>
"""

import shutil
import sys
from pathlib import Path

from config import DATA_DIR, BACKUP_DIR, PROJECT_DIR


def run_restore(backup_path: Path) -> None:
    """Восстановить БД из папки с CSV-файлами."""
    if not backup_path.exists():
        print(f"Папка не найдена: {backup_path}")
        sys.exit(1)
    if not backup_path.is_dir():
        print("Укажите папку с резервной копией (например backups/products_db_20250216_120000)")
        sys.exit(1)
    csv_files = list(backup_path.glob("*.csv"))
    if not csv_files:
        print("В указанной папке нет CSV-файлов.")
        sys.exit(1)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for f in csv_files:
        dest = DATA_DIR / f.name
        shutil.copy2(f, dest)
        print(f"  Восстановлен {f.name}")
    print(f"Восстановление из {backup_path} завершено.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python restore_db.py <папка_бэкапа>")
        print("Пример: python restore_db.py backups/products_db_20250216_120000")
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.is_absolute():
        candidate = PROJECT_DIR / path
        path = candidate if candidate.exists() else path
    run_restore(path)
