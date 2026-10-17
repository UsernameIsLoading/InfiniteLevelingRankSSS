"""Cria uma cópia do banco local do Necromante System."""
from pathlib import Path
from datetime import datetime
import shutil

home = Path.home() / ".necromante_system"
db = home / "game.db"
if not db.exists():
    raise SystemExit(f"Banco não encontrado: {db}\nAbra o aplicativo pelo menos uma vez.")
backups = home / "backups"
backups.mkdir(parents=True, exist_ok=True)
dest = backups / f"game_{datetime.now():%Y%m%d_%H%M%S}.db"
shutil.copy2(db, dest)
print(f"Backup criado: {dest}")
