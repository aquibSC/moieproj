# Nightreel — AI Movie Recommendation Website

A Flask + scikit-learn website that recommends movies based on **mood/vibe text search**
and **"more like this"** content similarity, with user accounts, a personal watchlist,
and star ratings.

## Stack
- **Backend:** Python, Flask
- **ML:** scikit-learn (TF-IDF vectorizer + cosine similarity) — content-based recommender
- **Database:** SQLite via Flask-SQLAlchemy (users, watchlist, ratings)
- **Auth:** Flask-Login (hashed passwords via Werkzeug)
- **Frontend:** Jinja2 templates, plain CSS, small vanilla JS (no build step, no framework)

## Project structure
```
movieproj/
├── app.py                 # Flask app + all routes
├── models.py               # User, WatchlistItem, Rating (SQLAlchemy)
├── recommender.py          # TF-IDF + cosine similarity engine
├── config.py                # App config (reads env vars)
├── wsgi.py                  # Production entry point
├── requirements.txt
├── data/
│   ├── build_dataset.py    # Script that generated movies.csv
│   └── movies.csv           # 72 curated movies (title, genres, keywords, overview, ...)
├── templates/                # Jinja2 HTML
└── static/
    ├── css/style.css
    └── js/main.js
```

## How the recommender works
Each movie's genres, keywords, overview, director and cast are combined into one text
"soup" (genres/keywords repeated 3x so they carry more weight than free text). A
`TfidfVectorizer` turns every movie into a weighted vector; `cosine_similarity` then
compares vectors:
- **Mood search** (`/mood`) vectorizes your typed sentence with the *same* fitted
  vectorizer and ranks every movie by similarity to it — so "slow and rainy heartbreak"
  surfaces melancholic dramas even though no movie has that exact phrase.
- **"More like this"** (on a movie page) compares that movie's vector against every
  other movie and returns the closest matches.

## Run locally

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) regenerate the movie dataset
python data/build_dataset.py

# 4. Run the dev server
python app.py
```

Visit `http://127.0.0.1:5000`. The SQLite database (`app.db`) is created automatically
on first run.

### Adding more movies
Edit the `MOVIES` list in `data/build_dataset.py` and re-run it — no code changes needed
elsewhere. Since it's content-based, adding more movies never requires retraining a model
in the ML sense; the TF-IDF matrix just rebuilds at app startup.

---

## Deploying (step by step)

Below are two paths: **PythonAnywhere** (simplest, free tier, good for students/demos)
and **Render** (also free tier, slightly more "real" production setup with gunicorn).
Pick one.

### Option A — PythonAnywhere

1. **Create a free account** at pythonanywhere.com.
2. **Upload your code.** Easiest way: zip the project, then in PythonAnywhere open a
   **Bash console** and run:
   ```bash
   # after uploading nightreel.zip via the Files tab
   unzip nightreel.zip -d nightreel
   cd nightreel
   ```
3. **Create a virtualenv and install dependencies** (from the same Bash console):
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 nightreel-env
   pip install -r requirements.txt
   ```
4. **Generate the dataset** (already included as `data/movies.csv`, but if you edited it):
   ```bash
   python data/build_dataset.py
   ```
5. **Create the web app:** Go to the **Web** tab → **Add a new web app** → choose
   **Manual configuration** → Python 3.10.
6. **Point it at your virtualenv:** in the Web tab, under "Virtualenv", enter the path
   PythonAnywhere gives you for `nightreel-env` (usually
   `/home/yourusername/.virtualenvs/nightreel-env`).
7. **Edit the WSGI file:** click the WSGI configuration file link on the Web tab and
   replace its contents with:
   ```python
   import sys
   path = '/home/yourusername/nightreel'
   if path not in sys.path:
       sys.path.append(path)

   from app import app as application
   ```
8. **Set the working directory / static files mapping** (Web tab):
   - Source code: `/home/yourusername/nightreel`
   - Static files: URL `/static/` → Directory `/home/yourusername/nightreel/static/`
9. **Set a real SECRET_KEY.** On the Web tab, under "Environment variables" (or by
   editing `config.py` directly), set `SECRET_KEY` to a long random string instead of
   the dev default.
10. Click **Reload** on the Web tab. Your site is live at `yourusername.pythonanywhere.com`.

### Option B — Render.com (gunicorn-based, closer to "real" production)

1. Push this project to a **GitHub repository**.
2. Create a free account at render.com → **New +** → **Web Service** → connect your repo.
3. Configure:
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn wsgi:app`
4. Under **Environment**, add an environment variable `SECRET_KEY` set to a long random
   string.
5. Click **Create Web Service**. Render builds and deploys automatically; you get a
   `yourapp.onrender.com` URL. Every future `git push` redeploys automatically.

Note: Render's free tier uses ephemeral disk, so the SQLite file resets on redeploy/
restart. Fine for a demo/portfolio project; for persistent user data long-term, swap
`DATABASE_URL` in `config.py` for a managed Postgres database (Render offers a free
Postgres instance you can connect via the same `DATABASE_URL` env var — SQLAlchemy
handles both with no code changes).

### Either option — pre-flight checklist
- [ ] `SECRET_KEY` is set to something random, not the `dev-secret...` default
- [ ] `requirements.txt` is up to date (`pip freeze > requirements.txt` if you added packages)
- [ ] `data/movies.csv` is committed/uploaded (the app reads it at startup)
- [ ] Static files (`/static/css`, `/static/js`) are actually served (test a page's styling after deploy)
