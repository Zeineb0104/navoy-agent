"""
app.py  —  Navoy Travel Recommendation System
Streamlit app with dual mode: Offline (seedData.json) + Live Neo4j toggle.
"""

import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ── page config ────────────────────────────────────────────────
st.set_page_config(
    page_title="Navoy – Travel Recommender",
    page_icon="🧳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── load seed data once ────────────────────────────────────────
@st.cache_data
def load_seed_data() -> list[dict]:
    seed_path = Path(__file__).parent / "seedData.json"
    with open(seed_path, "r", encoding="utf-8") as f:
        return json.load(f)

ALL_TRIPS = load_seed_data()

# Unique users from seed data
@st.cache_data
def get_seed_users() -> list[dict]:
    seen: dict[str, dict] = {}
    for ut in ALL_TRIPS:
        u = ut["user"]
        if u["id"] not in seen:
            seen[u["id"]] = u
    return list(seen.values())

SEED_USERS = get_seed_users()

SKIP_LABELS = {
    "heavy_physical": "Heavy physical exertion",
    "crowded_hotspots": "Crowded tourist hotspots",
    "loud_nightlife": "Loud nightlife & partying",
    "museums_history": "Lots of museums & history",
    "religious_sites": "Religious & sacred sites",
    "formal_dining": "Formal / long sit-down dining",
}

DEST_FLAGS = {
    "FR": "🇫🇷", "JP": "🇯🇵", "US": "🇺🇸", "IT": "🇮🇹",
    "ID": "🇮🇩", "ES": "🇪🇸", "AE": "🇦🇪", "GB": "🇬🇧",
    "AU": "🇦🇺", "MA": "🇲🇦",
}

# ── sidebar ─────────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://em-content.zobj.net/source/apple/391/luggage_1f9f3.png",
        width=60,
    )
    st.title("Navoy Recommender")
    st.markdown("---")

    mode = st.radio(
        "**Data Source**",
        ["📁 Offline — Seed Data", "🔴 Live Neo4j"],
        index=0,
    )
    st.markdown("---")

    # ── OFFLINE mode controls ──────────────────────────────────
    if mode == "📁 Offline — Seed Data":
        st.subheader("Select User")
        user_labels = [
            f"{u['id'][:8]}…  ({u.get('age_bracket','?')} · {u.get('chronotype','?')})"
            for u in SEED_USERS
        ]
        selected_idx = st.selectbox(
            "User", range(len(SEED_USERS)),
            format_func=lambda i: user_labels[i],
        )
        selected_user = SEED_USERS[selected_idx]
        neo4j_uri = neo4j_user = neo4j_pass = None

    # ── LIVE NEO4J mode controls ───────────────────────────────
    else:
        st.subheader("Neo4j Connection")
        neo4j_uri  = st.text_input("URI",      value=os.getenv("NEO4J_URI",      "bolt://localhost:7687"))
        neo4j_user = st.text_input("Username", value=os.getenv("NEO4J_USER",     "neo4j"))
        neo4j_pass = st.text_input("Password", value=os.getenv("NEO4J_PASSWORD", ""), type="password")

        col_a, col_b = st.columns([1, 1])
        with col_a:
            test_btn = st.button("🔌 Test")
        conn_ok = False
        if test_btn:
            from neo4j_mode import test_connection
            ok, msg = test_connection(neo4j_uri, neo4j_user, neo4j_pass)
            conn_ok = ok
            if ok:
                st.success(f"✅ {msg}")
            else:
                st.error(f"❌ {msg}")

        st.markdown("---")
        st.subheader("Select User ID")

        uid_source = st.radio("User ID from", ["Fetch from graph", "Enter manually"])
        if uid_source == "Fetch from graph":
            if st.button("📋 Load users"):
                from neo4j_mode import get_all_user_ids
                ids = get_all_user_ids(neo4j_uri, neo4j_user, neo4j_pass)
                st.session_state["neo4j_user_ids"] = ids
            ids_list = st.session_state.get("neo4j_user_ids", [])
            if ids_list:
                neo4j_selected_id = st.selectbox("User ID", ids_list)
            else:
                neo4j_selected_id = st.text_input("User ID", placeholder="Click 'Load users' first")
        else:
            neo4j_selected_id = st.text_input("User ID", placeholder="Paste a UUID…")

        selected_user = None

# ═══════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════
st.markdown(
    "<h1 style='text-align:center;'>🧳 Navoy — Travel Recommendation System</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align:center; color:grey;'>Collaborative filtering · Graph-based · LLM-enhanced</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ═══════════════════════════════════════════════════════════════
# OFFLINE MODE  ─  full pipeline
# ═══════════════════════════════════════════════════════════════
if mode == "📁 Offline — Seed Data":
    from recommender import get_recommendations, SKIP_CATEGORY_LABELS

    user = selected_user
    user_id = user["id"]

    # ── User profile card ──────────────────────────────────────
    with st.expander("👤 User Profile", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Age Bracket",    user.get("age_bracket",       "—"))
        c2.metric("Chronotype",     user.get("chronotype",        "—").capitalize())
        c3.metric("Planning Style", user.get("planning_style",    "—").capitalize())
        c4.metric("Splurge Pref",   user.get("splurge_preference","—").capitalize())

        skip = user.get("skipList") or []
        diet = user.get("dietaryRestrictions") or []
        home = f"{user.get('home_city','')}, {user.get('home_country','')}"

        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("🏠 **Home:**", home)
        with col2:
            st.write("🚫 **Skip list:**",
                     ", ".join(SKIP_CATEGORY_LABELS.get(s, s) for s in skip) or "None")
        with col3:
            st.write("🍽️ **Dietary:**", ", ".join(diet) or "None")
        st.write("🛡️ **Safety-first:**", "Yes" if user.get("safety_first") else "No")
        st.caption(f"User ID: `{user_id}`")

    # ── Run recommender ────────────────────────────────────────
    with st.spinner("Running recommendation engine…"):
        result = get_recommendations(user_id, ALL_TRIPS)

    user_trips = [ut for ut in ALL_TRIPS if ut["user"]["id"] == user_id]
    past_dest  = list({ut["destination"]["name"] for ut in user_trips})

    st.markdown("#### 🗺️ Past Destinations")
    if past_dest:
        st.info("  ·  ".join(past_dest))
    else:
        st.info("No past destinations recorded.")

    st.markdown("---")

    # ── Results: 3 columns ────────────────────────────────────
    col_dest, col_act, col_focus = st.columns(3)

    with col_dest:
        st.markdown("### 🌍 Recommended Destinations")
        dests = result["recommendedDestinations"]
        if dests:
            for d in dests:
                cc   = d.get("country_code", "")
                flag = DEST_FLAGS.get(cc, "🌐")
                st.markdown(
                    f"""<div style='background:#1e2a3a;padding:12px;border-radius:8px;margin-bottom:8px;'>
                    <span style='font-size:1.5rem;'>{flag}</span>
                    <strong style='font-size:1.1rem;'> {d['name']}</strong><br/>
                    <span style='color:#aaa;'>{d.get('city','')}, {d.get('country','')}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.warning("No destination recommendations yet.")

    with col_act:
        st.markdown("### 🏃 Recommended Activities")
        acts = result["recommendedActivities"]
        if acts:
            for a in acts:
                cat   = (a.get("category_id") or "").replace("_", " ").title()
                budg  = a.get("budget")
                budg_txt = f"${budg}" if budg is not None else "N/A"
                st.markdown(
                    f"""<div style='background:#1a2a1a;padding:12px;border-radius:8px;margin-bottom:8px;'>
                    <strong>{a['name']}</strong><br/>
                    <span style='color:#7ec891;'>📂 {cat}</span> &nbsp;|&nbsp;
                    <span style='color:#f0c040;'>💰 {budg_txt}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.warning("No activity recommendations yet.")

    with col_focus:
        st.markdown("### 🎯 Recommended Trip Focuses")
        focuses = result["recommendedTripFocus"]
        if focuses:
            for f in focuses:
                st.markdown(
                    f"""<div style='background:#2a1a2a;padding:12px;border-radius:8px;margin-bottom:8px;'>
                    🎯 <strong>{f['name']}</strong>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.warning("No trip-focus recommendations yet.")

    st.markdown("---")

    # ── Similar users + similarity chart ─────────────────────
    sim_users  = result["similarUsers"]
    sim_scores = result["similarityScores"]

    st.markdown(f"### 👥 Similar Users Found: **{len(sim_users)}**")

    if sim_scores:
        top_scores = sorted(sim_scores.items(), key=lambda x: x[1], reverse=True)[:15]
        labels = [uid[:8] + "…" for uid, _ in top_scores]
        values = [score for _, score in top_scores]
        df_sim = pd.DataFrame({"User (truncated ID)": labels, "Similarity Score": values})
        fig = px.bar(
            df_sim, x="Similarity Score", y="User (truncated ID)",
            orientation="h",
            color="Similarity Score",
            color_continuous_scale="teal",
            title="Top 15 Most Similar Users",
        )
        fig.update_layout(
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="white", height=420,
            yaxis={"autorange": "reversed"},
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No similar users found for this user.")


# ═══════════════════════════════════════════════════════════════
# LIVE NEO4J MODE
# ═══════════════════════════════════════════════════════════════
else:
    from neo4j_mode import get_neo4j_recommendations, get_user_profile

    st.markdown("### 🔴 Live Neo4j Mode")

    if not neo4j_uri or not neo4j_user or not neo4j_pass:
        st.warning("⚠️ Please fill in the Neo4j connection details in the sidebar.")
        st.stop()

    if not neo4j_selected_id or not neo4j_selected_id.strip():
        st.info("👈 Select or enter a User ID in the sidebar to get recommendations.")
        st.stop()

    user_id = neo4j_selected_id.strip()

    # Fetch and display user profile
    with st.spinner("Fetching user profile from Neo4j…"):
        profile = get_user_profile(neo4j_uri, neo4j_user, neo4j_pass, user_id)

    if profile:
        with st.expander("👤 User Profile (from Neo4j)", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Age Bracket",    profile.get("age_bracket",       "—") or "—")
            c2.metric("Chronotype",     str(profile.get("chronotype",    "—") or "—").capitalize())
            c3.metric("Planning Style", str(profile.get("planning_style","—") or "—").capitalize())
            c4.metric("Splurge Pref",   str(profile.get("splurge_preference","—") or "—").capitalize())
            home = f"{profile.get('home_city','') or ''}, {profile.get('home_country','') or ''}"
            st.write("🏠 **Home:**", home.strip(", ") or "—")
            st.write("🛡️ **Safety-first:**", "Yes" if profile.get("safety_first") else "No")
            st.caption(f"User ID: `{user_id}`")

    st.markdown("---")

    # Fetch recommendations
    with st.spinner("Querying Neo4j graph for recommendations…"):
        result = get_neo4j_recommendations(neo4j_uri, neo4j_user, neo4j_pass, user_id)

    if result.get("error"):
        st.error(f"❌ {result['error']}")
        st.stop()

    # Results: 3 columns
    col_dest, col_act, col_focus = st.columns(3)

    with col_dest:
        st.markdown("### 🌍 Recommended Destinations")
        dests = result.get("recommendedDestinations", [])
        if dests:
            for d in dests:
                cc   = d.get("country_code") or d.get("id", "").split("-")[-1].upper()
                flag = DEST_FLAGS.get(cc, "🌐")
                score_txt = f"  · score {d.get('score','')}" if d.get("score") else ""
                st.markdown(
                    f"""<div style='background:#1e2a3a;padding:12px;border-radius:8px;margin-bottom:8px;'>
                    <span style='font-size:1.5rem;'>{flag}</span>
                    <strong style='font-size:1.1rem;'> {d.get('name','—')}</strong><br/>
                    <span style='color:#aaa;'>{d.get('city','')}, {d.get('country','')}{score_txt}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.warning("No destination recommendations found.")

    with col_act:
        st.markdown("### 🏃 Recommended Activities")
        acts = result.get("recommendedActivities", [])
        if acts:
            for a in acts:
                cat = (a.get("category_label") or a.get("category_id") or "").replace("_", " ").title()
                budg = a.get("budget")
                budg_txt = f"${budg}" if budg is not None else "N/A"
                rel = a.get("relevanceScore")
                rel_txt = f"  · relevance {rel:.1f}" if rel else ""
                st.markdown(
                    f"""<div style='background:#1a2a1a;padding:12px;border-radius:8px;margin-bottom:8px;'>
                    <strong>{a.get('name','—')}</strong><br/>
                    <span style='color:#7ec891;'>📂 {cat}</span> &nbsp;|&nbsp;
                    <span style='color:#f0c040;'>💰 {budg_txt}</span>
                    <span style='color:#888;'>{rel_txt}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.warning("No activity recommendations found.")

    with col_focus:
        st.markdown("### 🎯 Trip Focus Preferences")
        focuses = result.get("recommendedTripFocus", [])
        cats    = result.get("topCategories", [])
        if focuses:
            for f in focuses:
                st.markdown(
                    f"""<div style='background:#2a1a2a;padding:12px;border-radius:8px;margin-bottom:8px;'>
                    🎯 <strong>{f.get('name','—')}</strong>
                    </div>""",
                    unsafe_allow_html=True,
                )
        if cats:
            st.markdown("**Top Activity Categories:**")
            for c in cats[:5]:
                st.markdown(f"  - {c}")
        if not focuses and not cats:
            st.warning("No trip focus data found for this user.")

    st.markdown("---")

    # Similar users
    sim_users = result.get("similarUsers", [])
    st.markdown(f"### 👥 Similar Users Found: **{len(sim_users)}**")
    if sim_users:
        st.write("  ·  ".join(uid[:12] + "…" for uid in sim_users))
    else:
        st.info("No similar users found for this user in Neo4j.")


# ── footer ──────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:grey;font-size:0.8rem;'>"
    "Navoy Travel Recommendation System · Built with Streamlit · "
    "Collaborative Filtering + Neo4j Graph + LLM Re-ranking</p>",
    unsafe_allow_html=True,
)


