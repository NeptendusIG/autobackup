# Outil de backup CLI — document de cadrage

*Version du 12 octobre 2026 · nom de l'application provisoire : `backup_tool`*

---

## 1. Objectif

Un outil en ligne de commande, en Python, qui copie chaque jour une liste de paires **source → destination**, à une heure unique, sans intervention manuelle, et qui envoie un rapport par mail.

Les priorités, dans l'ordre :

1. **Fiabilité** : l'outil ne plante pas, et un échec est toujours signalé.
2. **Fonctionnement autonome** : rien à relancer à la main.
3. **Simplicité** : peu d'options, mais chacune doit être robuste.

**Plateformes cibles :** Windows Server (cible principale, redémarré de temps en temps), macOS et Linux. Le fonctionnement sur les trois plateformes est une exigence ferme.

---

## 2. Périmètre

**Inclus**
- La gestion d'une liste de paires source → destination, avec au plus un ou deux paramètres par paire.
- Un backup quotidien, à la même heure pour toutes les paires.
- Le déclenchement automatique par le planificateur du système.
- Un rapport par mail (SMTP via Gmail), lisible depuis un autre appareil.
- La journalisation (logs) sur disque.

**Exclu**
- Des horaires différents selon la paire.
- Une interface graphique.
- Un démon Python qui tourne en permanence.
- Les notifications de bureau locales.

---

## 3. Décisions prises

**D1 — La planification est déléguée au planificateur natif de chaque OS.**
Ce sont launchd (macOS), un timer systemd (Linux) et le Planificateur de tâches (Windows). On n'utilise ni `schedule` ni APScheduler.
*Raison :* un démon Python devrait lui-même être maintenu en vie et relancé au démarrage, ce qui ramène au planificateur natif. Le système gère déjà le déclenchement, le rattrapage des exécutions manquées et les redémarrages.

**D2 — La configuration est un fichier TOML, pas une base SQLite.**
*Raison :* une liste de paires est de la configuration, pas des données relationnelles. SQLite ne se justifierait que pour un historique des exécutions qu'on voudrait interroger.
*Pourquoi pas un `.txt` :* il faudrait inventer un format maison et écrire son propre parseur. Le choix du séparateur pose problème, car les chemins Windows contiennent `:`, des espaces et parfois des virgules. Il faudrait aussi gérer les commentaires, les lignes vides, le paramètre optionnel et les erreurs de saisie. TOML est un fichier texte tout aussi lisible, avec une grammaire standard et un parseur déjà testé.
On lit le fichier avec `tomllib` (bibliothèque standard, Python ≥ 3.11). On l'écrit avec **`tomli-w`**, car `tomllib` ne sait que lire.

Exemple :

```toml
heure = "02:00"
destinataire = "moi@exemple.com"
smtp_mot_de_passe = "xxxx xxxx xxxx xxxx"

[[paires]]
source = 'D:\Donnees'
destination = 'E:\Backup\Donnees'
```

En édition manuelle, les chemins Windows se mettent entre apostrophes simples (chaînes littérales) ; sinon les `\` sont interprétés comme des échappements. Quand la config est écrite par le CLI, `tomli-w` s'en charge.

**D3 — Les emplacements de fichiers sont fournis par `platformdirs`.**
La config, les logs et l'état sont rangés dans les dossiers standards de chaque OS, sans aucun chemin codé en dur. Tous les chemins sont manipulés avec `pathlib`.

**D4 — Le moteur de copie est écrit en Python pur** (`shutil`, `os`).
rsync n'existe pas nativement sous Windows.

**D5 — Les mails passent par `smtplib`, avec un compte Gmail dédié et un mot de passe d'application.**
- La validation en deux étapes est activée sur ce compte.
- Le mot de passe d'application est révocable et n'est jamais le mot de passe principal.
- Le compte sert uniquement au backup ; il est distinct du compte personnel.

**D6 — Le secret ne vit jamais dans le code ni dans le dépôt.**
Le stockage est détaillé au §8.

**D7 — La journalisation utilise `logging`** (bibliothèque standard).
Les logs sont écrits dans un fichier tournant (`RotatingFileHandler`), dans le dossier de logs fourni par `platformdirs`.

**D8 — Les sous-commandes sont analysées par `argparse`** (bibliothèque standard).
`questionary` sert uniquement aux commandes interactives.

---

## 4. Architecture

```
backup_tool/
├── pyproject.toml
├── README.md
├── src/
│   └── backup_tool/
│       ├── __main__.py        # point d'entrée : python -m backup_tool
│       ├── cli.py             # sous-commandes argparse + prompts questionary
│       ├── config.py          # lecture / écriture / validation du TOML
│       ├── backup.py          # moteur de copie + rapport d'exécution
│       ├── notify.py          # construction et envoi du mail
│       ├── logs.py            # configuration du logging
│       ├── paths.py           # emplacements via platformdirs
│       └── scheduler/
│           ├── __init__.py    # interface commune + détection de l'OS
│           ├── windows.py
│           ├── launchd.py
│           └── systemd.py
└── tests/
```

Le module de logs s'appelle `logs.py` et non `logging.py`, pour éviter toute confusion avec le module standard.

### Rôle de chaque module

| Module | Responsabilité |
|---|---|
| `__main__` | Initialise le logging et délègue à `cli`. |
| `cli` | Définit les sous-commandes et les prompts interactifs. Contient toute l'interface utilisateur et aucune logique métier. |
| `config` | Charge, valide et sauvegarde la liste des paires et les réglages globaux (heure, destinataire du mail). |
| `backup` | Exécute les copies et produit un objet *rapport*. Ne dépend ni de `cli` ni de `questionary`. |
| `notify` | Transforme un rapport en mail et l'envoie. |
| `scheduler` | Installe ou retire la tâche quotidienne selon l'OS détecté. |
| `paths` / `logs` | Fournissent les emplacements standards et la configuration des logs. |

**Règle de dépendance :** le moteur (`backup`, `notify`) ne connaît pas l'interface. Il est exécuté sans terminal par le planificateur, donc il ne doit jamais rien demander à l'utilisateur.

---

## 5. Commandes

| Commande | Rôle | Interactive |
|---|---|---|
| `add` | Ajoute une paire source → destination | oui |
| `list` | Affiche les paires configurées | non |
| `remove` | Supprime une paire | oui |
| `run` | Exécute le backup (c'est elle que le planificateur appelle) | **non** |
| `install --time HH:MM` | Enregistre la tâche quotidienne | non |
| `uninstall` | Retire la tâche | non |
| `test-mail` | Envoie un mail de test | non |

`run` est strictement non interactive. Elle renvoie le code de sortie `0` si tout s'est bien passé, et un code non nul sinon.

---

## 6. Moteur de backup : règles de robustesse

- **Isolation des erreurs.** Une erreur sur un fichier n'arrête pas la paire, et une erreur sur une paire n'arrête pas les autres. Toutes les erreurs sont collectées dans le rapport.
- **Vérifications préalables.** On vérifie que la source existe et que la destination est accessible. Si la destination est un disque externe ou un partage réseau non monté, le run échoue au lieu d'écrire dans le point de montage vide.
- **Copie atomique.** Chaque fichier est d'abord écrit dans un fichier temporaire à côté de la cible, puis renommé avec `os.replace`. Il n'y a donc jamais de fichier à moitié copié en destination.
- **Métadonnées.** On utilise `shutil.copy2` pour conserver la date de modification.
- **Fichiers inchangés.** On compare la taille et la date de modification pour ne pas tout recopier. Le détail dépend de la stratégie de copie retenue (§10, question 1).
- **Verrou.** Deux exécutions simultanées sont empêchées, par exemple un run manuel pendant le run planifié. Un fichier verrou naïf reste bloqué après un crash : il faut utiliser un vrai verrou système (bibliothèque `filelock`) ou gérer explicitement le verrou périmé.
- **Rapport.** Il contient le nombre de fichiers copiés, ignorés et en erreur, le volume, la durée et la liste des erreurs. Ce rapport alimente à la fois le mail et le log.
- **Échec d'envoi du mail.** Il est journalisé et ne fait jamais planter le run.

### Points spécifiques à Windows

- **Chemins de plus de 260 caractères.** Il faut activer les chemins longs (clé de registre `LongPathsEnabled`) ou utiliser le préfixe `\\?\`.
- **Fichiers ouverts par un autre programme.** Ils lèvent une `PermissionError`, qui doit être traitée comme une erreur sur ce fichier, pas comme un plantage.
- **Tests.** Tout cela doit être testé tôt, sur le serveur réel.

---

## 7. Planification par OS

**Interface commune :** `install(heure, commande)`, `uninstall()`, `is_installed()`.

**Commande enregistrée :** le chemin absolu de l'interpréteur (`sys.executable`, celui du venv), suivi de `-m backup_tool run`. Le planificateur ne dispose ni du `PATH` ni de l'environnement de ton shell.

### Windows — Planificateur de tâches
- On génère un XML de tâche et on l'enregistre avec `schtasks /Create /XML`.
- On coche « Exécuter même si l'utilisateur n'est pas connecté ». Le mot de passe du compte est alors demandé à l'installation.
- On active `StartWhenAvailable` : une exécution manquée (serveur redémarré à l'heure prévue) est rattrapée dès que possible.
- La tâche tourne sous un compte précis. La config, les logs et le secret doivent donc être ceux de ce compte, car `platformdirs` renvoie les dossiers de l'utilisateur qui exécute la commande.

### Linux — timer systemd
- On crée deux unités utilisateur : un `.service`, qui porte la commande, et un `.timer` avec `OnCalendar=*-*-* HH:MM:00` et `Persistent=true`. `Persistent=true` rattrape une exécution manquée pendant que la machine était éteinte.
- La commande `loginctl enable-linger <user>` permet au timer de tourner sans session ouverte.

### macOS — launchd
- On place une plist dans `~/Library/LaunchAgents`, avec `StartCalendarInterval`.
- Une exécution manquée pendant la veille est lancée au réveil. Une exécution manquée pendant que la machine était éteinte est perdue.
- Un LaunchAgent ne tourne que si l'utilisateur a une session ouverte. Un LaunchDaemon tourne sans session, mais demande les droits administrateur.

---

## 8. Notifications et identifiants

### Politique proposée (à confirmer)
- Un mail à **chaque échec**.
- Un **résumé quotidien** en cas de succès. Il sert de signe de vie : s'il n'arrive pas, c'est que le backup n'a pas tourné. Sans ce résumé, un planificateur en panne passe inaperçu.

### Envoi
On utilise `smtplib` et `email.message.EmailMessage`, avec le serveur `smtp.gmail.com` sur le port 465 (SSL) ou 587 (STARTTLS).

### Stockage du mot de passe d'application
Le mot de passe d'application est stocké **en clair dans le fichier de config**, rangé dans le dossier `platformdirs`, hors du dépôt. Il n'y a ni variable d'environnement, ni permissions spéciales, ni rien de spécifique à un OS.

- *Pourquoi pas de restriction de permissions :* le serveur est local et fermé. Restreindre l'accès au fichier n'apporterait presque rien, et cela coûterait du code propre à chaque OS (ACL Windows, `chmod`).
- *Pourquoi pas de variable d'environnement :* une variable définie dans le shell (`.zshrc`, `.bashrc`) n'est pas vue par launchd ni par systemd.
- *La seule règle non négociable :* le mot de passe n'est jamais dans le code ni dans un fichier versionné. C'est le dépôt Git qui reste le vecteur de fuite réel, au premier push sur GitHub.
- *Le filet de sécurité :* le compte Gmail est dédié au backup et le mot de passe d'application est révocable. En cas de fuite, on révoque l'ancien et on en génère un nouveau, sans toucher au compte personnel.

---

## 9. Dépendances

- **Externes :** `questionary`, `platformdirs`, `tomli-w`, et éventuellement `filelock`.
- **Développement :** `pytest`.
- **Bibliothèque standard :** `argparse`, `tomllib`, `pathlib`, `os`, `shutil`, `logging`, `smtplib`, `email`, `subprocess` (pour enregistrer les tâches) et `sys`.
- **Python ≥ 3.11**, à cause de `tomllib`.

---

## 10. Questions ouvertes

1. **La stratégie de copie.** C'est la décision la plus structurante, et elle n'est pas encore prise.
   - *Miroir* : la destination reflète exactement la source, suppressions comprises. Le risque est qu'une suppression accidentelle ou un chiffrement par rançongiciel soit propagé dès le run suivant.
   - *Copie additive* : on copie et on met à jour, sans jamais rien supprimer en destination. C'est simple, mais la destination grossit, et un fichier corrompu écrase sa bonne version.
   - *Instantanés datés* : un dossier par jour, avec une rétention (on garde N jours). C'est l'option la plus sûre et la plus coûteuse en espace.
2. **La politique de notification.** Faut-il confirmer « mail à chaque échec + résumé quotidien » ?
3. **Les paramètres par paire.** Lesquels exactement : motifs d'exclusion, activer ou désactiver une paire… ? On en garde au plus un ou deux.
4. **Le compte d'exécution sur le serveur Windows.** Quel compte utiliser, et a-t-il accès aux destinations (partages réseau, disques) ?
5. **L'installation sur le serveur.** Avec `pipx` ou dans un venv dédié ?
6. **Les tests sur plusieurs OS.** As-tu un accès direct aux trois OS, ou faut-il une CI GitHub Actions avec une matrice Windows / macOS / Ubuntu ?
7. **Le nom de l'application.**

---

## 11. Plan de démarrage

> Principe : on n'automatise que ce qui marche déjà parfaitement à la main.

1. Créer le squelette : `pyproject.toml`, la structure `src/`, `logs.py` et `paths.py`.
2. Écrire `config.py` et les commandes `add`, `list` et `remove`.
3. Écrire `backup.py` et la commande `run`, lancée à la main. La tester sur des dossiers temporaires (`pytest`, `tmp_path`), y compris tous les cas d'erreur.
4. Écrire `notify.py` et la commande `test-mail`.
5. Écrire le backend Windows du planificateur et le tester sur le serveur réel, y compris un redémarrage pendant l'heure prévue.
6. Écrire les backends systemd et launchd.
7. Mettre en place la CI sur plusieurs OS.

**La question 1 (stratégie de copie) doit être tranchée avant l'étape 3.**