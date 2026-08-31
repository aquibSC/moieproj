from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)

from config import Config
from models import db, User, WatchlistItem, Rating
from recommender import engine


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.login_message_category = "info"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    with app.app_context():
        db.create_all()

    # ---------- helpers ----------
    def get_user_rating_map():
        """{movie_id: stars} for the logged-in user, for star display."""
        if not current_user.is_authenticated:
            return {}
        rows = Rating.query.filter_by(user_id=current_user.id).all()
        return {r.movie_id: r.stars for r in rows}

    def get_user_watchlist_ids():
        if not current_user.is_authenticated:
            return set()
        rows = WatchlistItem.query.filter_by(user_id=current_user.id).all()
        return {w.movie_id for w in rows}

    # ---------- routes ----------
    @app.route("/")
    def index():
        top_movies = engine.top_rated(12)
        return render_template(
            "index.html",
            movies=top_movies,
            watchlist_ids=get_user_watchlist_ids(),
        )

    @app.route("/mood", methods=["GET", "POST"])
    def mood():
        mood_text = request.values.get("mood_text", "").strip()
        results = engine.recommend_for_mood(mood_text, n=9) if mood_text else []
        return render_template(
            "results.html",
            mood_text=mood_text,
            movies=results,
            watchlist_ids=get_user_watchlist_ids(),
        )

    @app.route("/search")
    def search():
        q = request.args.get("q", "").strip()
        results = engine.search_titles(q, limit=12) if q else []
        return render_template(
            "results.html",
            mood_text=None,
            search_query=q,
            movies=results,
            watchlist_ids=get_user_watchlist_ids(),
        )

    @app.route("/movie/<int:movie_id>")
    def movie_detail(movie_id):
        movie = engine.get_movie(movie_id)
        if not movie:
            flash("Movie not found.", "warning")
            return redirect(url_for("index"))

        similar = engine.similar_to(movie["title"], n=6)
        rating_map = get_user_rating_map()
        return render_template(
            "movie_detail.html",
            movie=movie,
            similar=similar,
            watchlist_ids=get_user_watchlist_ids(),
            user_rating=rating_map.get(movie_id, 0),
        )

    @app.route("/watchlist")
    @login_required
    def watchlist():
        items = WatchlistItem.query.filter_by(user_id=current_user.id).order_by(
            WatchlistItem.added_at.desc()
        ).all()
        movies = []
        for item in items:
            m = engine.get_movie(item.movie_id)
            if m:
                movies.append(m)
        return render_template(
            "watchlist.html", movies=movies, watchlist_ids=get_user_watchlist_ids()
        )

    @app.route("/watchlist/toggle/<int:movie_id>", methods=["POST"])
    @login_required
    def toggle_watchlist(movie_id):
        movie = engine.get_movie(movie_id)
        if not movie:
            return jsonify({"error": "not found"}), 404

        existing = WatchlistItem.query.filter_by(
            user_id=current_user.id, movie_id=movie_id
        ).first()

        if existing:
            db.session.delete(existing)
            db.session.commit()
            in_watchlist = False
        else:
            item = WatchlistItem(
                user_id=current_user.id, movie_id=movie_id, movie_title=movie["title"]
            )
            db.session.add(item)
            db.session.commit()
            in_watchlist = True

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"in_watchlist": in_watchlist})

        return redirect(request.referrer or url_for("index"))

    @app.route("/rate/<int:movie_id>", methods=["POST"])
    @login_required
    def rate_movie(movie_id):
        movie = engine.get_movie(movie_id)
        if not movie:
            return jsonify({"error": "not found"}), 404

        try:
            stars = int(request.form.get("stars", 0))
        except ValueError:
            stars = 0
        stars = max(1, min(5, stars))

        existing = Rating.query.filter_by(
            user_id=current_user.id, movie_id=movie_id
        ).first()

        if existing:
            existing.stars = stars
        else:
            db.session.add(Rating(
                user_id=current_user.id, movie_id=movie_id,
                movie_title=movie["title"], stars=stars,
            ))
        db.session.commit()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"stars": stars})

        return redirect(request.referrer or url_for("movie_detail", movie_id=movie_id))

    # ---------- auth ----------
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("index"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not username or not email or not password:
                flash("All fields are required.", "warning")
                return redirect(url_for("register"))

            if User.query.filter_by(username=username).first():
                flash("That username is taken.", "warning")
                return redirect(url_for("register"))

            if User.query.filter_by(email=email).first():
                flash("An account with that email already exists.", "warning")
                return redirect(url_for("register"))

            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            login_user(user)
            flash("Welcome to Nightreel!", "success")
            return redirect(url_for("index"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("index"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                flash("Logged in successfully.", "success")
                next_page = request.args.get("next")
                return redirect(next_page or url_for("index"))

            flash("Invalid username or password.", "danger")

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Logged out.", "info")
        return redirect(url_for("index"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
