"""
Boites de navigation de fichier.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import tkinter as tk
    from tkinter import filedialog
except ImportError:          # Tkinter absent (Linux, Python Homebrew…)
    tk = None


def ask_dir(title: str = "Choisir un dossier", initialdir: Path | None = None) -> Path | None:
    """Ouvre un sélecteur de dossier graphique.

    Renvoie le dossier choisi, ou None si l'utilisateur annule.
    Lève RuntimeError si aucune interface graphique n'est disponible.
    """
    if tk is None:
        raise RuntimeError("Tkinter n'est pas installé.")
    try:
        root = tk.Tk()
    except tk.TclError as e:  # pas d'écran (SSH, serveur sans interface)
        raise RuntimeError(f"Pas d'interface graphique : {e}") from e

    try:
        root.withdraw()
        root.attributes("-topmost", True)   # au premier plan, pas derrière le terminal
        folder = filedialog.askdirectory(
            #parent=root,
            title=title,
            #initialdir=initialdir or Path.cwd(),
            mustexist=True,
        )
    finally:
        root.destroy()                       # une seule fenêtre Tk, toujours libérée

    return Path(folder) if folder else None  # annulation : "" ou ()