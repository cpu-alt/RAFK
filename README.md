# RAFK

Petit outil Windows qui garde ta session Roblox active pendant que tu es AFK
(Roblox déconnecte après 20 min d'inactivité).

Il ne touche pas au jeu : il trouve la ou les fenêtres `RobloxPlayerBeta.exe`,
leur donne le focus, envoie une touche (saut par défaut) toutes les ~10 min,
puis rend le focus à la fenêtre que tu utilisais.

## Prérequis

- Windows
- Python 3.11+ (aucune dépendance externe)

## Utilisation

```bash
cp config.example.toml config.toml
python -m rafk
```

Options :

- `--place <id>` : lance le jeu `<id>` avant de démarrer l'anti-AFK
- `--once` : envoie une seule touche puis quitte (pour tester)
- `-c <fichier>` : autre fichier de config

## Roadmap

- [ ] Détection de déconnexion + relance automatique
- [ ] Icône dans la barre des tâches (pause / reprise)
- [ ] Mouvements de caméra en plus des touches
- [ ] Logs dans un fichier
