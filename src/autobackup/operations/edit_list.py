"""
Opérations pour modifier la liste des paires de backup.
"""
import logging
from pathlib import Path

import questionary as q

from autobackup.pairs import read_pairs, write_pairs, Pair
from autobackup.paths import config_dir


logger = logging.getLogger(__name__)



def manage_edit_list():
    """
    Gère l'affichage et la modification de la liste des paires de backup.

    requirements:
        - config_dir() doit exister et contenir pairs.toml
        - config_dir()/...toml doit exister (même si default).
    """
    # - 1 - Récupérer la liste actuelle
    pairs: list[Pair] = read_pairs(config_dir())
    logger.debug("Current backup pairs: %s", pairs)
    if not pairs:
        q.print("No backup pairs found. Please add a pair first.")

    # - 2 - Afficher la liste et demander à l'utilisateur ce qu'il veut faire
    choices = [q.Choice(f"(edit) {pair.source} -> {pair.destination}", value=i) for (i, pair) in enumerate(pairs)]

    selected = q.select(
        f"Current backup pairs ({len(pairs)}):",
        choices=choices + [q.Separator(), q.Choice("Exit", value="exit")],
        #style=q.Style(
        #    q.Token.Separator: "#888888",
        #    q.Token.Choice: "#00ff00",
        #    q.Token.Selected: "#00ff00",
        #),
    ).unsafe_ask()
    logger.debug(f"User selected pair index: {selected}")
    if selected == "exit":
        logger.info("User exited the edit list menu.")
        return

    # - 3 - Traiter la sélection de l'utilisateur
    if _edit_pair(pairs, selected):
        write_pairs(config_dir(), pairs)
        logger.debug("Updated backup pairs saved to pairs.toml.")




def _edit_pair(pairs: list[Pair], index: int) -> bool:
    """
    Permet à l'utilisateur de modifier une paire existante.
    """
    pair = pairs[index]
    logger.debug("User selected pair: %s -> %s", pair.source, pair.destination)
    choice = q.select(
        f"Selected pair: {pair.source} -> {pair.destination}. What do you want to do?",
        choices=[
            q.Choice("Edit source", value="edit_source"),
            q.Choice("Edit destination", value="edit_destination"),
            q.Choice("Delete pair", value="delete"),
            q.Separator(),
            q.Choice("Cancel (back to menu)", value="exit"),
        ],
    ).unsafe_ask()
    if choice is None or choice == "exit":
        logger.info("User cancelled the action on the selected pair.")
        return False

    match choice:
        case "edit_source":
            new_source = Path(q.path("Enter new source path:", 
                                default=str(pair.source),
                                validate=lambda x: Path(x).exists()
                                ).unsafe_ask())
            if not new_source.exists():
                logger.warning("New source path %s does not exist.", new_source)
                q.print(f"Warning: The new source path {new_source} does not exist.")
                return False
            pair.source = new_source
            logger.info("Updated source for pair %d to %s.", index, new_source)
            return True

        case "edit_destination":
            new_destination = Path(q.path("Enter new destination path:", 
                                     default=str(pair.destination),
                                     validate=lambda x: Path(x).exists()
                                     ).unsafe_ask())
            if not new_destination.exists():
                logger.warning("New destination path %s does not exist.", new_destination)
                q.print(f"Warning: The new destination path {new_destination} does not exist.")
                return False
            pair.destination = new_destination
            logger.info("Updated destination for pair %d to %s.", index, new_destination)
            return True

        case "delete":
            if not q.confirm("Supprimer cette paire ?", default=False).unsafe_ask():
                return False
            logger.info("Paire %d supprimée : %s → %s", index, pair.source, pair.destination)
            pairs.pop(index)
            return True

        case _:
            logger.error("Unexpected choice: %s", choice)
            return False 
    
