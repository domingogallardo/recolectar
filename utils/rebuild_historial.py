#!/usr/bin/env python3
"""
Rebuild Historial.txt from scratch.

• Incluye todos los .md en   Posts/Posts <año>/
• Incluye todos los .pdf en  Pdfs/Pdfs  <año>/
• Orden: más nuevo arriba, según fecha de creación (st_ctime)
• Sobrescribe Historial.txt (hace copia .bak por seguridad)
"""

from pathlib import Path
import shutil
import config as cfg  # BASE_DIR, HISTORIAL

def collect_files():
    """Devuelve lista de Path con .md y .pdf relevantes."""
    files = []

    # Posts
    for year_dir in (cfg.BASE_DIR / "Posts").glob("Posts *"):
        files.extend(year_dir.glob("*.md"))

    # Pdfs
    for year_dir in (cfg.BASE_DIR / "Pdfs").glob("Pdfs *"):
        files.extend(year_dir.glob("*.pdf"))

    return files

def get_creation_time(path: Path) -> float:
    """
    Devuelve la fecha de creación (st_ctime) del archivo.
    En la mayoría de sistemas Unix es la fecha de cambio de metadatos,
    pero en macOS es realmente la fecha de creación real.
    """
    return path.stat().st_ctime

def main():
    all_files = collect_files()

    # Ordenar por fecha de creación (más recientes primero)
    all_files.sort(key=get_creation_time, reverse=True)

    # Formatear rutas relativas con "./"
    lines = ["./" + f.relative_to(cfg.BASE_DIR).as_posix() + "\n"
             for f in all_files]

    # Copia de seguridad
    if cfg.HISTORIAL.exists():
        shutil.copy2(cfg.HISTORIAL, cfg.HISTORIAL.with_suffix(".bak"))

    # Sobrescribir Historial.txt
    cfg.HISTORIAL.write_text("".join(lines), encoding="utf-8")

    print(f"Historial reconstruido: {len(lines)} entradas (ordenadas por creación).")

if __name__ == "__main__":
    main()