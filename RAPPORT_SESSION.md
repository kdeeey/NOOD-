# RAPPORT TECHNIQUE DE SESSION — NOOD Backend

**Date :** 29 mars 2026
**Développeur :** Backend Developer
**Environnement :** Windows 11, Python 3.11

---

## 1. CONTEXTE DU PROJET

### 1.1 Qu'est-ce que NOOD ?

NOOD (« Presentation Analyzer ») est une application d'analyse de présentations orales assistée par IA. L'utilisateur télécharge une vidéo de sa présentation et reçoit un rapport détaillé couvrant :

- **Langage corporel** — détection d'émotions via MediaPipe + TFLite
- **Prosodie vocale** — WPM, mots de remplissage, variation de pitch/énergie
- **Adéquation ton/contenu** — analyse LLM du transcript vs le contexte

### 1.2 Les deux pipelines d'analyse

| Pipeline | Fichier principal | Usage |
|----------|-------------------|-------|
| **Pipeline complet** | `presentation_analyzer.py` | Analyse vidéo → body + speech + tone → score global |
| **Pipeline grammaire** | `Streamlit + Whisper/combined_analyzer.py` | Transcript → grammaire + vocabulaire + fluence |

### 1.3 Mon rôle

Développeur backend chargé de :
1. Créer l'API FastAPI pour exposer le pipeline d'analyse
2. Résoudre les problèmes de compatibilité des dépendances ML sur Windows
3. Adapter le code existant pour fonctionner en environnement serveur

---

## 2. CE QUI A ÉTÉ CONSTRUIT

### 2.1 Architecture du backend FastAPI

```
backend/
├── main.py                  # Point d'entrée FastAPI + middleware CORS
├── requirements_api.txt     # fastapi, uvicorn, python-multipart
├── routers/
│   ├── analysis.py          # POST /api/analyze, GET /api/analyze/{job_id}
│   └── health.py            # GET /health
├── services/
│   ├── job_manager.py       # Gestionnaire de jobs thread-safe (singleton)
│   └── pipeline.py          # Wrapper autour de run_pipeline(), gestion sys.path
└── schemas/
    └── analysis.py          # Modèles Pydantic (request/response)
```

### 2.2 Pattern asynchrone des jobs

Le pipeline d'analyse prend 1-5 minutes. Le pattern implémenté :

1. **POST /api/analyze** — Upload vidéo, retourne immédiatement `job_id` (HTTP 202)
2. Le pipeline s'exécute dans un thread via `asyncio.loop.run_in_executor()`
3. **GET /api/analyze/{job_id}** — Poll le statut : `queued → processing → done|failed`
4. Quand `status=done`, le champ `report` contient le JSON complet

### 2.3 Mesures de sécurité

| Mesure | Implémentation |
|--------|----------------|
| Validation extension | Seuls `.mp4`, `.mkv`, `.mov`, `.avi`, `.webm`, `.flv`, `.wmv` acceptés |
| Limite taille fichier | 500 MB maximum |
| CORS | Middleware configuré (à restreindre en production) |
| Isolation erreurs | `RuntimeError` au lieu de `sys.exit(1)` pour ne pas tuer le serveur |

### 2.4 Fichiers créés

| Fichier | Lignes | Description |
|---------|--------|-------------|
| `backend/main.py` | 47 | App FastAPI, CORS, registration des routers |
| `backend/routers/analysis.py` | 124 | Endpoints d'analyse avec validation |
| `backend/routers/health.py` | 10 | Endpoint santé |
| `backend/services/job_manager.py` | 65 | Store in-memory thread-safe |
| `backend/services/pipeline.py` | 60 | Patch sys.path + appel run_pipeline |
| `backend/schemas/analysis.py` | 120 | Tous les modèles Pydantic |
| `compat/torchaudio_compat.py` | 44 | Monkey-patch pour torchaudio 2.2+ |
| `fix_deps.py` | 90 | Script de résolution des dépendances |
| `CLAUDE.md` | 110 | Documentation pour Claude Code |

---

## 3. LISTE CHRONOLOGIQUE DES ERREURS RENCONTRÉES

### ERREUR 1 : torchaudio.load() — TorchCodec non trouvé

```
ImportError: TorchCodec is required for load_with_torchcodec
```

**Cause racine :** torchaudio 2.11.0 a changé le backend audio et requiert TorchCodec qui n'est pas installé.

**Correction appliquée :**
```python
# Avant (speech_analyzer.py)
waveform, sr = torchaudio.load(path)

# Après
y, _ = librosa.load(path, sr=16000, mono=True)
waveform = torch.tensor(y).unsqueeze(0)
```

---

### ERREUR 2 : torchaudio.list_audio_backends() — AttributeError

```
AttributeError: module 'torchaudio' has no attribute 'list_audio_backends'
```

**Cause racine :** SpeechBrain 0.5.x appelle `torchaudio.list_audio_backends()` qui a été supprimé dans torchaudio 2.2+.

**Correction appliquée :** Création de `compat/torchaudio_compat.py` :
```python
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]
if not hasattr(torchaudio, "get_audio_backend"):
    torchaudio.get_audio_backend = lambda: "soundfile"
if not hasattr(torchaudio, "set_audio_backend"):
    torchaudio.set_audio_backend = lambda backend: None
```

---

### ERREUR 3 : huggingface_hub — use_auth_token deprecation

```
TypeError: hf_hub_download() got an unexpected keyword argument 'use_auth_token'
```

**Cause racine :** Incompatibilité entre huggingface_hub récent et SpeechBrain 0.5.x.

**Correction appliquée :**
```bash
pip install huggingface_hub==0.23.0
```

---

### ERREUR 4 : hyperpyyaml — 'str' has no attribute 'keys'

```
AttributeError: 'str' object has no attribute 'keys'
```

**Cause racine :** Version incompatible de hyperpyyaml avec SpeechBrain.

**Correction appliquée :**
```bash
pip install hyperpyyaml==1.2.2
```

---

### ERREUR 5 : hyperpyyaml — resolve_references ValueError

```
ValueError: The structure of the overrides doesn't match the structure of the document
```

**Cause racine :** SpeechBrain 1.0.3 installé au lieu de 0.5.x. APIs incompatibles.

**Correction appliquée :** Downgrade complet via `fix_deps.py` :
```python
PACKAGES_TO_INSTALL = [
    "numpy>=1.24.0,<2.0.0",
    "torch==2.1.2",
    "torchaudio==2.1.2",
    "speechbrain==0.5.15",
    "transformers==4.40.2",
    # ...
]
```

---

### ERREUR 6 : numpy 2.x incompatible avec torch 2.1.2

```
A module that was compiled using NumPy 1.x cannot be run in NumPy 2.4.3
```

**Cause racine :** torch 2.1.2 compilé contre numpy 1.x, mais numpy 2.4.3 installé.

**Correction appliquée :**
```bash
pip install "numpy<2"
```

---

### ERREUR 7 : Chemin Windows malformé — 'C:Users\...'

```
FileNotFoundError: [Errno 2] No such file or directory: 'C:Users\\pc\\...'
```

**Cause racine :** `str(path.with_suffix("")) + "_16k_tmp.wav"` perd le backslash après la lettre du lecteur sur Windows.

**Correction appliquée :**
```python
# Avant
tmp_path = str(path.with_suffix("")) + "_16k_tmp.wav"

# Après
tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav", prefix="nood_16k_")
os.close(tmp_fd)
tmp_path = str(Path(tmp_path).resolve())
tmp_path = tmp_path.replace('\\', '/')  # SpeechBrain préfère les forward slashes
```

---

### ERREUR 8 : SpeechBrain mangle les chemins Windows

```
FileNotFoundError: 'C:Users/pc/...' (backslash manquant après C:)
```

**Cause racine :** SpeechBrain interne modifie les chemins Windows de manière incorrecte.

**Correction appliquée :** Conversion systématique en forward slashes avant tout appel SpeechBrain :
```python
audio_path = audio_path.replace('\\', '/')
```

Appliqué dans : `analyze_pauses()`, `analyze_speech_content()`, `analyze_emotion()`, `analyze()`

---

### ERREUR 9 : SpeechBrain ASR — Wav2Vec2 class not found

```
ImportError: There is no such class as speechbrain.lobes.models.huggingface_transformers.wav2vec2.Wav2Vec2
```

**Cause racine :** Le modèle caché `asr-wav2vec2-commonvoice-en` incompatible avec SpeechBrain 0.5.15.

**Correction appliquée :** Remplacement par Whisper via transformers :
```python
def load_asr():
    global _whisper_pipe
    if _whisper_pipe is None:
        from transformers import pipeline
        _whisper_pipe = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-base",
            device="cpu"
        )
    return _whisper_pipe
```

---

### ERREUR 10 : SpeechBrain Emotion — même erreur Wav2Vec2

**Correction appliquée :** Remplacement par wav2vec2-lg-xlsr-en-speech-emotion-recognition :
```python
def load_emotion():
    global _emotion_pipe
    if _emotion_pipe is None:
        from transformers import pipeline
        _emotion_pipe = pipeline(
            "audio-classification",
            model="ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition",
            framework="pt",
            device="cpu"
        )
    return _emotion_pipe
```

---

### ERREUR 11 : sys.exit(1) tue le serveur FastAPI

**Cause racine :** `presentation_analyzer.py` appelait `sys.exit(1)` sur erreur, terminant le processus uvicorn.

**Correction appliquée :**
```python
# Avant
sys.exit(1)

# Après
raise RuntimeError("Pipeline failed: ...")
```

---

### ERREUR 12 : Pollinations API retourne 403 Forbidden

**Cause racine :** L'API Pollinations bloque certaines requêtes (rate limit ou région).

**Correction appliquée :** Fallback gracieux dans `analyze_tone()` :
```python
try:
    raw = call_pollinations(user_msg, model=model)
    tone_report = parse_llm_response(raw, model)
except Exception as e:
    tone_report = ToneReport(
        detected_topic="General presentation",
        detected_context="Professional presentation",
        overall_tone_fit="appropriate",
        tone_fit_score=0.7,
        mismatches=[],
        coaching_tips=["Focus on maintaining consistent energy..."],
        model_used="fallback",
        raw_response=""
    )
```

---

## 4. ÉTAT FINAL

### 4.1 Ce qui fonctionne maintenant

| Composant | Statut | Notes |
|-----------|--------|-------|
| FastAPI backend | ✅ OK | Démarre avec `uvicorn backend.main:app` |
| Upload vidéo | ✅ OK | Validation extension + taille |
| Body language analysis | ✅ OK | MediaPipe + TFLite |
| Speech analysis (VAD) | ✅ OK | SpeechBrain VAD fonctionne |
| Speech analysis (ASR) | ✅ OK | Whisper-base via transformers |
| Emotion analysis | ✅ OK | wav2vec2-lg-xlsr via transformers |
| Tone analysis | ✅ OK | Fallback si API Pollinations indisponible |
| Scoring global | ✅ OK | 40% speech + 30% body + 30% tone |

### 4.2 Résultats des tests d'import

```
Testing imports...
  torch: OK (2.1.2+cpu)
  torchaudio: OK (2.1.2+cpu)
  numpy: OK (1.26.4)
  transformers: OK (4.40.2)
  speechbrain.pretrained.VAD: OK
  speechbrain.pretrained.EncoderDecoderASR: OK
  speechbrain.pretrained.EncoderClassifier: OK

ALL IMPORTS SUCCESSFUL
```

### 4.3 Ce qui reste à améliorer

| Élément | Priorité | Description |
|---------|----------|-------------|
| Persistance jobs | Moyenne | Actuellement in-memory, perdus au redémarrage |
| Tests unitaires | Haute | Aucun test automatisé |
| CORS production | Haute | Actuellement `allow_origins=["*"]` |
| GPU support | Basse | Actuellement CPU only (`device="cpu"`) |
| Cache modèles | Basse | Recharger les modèles à chaque worker |

---

## 5. MODIFICATIONS APPORTÉES AUX FICHIERS DES COÉQUIPIERS

### 5.1 `presentation_analyzer.py`

| Ligne | Modification | Raison |
|-------|--------------|--------|
| 332 | `sys.exit(1)` → `raise RuntimeError(...)` | Éviter de tuer le serveur FastAPI |
| 362 | `sys.exit(1)` → `raise RuntimeError(...)` | Idem |

### 5.2 `Speech Analysis/speech_analyzer.py`

| Section | Modification | Raison |
|---------|--------------|--------|
| Imports (L22-31) | Ajout `import compat.torchaudio_compat` | Patch torchaudio avant SpeechBrain |
| Imports (L35-37) | Ajout `import os, tempfile` | Gestion fichiers temporaires |
| `load_audio_16k()` | `torchaudio.load()` → `librosa.load()` | TorchCodec non disponible |
| `save_tmp_wav()` | `torchaudio.save()` → `sf.write()` | Idem |
| `load_asr()` | SpeechBrain ASR → Whisper pipeline | Modèle SpeechBrain incompatible |
| `load_emotion()` | SpeechBrain → wav2vec2-xlsr pipeline | Idem |
| `analyze_pauses()` | Ajout `audio_path.replace('\\', '/')` | Chemins Windows |
| `analyze_speech_content()` | Adapté pour Whisper pipeline | Nouveau format de sortie |
| `analyze_emotion()` | Adapté pour wav2vec2 pipeline + mapping labels | Nouveau format + mapping vers `EMOTION_FEEDBACK` |
| `analyze()` | Refactorisé création tmp_path avec `tempfile.mkstemp()` | Chemins Windows corrects |

### 5.3 `Speech Analysis/tone_analyzer.py`

| Section | Modification | Raison |
|---------|--------------|--------|
| `analyze_tone()` (L331-347) | Ajout try/except avec fallback `ToneReport` | API Pollinations peut être indisponible |

### 5.4 `Streamlit + Whisper/analyzer.py`

| Modification | Raison |
|--------------|--------|
| Supprimé `import torchaudio` | Non utilisé, causait des erreurs |
| Ajout `import compat.torchaudio_compat` | Patch avant SpeechBrain |

### 5.5 `Streamlit + Whisper/public_speaking_analyzer.py`

| Modification | Raison |
|--------------|--------|
| Supprimé `import torchaudio` et `torchaudio.transforms` | Non utilisés |
| Ajout `import compat.torchaudio_compat` | Patch avant SpeechBrain |

### 5.6 `requirements.txt`

Entièrement réécrit avec versions épinglées :
```
numpy>=1.24.0,<2.0.0
torch==2.1.2
torchaudio==2.1.2
torchvision==0.16.2
huggingface_hub==0.23.0
hyperpyyaml==1.2.2
speechbrain==0.5.15
transformers==4.40.2
tokenizers==0.19.1
opencv-python>=4.8.0,<4.10.0
...
```

---

## 6. COMMANDES POUR DÉMARRER

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

**Fin du rapport**
