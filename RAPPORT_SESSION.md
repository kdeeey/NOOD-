COMMANDES POUR DÉMARRER

```bash
# 1. Installer les dépendances (ordre important)
pip install -r requirements.txt
pip install -r backend/requirements_api.txt

# 2. Démarrer le serveur
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 3. Accéder à la documentation
# http://localhost:8000/docs
```

---

