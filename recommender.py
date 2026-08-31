"""
recommender.py
----------------
Content-based movie recommendation engine using TF-IDF + cosine similarity.

Two modes:
  1. similar_to(title, n)   -> "more like this" for a given movie
  2. recommend_for_mood(text, n) -> free-text mood/vibe search against the corpus

Both work off the same TF-IDF matrix, built once at import time (module-level
cache) so we don't recompute it on every request.
"""
import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "movies.csv")


class Recommender:
    def __init__(self, csv_path=DATA_PATH):
        self.df = pd.read_csv(csv_path)
        self.df["soup"] = self.df.apply(self._build_soup, axis=1)

        # Custom stopwords keep genre/mood words like "dark" or "light" meaningful
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 1))
        self.tfidf_matrix = self.vectorizer.fit_transform(self.df["soup"])

        # Precompute full similarity matrix — fine at this dataset size (<5k movies).
        # For much larger datasets, compute row-by-row on demand instead.
        self.similarity_matrix = cosine_similarity(self.tfidf_matrix)

        self.title_to_index = {
            t.lower(): i for i, t in enumerate(self.df["title"])
        }

    @staticmethod
    def _build_soup(row):
        """Combine weighted fields into one text blob per movie.
        Genres and keywords are repeated to give them more weight than
        the free-text overview, cast, and director (mood-relevant fields)."""
        parts = [
            str(row["genres"]) * 3,
            str(row["keywords"]) * 3,
            str(row["overview"]),
            str(row["director"]),
            str(row["cast"]),
        ]
        return " ".join(parts).lower()

    def all_movies(self):
        return self.df.to_dict("records")

    def get_movie(self, movie_id):
        row = self.df[self.df["id"] == int(movie_id)]
        if row.empty:
            return None
        return row.iloc[0].to_dict()

    def search_titles(self, query, limit=10):
        q = query.lower().strip()
        if not q:
            return []
        matches = self.df[self.df["title"].str.lower().str.contains(q, na=False)]
        return matches.head(limit).to_dict("records")

    def similar_to(self, title, n=6):
        """Movie -> movie recommendations ('more like this')."""
        idx = self.title_to_index.get(title.lower())
        if idx is None:
            return []
        scores = list(enumerate(self.similarity_matrix[idx]))
        scores = sorted(scores, key=lambda x: x[1], reverse=True)
        scores = [s for s in scores if s[0] != idx][:n]
        results = []
        for i, score in scores:
            movie = self.df.iloc[i].to_dict()
            movie["match_score"] = round(float(score) * 100, 1)
            results.append(movie)
        return results

    def recommend_for_mood(self, mood_text, n=8):
        """Free-text 'I want something slow and rainy' -> ranked movie list.
        We vectorize the mood text with the SAME fitted vectorizer, then
        compare it against every movie's TF-IDF vector directly — this
        treats the mood description as a pseudo-document/query."""
        if not mood_text or not mood_text.strip():
            return []
        query_vec = self.vectorizer.transform([mood_text.lower()])
        sims = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        top_indices = sims.argsort()[::-1][:n]
        results = []
        for i in top_indices:
            if sims[i] <= 0:
                continue
            movie = self.df.iloc[i].to_dict()
            movie["match_score"] = round(float(sims[i]) * 100, 1)
            results.append(movie)
        return results

    def top_rated(self, n=12):
        return self.df.sort_values("rating", ascending=False).head(n).to_dict("records")


# Module-level singleton — built once when the Flask app imports this module.
engine = Recommender()
