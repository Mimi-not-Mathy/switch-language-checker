# 🎮 Switch Language Checker

Identifie un jeu Nintendo Switch depuis sa boîte et vérifie les langues supportées sur le Nintendo eShop Japon.

---

## 🚀 Déploiement sur Railway (gratuit, accessible depuis mobile)

### Étape 1 — Créer un compte GitHub (si tu n'en as pas)
→ https://github.com/signup

### Étape 2 — Créer un dépôt GitHub avec ces fichiers

1. Va sur https://github.com/new
2. Nom du dépôt : `switch-language-checker`
3. Visibilité : **Private** (recommandé)
4. Clique **Create repository**
5. Sur la page suivante, clique **uploading an existing file**
6. Glisse **tous les fichiers** de ce dossier (server.py, requirements.txt, Procfile, railway.toml, runtime.txt, et le dossier static/)
7. Clique **Commit changes**

### Étape 3 — Déployer sur Railway

1. Va sur https://railway.app
2. Clique **Start a New Project**
3. Choisis **Deploy from GitHub repo**
4. Connecte ton compte GitHub si demandé
5. Sélectionne `switch-language-checker`
6. Railway détecte automatiquement Python et lance le déploiement ✅
7. Une fois déployé, clique sur ton service → onglet **Settings** → **Networking** → **Generate Domain**
8. Tu obtiens une URL publique du type `switch-language-checker.up.railway.app` 🎉

### Étape 4 — Utiliser depuis ton téléphone

Ouvre l'URL générée depuis n'importe quel navigateur, sur n'importe quel appareil !

---

## 💰 Coût

Railway offre **500 heures gratuites/mois** sur le plan Hobby (suffisant pour un usage perso).
Pour un usage 24h/24 : ~5$/mois.

---

## 🛠 Développement local

```bash
pip install -r requirements.txt
python server.py
# → http://localhost:5555
```

---

## 📁 Structure

```
switch-checker/
├── server.py          # Serveur Flask (Google Lens + scraping Nintendo JP)
├── requirements.txt   # Dépendances Python
├── Procfile           # Commande de démarrage pour Railway
├── railway.toml       # Config Railway
├── runtime.txt        # Version Python
└── static/
    └── index.html     # Interface web (upload + caméra)
```
