# Console Prospection Insta · Lauric

Console de suivi du setting Instagram de Lauric : entonnoir (messages, nouveaux abonnés, scans acceptés, scans remplis) avec sélecteur Hier / 3 / 7 / 30 jours, chiffres clés avec delta vs 7 jours précédents et cumul du mois, tuiles « Messages par catégorie », vue par setter, messages par jour, alerte si l'EOD n'est plus rempli. Instagram uniquement, LinkedIn exclu.

## Où ça vit

| | |
|---|---|
| **Page live (à partager)** | https://alexyoucompte99-lang.github.io/console-prospection-lauric/ |
| **Artifact Claude (copie figée)** | https://claude.ai/code/artifact/80404996-d93b-4883-8258-e895c32ce168 |
| **Repo** | https://github.com/alexyoucompte99-lang/console-prospection-lauric |

La page live n'a pas besoin d'être régénérée : elle lit les Google Sheets **en direct dans le navigateur**, à chaque ouverture, au retour sur l'onglet (si la dernière lecture date de plus de 5 min), toutes les 10 min tant que l'onglet est visible, et sur clic du bouton **Actualiser**. Le petit badge en haut à droite dit d'où viennent les chiffres et de quand ils datent.

## Sources

Google Sheets publics, export CSV direct par URL (pas besoin du MCP Drive) :

- EOD setters : `1vVzQXjAGp-lzF1LTeDMg281dan3TcPxrksvWvxZQRuU`, onglet gid `123224703` (« Réponses au formulaire 1 »)
- Soumissions Tally (scans remplis) : `1aMQ_zNQbq2xyntex3V_6GDY5pE9pIaD_v-FTCzJWxes`

Google renvoie bien les en-têtes CORS sur `export?format=csv`, y compris sur la redirection : le `fetch` depuis GitHub Pages passe.

## Fichiers

- `index.html` — toute la console (parsing CSV, agrégation, rendu). Seul fichier à modifier.
- `data/eod.csv`, `data/tally.csv` — copie de secours, utilisée seulement si Google est injoignable. Rafraîchie par GitHub Actions.
- `build.py` — télécharge les CSV et génère `dashboard.html` (copie figée d'`index.html` avec les CSV inlinés) pour l'artifact Claude, qui ne peut pas appeler le réseau.
- `.github/workflows/refresh.yml` — cron 6 h et 11 h UTC, commit `data/` si ça a bougé.

`dashboard.html` est généré, il n'est pas versionné.

## Republier l'artifact Claude

```bash
python3 build.py
```

Puis outil Artifact avec `file_path` = chemin absolu de `dashboard.html`, `url` = l'artifact ci-dessus (URL stable, toujours republier dessus), `favicon` = 🎯.

Options : `--data-only` (télécharge seulement, utilisé par l'Action), `--no-fetch` (réutilise les CSV locaux, debug).

## Pièges connus

- Valeurs sales dans l'EOD : « 25/30 », « 40 (messages) », « P », textes libres. On prend le premier nombre trouvé, sinon 0. Les cellules texte sans chiffre (« Pas de likes ni commentaires ») comptent 0, c'est voulu.
- Colonnes du form longtemps vides : likes (15) et commentaires (16) ont commencé à se remplir en août 2026, scans acceptés (17) démarre à peine, scans remplis (18) toujours vide. Tant qu'une colonne n'a jamais reçu de valeur, la page affiche « pas encore reporté » au lieu de faux zéros, et bascule toute seule dès qu'elle se remplit.
- Le Tally n'a pas de colonne date : il sert de compteur total (+ prénoms), pas de données par jour.
- Les fenêtres 3 / 7 / 30 j se terminent au dernier jour reporté (hier en général, aujourd'hui si l'EOD du jour est déjà là). La ligne sous l'entonnoir dit combien de jours de la fenêtre ont vraiment un EOD.
- Plusieurs lignes EOD par date (plusieurs setters, corrections) : elles s'additionnent.
- Catégories du graphe : Abonnés = colonnes nouveaux + anciens ; Relances = colonne 7 ; Autres = colonne 5 (like/commentaire/story en texte libre au début du form).
- Les colonnes de l'EOD sont repérées par **index**, pas par nom. Si une question est insérée dans le formulaire, tout décale : ajuster `COL` dans `index.html` et les constantes de `build.py`.

## Prévisualisation locale

Serveur `lauric-dashboard` dans `/Users/alex/Alex/.claude/launch.json` (port 8752), page `index.html`.
