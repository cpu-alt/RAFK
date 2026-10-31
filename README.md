# RAFK

[![CI](https://github.com/cpu-alt/RAFK/actions/workflows/ci.yml/badge.svg)](https://github.com/cpu-alt/RAFK/actions/workflows/ci.yml)

Anti-AFK Roblox pour Windows : lance ton jeu, pars, RAFK garde ta session en vie
(Roblox déconnecte après 20 min d'inactivité) et relance le jeu s'il plante.

Il ne touche pas au jeu : pas d'injection, pas de lecture mémoire. Il envoie
simplement des touches clavier à la fenêtre Roblox, comme tu le ferais.

## Fonctionnalités

- **Actions variées** : saut, petit pas avant/arrière, rotation de caméra, zoom…
  tirées au hasard, à intervalle aléatoire.
- **Ne te dérange pas** : si tu utilises le PC, RAFK attend que tu sois inactif
  avant de prendre le focus, et ne force l'action qu'avant le kick. Si tu joues,
  il ne fait rien. Le focus revient ensuite sur ta fenêtre, et Roblox est
  re-minimisé s'il l'était.
- **Multi-comptes** : gère toutes les fenêtres Roblox ouvertes.
- **Auto-rejoin** : si Roblox se ferme, crash ou se fige, RAFK nettoie les
  processus bloqués et relance le jeu (avec backoff 1 → 10 min).
- **Détection de déconnexion** (expérimental) : lit les logs Roblox pour
  repérer l'écran « Disconnected » et relancer.
- **Anti-veille** : empêche le PC de s'endormir tant que RAFK tourne.
- **Pause/reprise** avec **F8**.
- **Notifications Discord** (démarrage, crash, relance, arrêt + stats).
- Python pur, zéro dépendance.

## Installation

Windows + [Python 3.11+](https://www.python.org/downloads/).

```bash
git clone https://github.com/cpu-alt/RAFK.git
cd RAFK
copy config.example.toml config.toml
```

## Utilisation

Le plus simple : double-clique sur **`RAFK.bat`**.

En ligne de commande :

| Commande | Effet |
| --- | --- |
| `python -m rafk` | anti-AFK sur les fenêtres Roblox ouvertes |
| `python -m rafk --place 920587237` | lance ce jeu, garde-le actif, relance si besoin |
| `python -m rafk --list` | diagnostic : fenêtres et processus Roblox détectés |
| `python -m rafk --once` | une seule action puis quitte (test) |
| `python -m rafk -c autre.toml` | autre fichier de config |

L'ID du jeu est le nombre dans l'URL : `roblox.com/games/`**`920587237`**`/...`

Toutes les options sont commentées dans [`config.example.toml`](config.example.toml).

## Dépannage

- **« Aucune fenêtre Roblox trouvée » alors que Roblox tourne** : lance
  `python -m rafk --list`. Si tu vois « Roblox tourne SANS fenêtre de jeu »,
  un lancement est resté bloqué : ferme-le dans le Gestionnaire des tâches
  (RAFK le fait tout seul en mode `--place`).
- **Le raccourci F8 ne marche pas** : une autre appli l'utilise, change
  `pause_hotkey`.

## Développement

```bash
python -m unittest discover -s tests -v
```

## Avertissement

Les outils anti-AFK sont tolérés en pratique mais vont techniquement contre
les conditions d'utilisation de Roblox. À utiliser en connaissance de cause.
