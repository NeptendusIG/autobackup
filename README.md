# autobackup - Automatic backup

Auteur(s) : Gaétan Lepage
Création : 15/09/2026
Description :

> Duplication journalière automatique (horodatée) de dossier source à dossier d'archivage.
> Heure unique pour tous les backup, choisie par l'utilisateur.
> Envoi optionnel des résultats par mail.

## *Installation*

### **Requirements**

- Python : `Python 3.11+`
- Dépendances externes : questionary platformdirs, tomli_w, tkinter, [optionnel] pytest 

### **Installation**

- Installer les requirements
```bash
#pip install -r requirements.txt
```
- Installer le programme
- Activer l'environnement
- Lancer les tests


## *Utilisation*

```bash
# Activer l'environnement
# Lancer l'application
python -m autobackup [-v] [--run]
```
- `-v` pour montrer les message d'INFO et de DEBUG
- `--run` pour démarrer le backup complet sans interactions utilisateurs.

- Mettre en place un canal de notifications
    - Télécharger l'application NTFY sur smartphone
    - Ouvrir les paramètres de autobackup, cela génère un code.
    - Écrire le code dans les paramètres ET sur un abonnement NTFY.
    - Tester en lançant un backup.


## *Cahier des charges*

- Fonction principale : Application CLI de backup automatiques journaliers avec Gestion de la liste des backup traqués (source & destination).
    - Ajout et suppression du suivis de dossier.
    - Backup journalier avec choix de l'heure d'exécution.
    - Les copies sont horodatées et jamais supprimées.
    - Envoi d'un compte rendu des sauvegardes possible à chaque Backup.

- Contraintes :
    - Fonctionnement sur le Server Windows.
    - Fiabilité du programme (maitriser les erreurs générées pour ne pas planter).
    - Expérience utilisateur "intuitive..."


## *Plus d'informations sur le projet*

- Décisions de Mise en oeuvre :
    - Les sources sont des dossiers (copie tout le contenu)
    - Le compte rendu est envoyé via un canal de l'application ntfy

### **Versions (Roadmap)**

- 1.0.0 - 18/10/24 - Version autérieure

- 2.0.0 - - Refactorisation du projet pour de la dépendance en Package managing
- 2.0.1 - - (fondations) Module de l'application principale et du logging 
- 2.0.2 - - 

- 2.1.0 - 26/10/26 - Fonction principale atteinte 
- 2.1.1 - 26/10/26 - Meilleure lisibilité des notifications
- 2.2.0 - 29/10/26 - Error managing et Logging amélioré

**Futur**

- 2.3.x -  - Notification par mail en cas de problème
- 2.4.x -  - Refactoriser les affichages en intégrant plus d'informations (taille et modif)
- 2.5.x -  - Refactoriser l'accès paramètres pour contrôler les modifs et ajouter des fonctionnalités (réduire les notifs/mails, clear la tâche en cours, changer de modes en "only-if-new-modifications").

- 3.x.x -  - *Changer la base du projet (langage, base, fonction principale)*


### **Structure du projet**

```text
autobackup-project/
├── pyproject.toml
├── requirements.txt
├── README.md
├── src/autobackup/
│   ├── __main__.py          # Point d'entrée : setup, logging, menu principal
│   ├── backup_results.py
│   ├── paths.py             # Emplacements standards (platformdirs)
│   ├── pairs.py             # Lecture/écriture TOML (pairs.toml, settings.toml)
│   ├── logs.py              # Configuration du logging
│   ├── file_explorer.py     # Boîtes de navigation de fichiers
│   ├── notify.py            # Rapport de backup -> envoi par notifications
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
- DEBUG : Valeurs d'input et d'ouput (paramètres et résultats de fonctions) pour diagnostique.
- INFO : Trace du déroulement normal.
- WARNING : action annulée ou partiellement annulée, peut être réglé sur la session en cours.
- ERROR : fonctionnement de la sauvegarde ou de l'application mit à défaut.
- CRITICAL : L'application ne peut pas continuer.

**Erreurs Handling**
- Une fonction lève une exception si son contrat est enfreint ? (arg/return) ? 
- Tous Captés ou non ?

**Format des messages**
- FILE_FORMAT = *"time - level-8s : moduleName | message"*
- CONSOLE_FORMAT = *"level-8s : moduleName | message"*  