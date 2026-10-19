# autoback - Auto back up

Auteur(s) : Gaétan Lepage
Création : 15/09/2026
Description :

> Duplication journalière automatique (horodatée) de dossier source à dossier d'archivage.
> Heure unique pour tous les backup, choisie par l'utilisateur.
> Envoi optionnel des résultats par mail.

## Prérequis

**Python** : `Python 3.8+`

**Dépendances externes** :
  - questionary
  - platformdirs
  - tomli_w
  - tkinter
  - [optionnel] pytest 

## Utilisation

```bash
#pip install -r requirements.txt
python -m autobackup [-v] [--run]
```
- `-v` pour montrer les message d'INFO et de DEBUG
- `--run` pour démarrer le backup complet sans interactions utilisateurs.

## Versions

1.0.0 - 18/10/24 - Version autérieure
2.x.x - - Package managing


## Plus d'informations sur le projet

### Structure du projet

```text
autobackup-project/
├── pyproject.toml
├── requirements.txt
├── README.md
├── src/autobackup/
│   ├── __main__.py          # Point d'entrée : setup, logging, menu principal
│   ├── settings.py          # Mise en place et gestion de l'environnement
│   ├── paths.py             # Emplacements standards (platformdirs)
│   ├── pairs.py             # Lecture/écriture TOML (pairs.toml, settings.toml)
│   ├── logs.py              # Configuration du logging
│   ├── file_explorer.py     # Boîtes de navigation de fichiers
│   ├── notify.py            # Rapport de backup -> envoi par mail
│   ├── operations/          # Actions du menu
│   │   ├── add.py           # Ajouter une paire de backup
│   │   ├── edit_list.py     # Modifier la liste des paires
│   │   ├── edit_settings.py # Modifier les paramètres
│   │   └── backup.py        # Sauvegarder toutes les paires
│   └── scheduler/           # Planification, selon l'OS
│       ├── __init__.py      # Interface publique (indépendante de l'OS)
│       ├── launchd.py       # macOS
│       ├── systemd.py       # Linux
│       └── windows.py       # Windows
└── tests/
    ├── test_email_sender.py
    ├── test_scheduler_launchd.py
    ├── data_input/          # Données d'exemple à sauvegarder
    └── data_ouput/          # Résultats de backup de test
```

### Logging

**Attendu**
- Mode normal : WARNING, ERROR visibles sur le stdout ; INFO, WARNING, ERROR écrits dans *autobackup.logs*
- Mode verbal : INFO, WARNING, ERROR sur stdout ; DEBUG, INFO, WARNING, ERROR dans *autobackup.logs*
- ERROR : fonctionnement de la sauvegarde ou de l'application mit à défaut.
- WARNING : action annulée ou partiellement annulée, peut être réglé sur la session en cours.
- INFO : Comportement attendu. 
- DEBUG : Valeurs d'input et d'ouput (paramètres et résultats de fonctions).

**Erreurs Handling**
- Une fonction lève une exception si son contrat est enfreint ? (arg/return) ? 
- Tous Captés ou non ?

**Format des messages**
- FILE_FORMAT = *"time - level-8s : moduleName | message"*
- CONSOLE_FORMAT = *"level-8s : moduleName | message"*  