import os
import re
from io import BytesIO
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
import pandas as pd
from transformers import pipeline
from wordcloud import WordCloud
from plotly.offline import plot
import plotly.express as px

# ─── Config ─────────────────────────────────────────────────────────────
load_dotenv()
NEWS_API_KEY  = os.getenv("NEWS_API_KEY")
NEWS_ENDPOINT = "https://newsapi.org/v2/everything"

# ─── App Init & SQLite ───────────────────────────────────────────────────
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"]        = "sqlite:///sentiments.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ─── Model ───────────────────────────────────────────────────────────────
class Article(db.Model):
    id           = db.Column(db.Integer,   primary_key=True)
    # keep the actual column name "query" but map to Python attr "search_query"
    search_query = db.Column("query", db.String(100), nullable=False)
    text         = db.Column(db.Text,       nullable=False)
    emotion      = db.Column(db.String(50),  nullable=False)
    sentiment    = db.Column(db.String(20),  nullable=False)
    created      = db.Column(db.DateTime,    default=datetime.utcnow)

with app.app_context():
    db.create_all()

# ─── Jinja helper ──────────────────────────────────────────────────────
@app.context_processor
def inject_now():
    return {"now": datetime.utcnow}

# ─── Sentiment pipeline ─────────────────────────────────────────────────
sentiment_pipeline = pipeline(
    "sentiment-analysis",
    model="j-hartmann/emotion-english-distilroberta-base"
)

# ─── Helpers ───────────────────────────────────────────────────────────
def fetch_news(query):
    params = {
        "q": query,
        "apiKey": NEWS_API_KEY,
        "language": "en",
        "pageSize": 50
    }
    resp = requests.get(NEWS_ENDPOINT, params=params)
    articles = resp.json().get("articles", [])
    return [
        f"{a.get('title','')} {a.get('description','')}".strip()
        for a in articles
        if a.get("description")
    ]

def clean_text(text):
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"@[A-Za-z0-9_]+", "", text)
    text = re.sub(r"#[A-Za-z0-9_]+", "", text)
    return text.strip()

# ─── Update Endpoint ───────────────────────────────────────────────────
@app.route("/update", methods=["POST"])
def update_cell():
    try:
        data  = request.get_json(force=True)
        id_   = int(data.get("id"))
        field = data.get("field")
        val   = data.get("value", "").strip()

        if field not in ("Emotion", "Sentiment"):
            return jsonify(success=False, error="Invalid field"), 400

        art = db.session.get(Article, id_)
        if not art:
            return jsonify(success=False, error="Not found"), 404

        setattr(art, field.lower(), val)
        db.session.commit()
        return jsonify(success=True)

    except Exception as e:
        app.logger.error("Update failed", exc_info=e)
        return jsonify(success=False, error=str(e)), 500

# ─── Main Route ────────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def index():
    results = {}

    # ── History lookup via GET
    history_q = request.args.get("history_query", "").strip()
    if history_q:
        rows = Article.query.filter(Article.search_query.contains(history_q)).all()
        if not rows:
            results["history_error"] = f"No records for '{history_q}'."
            return render_template("index.html", **results)

        df = pd.DataFrame([{
            "Text":      r.text,
            "Emotion":   r.emotion,
            "Sentiment": r.sentiment
        } for r in rows])

        # mapping & chart logic (unchanged)…
        mapping = {
            "joy": "Positive", "excitement": "Positive",
            "anger": "Negative", "sadness": "Negative",
            "fear": "Negative",  "neutral": "Neutral"
        }
        sentiment_counts = df["Sentiment"].value_counts()
        emotion_counts   = {k: 0 for k in mapping}
        for e in df["Emotion"]:
            if e in emotion_counts:
                emotion_counts[e] += 1
        emo_df = (
            pd.DataFrame.from_dict(emotion_counts, orient="index", columns=["Count"])
              .reset_index().rename(columns={"index": "Emotion"})
        )

        pie_div = plot(
            px.pie(names=sentiment_counts.index,
                   values=sentiment_counts.values,
                   title="Sentiment Distribution (History)"),
            output_type="div", include_plotlyjs="cdn"
        )
        bar_div = plot(
            px.bar(emo_df, x="Emotion", y="Count",
                   title="Emotion Breakdown (History)",
                   color="Emotion"),
            output_type="div", include_plotlyjs=False
        )
        emo_pie_div = plot(
            px.pie(emo_df, names="Emotion", values="Count",
                   title="Emotion Distribution (History)"),
            output_type="div", include_plotlyjs=False
        )

        wc = WordCloud(width=1200, height=400, background_color="white")
        wc_img = wc.generate(" ".join(df["Text"]))
        buf = BytesIO(); wc_img.to_image().save(buf, format="PNG"); buf.seek(0)
        os.makedirs("static/images", exist_ok=True)
        with open("static/images/wordcloud.png", "wb") as f:
            f.write(buf.read())

        results.update({
            "show_results":      True,
            "query":             history_q,
            "overall_sentiment": sentiment_counts.idxmax(),
            "key_emotions":      {k: v for k, v in emotion_counts.items() if v},
            "pie_div":           pie_div,
            "bar_div":           bar_div,
            "emo_pie_div":       emo_pie_div,
            "table": [
                {"ID": r.id, "Text": r.text, "Emotion": r.emotion, "Sentiment": r.sentiment}
                for r in rows
            ]
        })
        return render_template("index.html", **results)

    # ── Live fetch & analyze via POST
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        texts = fetch_news(query)
        cleaned = [clean_text(t) for t in texts]
        if not cleaned:
            results["error"] = "No articles found."
            return render_template("index.html", **results)

        emo_results = sentiment_pipeline(cleaned)
        labels      = [r["label"] for r in emo_results]
        df          = pd.DataFrame({"Text": cleaned, "Emotion": labels})

        mapping = {
            "joy": "Positive", "excitement": "Positive",
            "anger": "Negative", "sadness": "Negative",
            "fear": "Negative",  "neutral": "Neutral"
        }
        df["Sentiment"] = df["Emotion"].map(lambda e: mapping.get(e, "Neutral"))
        sentiment_counts = df["Sentiment"].value_counts()

        emotion_counts = {k: 0 for k in mapping}
        for e in labels:
            if e in emotion_counts:
                emotion_counts[e] += 1
        emo_df = (
            pd.DataFrame.from_dict(emotion_counts, orient="index", columns=["Count"])
              .reset_index().rename(columns={"index": "Emotion"})
        )

        pie_div = plot(
            px.pie(names=sentiment_counts.index,
                   values=sentiment_counts.values,
                   title="Sentiment Distribution"),
            output_type="div", include_plotlyjs="cdn"
        )
        bar_div = plot(
            px.bar(emo_df, x="Emotion", y="Count",
                   title="Emotion Breakdown", color="Emotion"),
            output_type="div", include_plotlyjs=False
        )
        emo_pie_div = plot(
            px.pie(emo_df, names="Emotion", values="Count",
                   title="Emotion Distribution"),
            output_type="div", include_plotlyjs=False
        )

        wc = WordCloud(width=1200, height=400, background_color="white")
        wc_img = wc.generate(" ".join(cleaned))
        buf = BytesIO(); wc_img.to_image().save(buf, format="PNG"); buf.seek(0)
        os.makedirs("static/images", exist_ok=True)
        with open("static/images/wordcloud.png", "wb") as f:
            f.write(buf.read())

        # persist with search_query=
        articles = []
        for _, row in df.iterrows():
            art = Article(
                search_query = query,
                text         = row["Text"],
                emotion      = row["Emotion"],
                sentiment    = row["Sentiment"]
            )
            db.session.add(art)
            articles.append(art)
        db.session.commit()

        results.update({
            "show_results":      True,
            "query":             query,
            "overall_sentiment": sentiment_counts.idxmax(),
            "key_emotions":      {k: v for k, v in emotion_counts.items() if v},
            "pie_div":           pie_div,
            "bar_div":           bar_div,
            "emo_pie_div":       emo_pie_div,
            "table": [
                {"ID": art.id, "Text": art.text, "Emotion": art.emotion, "Sentiment": art.sentiment}
                for art in articles
            ]
        })

    return render_template("index.html", **results)


if __name__ == "__main__":
    app.run(debug=True)
