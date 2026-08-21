# 🧳 Navoy — Travel Recommendation System (Streamlit)

A fully interactive Streamlit app that demonstrates the Navoy hyper-personalization
recommendation engine — supporting both **offline (seed data)** and **live Neo4j** modes.

---

## 📁 Project Structure

```
navoy-streamlit/
├── app.py              ← Main Streamlit UI
├── recommender.py      ← Python port of recommender.ts (collaborative filtering)
├── neo4j_mode.py       ← Live Neo4j Cypher query module
├── seedData.json       ← Pre-generated data (100+ users, copied from navoy-agent)
├── requirements.txt    ← Python dependencies
├── .env.example        ← Template for local Neo4j credentials
└── README.md
```

---

## 🚀 Run Locally

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. (Optional) Configure Neo4j for live mode
```bash
cp .env.example .env
# Edit .env and fill in your NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
```

### 3. Run the app
```bash
streamlit run app.py
```

The app opens at **http://localhost:8501**

---

## 🌐 Deploy on Streamlit Cloud (Free)

1. Push this folder to a **GitHub repository**
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select your GitHub repo → branch → set **Main file path** to `app.py`
4. Click **Deploy**
5. Your app is live at `https://your-app-name.streamlit.app`

### Adding Neo4j secrets on Streamlit Cloud
In your app's **Settings → Secrets**, add:
```toml
NEO4J_URI = "neo4j+s://xxxx.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your_aura_password"
```

---

## 🧠 How It Works

### Offline Mode (Seed Data)
- Loads `seedData.json` (103 users, ~200 trips)
- Runs the **collaborative filtering** engine (`recommender.py`) — a faithful Python port of `recommender.ts`
- Scores users by:
  - Shared destinations (+3), trip focuses (+2), activity categories (+1)
  - Profile attributes: chronotype, age bracket, splurge preference, planning style (+1–2 each)
  - Shared dietary restrictions & skip list overlap
- Returns: Recommended **Destinations**, **Activities**, **Trip Focuses** + similarity chart

### Live Neo4j Mode
- Connects to your Neo4j instance (local or AuraDB)
- Queries the graph using the same Cypher logic as `tripRepository.ts`:
  - `PREFERS` → TripFocus & ActivityCategory weights
  - `AVOIDS` → SkipCategory filtering
  - `LIKED / DISLIKED` → seen activity exclusion
  - `GENERATED → DESTINED_FOR` → collaborative destination recommendations
- Falls back gracefully with error messages if connection fails

---

## 📊 Recommendation Algorithm

```
User A selected
      │
      ▼
Find similar users (collaborative filtering)
  ┌─ Same destination visited?         +3
  ├─ Same trip focus/purpose?          +2
  ├─ Same preferred activity category? +1
  ├─ Same chronotype?                  +2
  ├─ Same age bracket?                 +2
  ├─ Same splurge preference?          +2
  ├─ Same planning style?              +1
  ├─ Shared skip-list items?           +1 each
  └─ Same safety_first setting?        +1
      │
      ▼
Top 5 most similar users
      │
      ├──► Destinations they visited (not yet seen by User A) → ranked by frequency
      ├──► Activities they liked (filtered by User A's avoid/dislike rules) → ranked by score
      └──► Trip focuses they have (not already in User A's history) → ranked by frequency
```
