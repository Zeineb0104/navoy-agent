"""
recommender.py

Python port of the navoy-agent collaborative filtering recommender.
Exact translation of recommender.ts logic.
Works on the UserTrip[] data from seedData.json.
"""

from __future__ import annotations

# ============================================================
# Category -> SkipCategory mapping  (same as recommender.ts)
# ============================================================
CATEGORY_TO_SKIP_CATEGORY: dict[str, str] = {
    "hiking": "heavy_physical",
    "water_sports": "heavy_physical",
    "cycling": "heavy_physical",
    "climbing": "heavy_physical",
    "winter_sports": "heavy_physical",
    "bar_hopping": "loud_nightlife",
    "nightclub": "loud_nightlife",
    "rooftop_drinks": "loud_nightlife",
    "beach_club": "loud_nightlife",
    "religious_site": "religious_sites",
    "museum": "museums_history",
    "historical_site": "museums_history",
    "architecture": "museums_history",
    "fine_dining": "formal_dining",
    "business_dining": "formal_dining",
    "theme_park": "crowded_hotspots",
    "water_park": "crowded_hotspots",
    "festival": "crowded_hotspots",
    "trade_show": "crowded_hotspots",
}

SKIP_CATEGORY_LABELS: dict[str, str] = {
    "heavy_physical": "Heavy physical exertion",
    "crowded_hotspots": "Crowded tourist hotspots",
    "loud_nightlife": "Loud nightlife & partying",
    "museums_history": "Lots of museums & history",
    "religious_sites": "Religious & sacred sites",
    "formal_dining": "Formal / long sit-down dining",
}


# ============================================================
# Helpers
# ============================================================

def _get_user_trips(user_id: str, all_trips: list[dict]) -> list[dict]:
    return [ut for ut in all_trips if ut["user"]["id"] == user_id]


def _get_user(user_id: str, all_trips: list[dict]) -> dict | None:
    for ut in all_trips:
        if ut["user"]["id"] == user_id:
            return ut["user"]
    return None


# ============================================================
# Profile-based similarity (same weights as recommender.ts)
# ============================================================

def _profile_similarity_score(user_a: dict, user_b: dict) -> float:
    score = 0.0
    if user_a.get("chronotype") and user_a.get("chronotype") == user_b.get("chronotype"):
        score += 2
    if user_a.get("splurge_preference") and user_a.get("splurge_preference") == user_b.get("splurge_preference"):
        score += 2
    if user_a.get("planning_style") and user_a.get("planning_style") == user_b.get("planning_style"):
        score += 1
    if user_a.get("age_bracket") and user_a.get("age_bracket") == user_b.get("age_bracket"):
        score += 2
    skip_a = set(user_a.get("skipList") or [])
    skip_b = set(user_b.get("skipList") or [])
    score += len(skip_a & skip_b)
    if user_a.get("safety_first") is not None and user_a.get("safety_first") == user_b.get("safety_first"):
        score += 1
    diet_a = set(user_a.get("dietaryRestrictions") or [])
    diet_b = set(user_b.get("dietaryRestrictions") or [])
    score += len(diet_a & diet_b)
    return score


# ============================================================
# Find Similar Users  (top-5 by combined behaviour + profile)
# ============================================================

def find_similar_users(user_id: str, all_trips: list[dict]) -> list[str]:
    user_trips = _get_user_trips(user_id, all_trips)
    user = _get_user(user_id, all_trips)
    if not user:
        return []

    user_dest_ids     = {ut["destination"]["id"] for ut in user_trips}
    user_purpose_ids  = {p["id"] for ut in user_trips for p in ut.get("purposes", [])}
    user_category_ids = {c["id"] for ut in user_trips for c in ut.get("preferredCategories", [])}

    similarity_scores: dict[str, float] = {}
    for ut in all_trips:
        if ut["user"]["id"] == user_id:
            continue
        score = 0.0
        if ut["destination"]["id"] in user_dest_ids:
            score += 3
        for purpose in ut.get("purposes", []):
            if purpose["id"] in user_purpose_ids:
                score += 2
        for category in ut.get("preferredCategories", []):
            if category["id"] in user_category_ids:
                score += 1
        score += _profile_similarity_score(user, ut["user"])
        if score > 0:
            uid = ut["user"]["id"]
            similarity_scores[uid] = similarity_scores.get(uid, 0) + score

    sorted_users = sorted(similarity_scores.items(), key=lambda x: x[1], reverse=True)
    return [uid for uid, _ in sorted_users[:5]]


def get_similarity_scores(user_id: str, all_trips: list[dict]) -> dict[str, float]:
    """Return raw similarity scores for ALL comparable users (used for chart)."""
    user_trips = _get_user_trips(user_id, all_trips)
    user = _get_user(user_id, all_trips)
    if not user:
        return {}
    user_dest_ids     = {ut["destination"]["id"] for ut in user_trips}
    user_purpose_ids  = {p["id"] for ut in user_trips for p in ut.get("purposes", [])}
    user_category_ids = {c["id"] for ut in user_trips for c in ut.get("preferredCategories", [])}

    similarity_scores: dict[str, float] = {}
    for ut in all_trips:
        if ut["user"]["id"] == user_id:
            continue
        score = 0.0
        if ut["destination"]["id"] in user_dest_ids:
            score += 3
        for purpose in ut.get("purposes", []):
            if purpose["id"] in user_purpose_ids:
                score += 2
        for category in ut.get("preferredCategories", []):
            if category["id"] in user_category_ids:
                score += 1
        score += _profile_similarity_score(user, ut["user"])
        if score > 0:
            uid = ut["user"]["id"]
            similarity_scores[uid] = similarity_scores.get(uid, 0) + score
    return similarity_scores


# ============================================================
# Recommend Destinations
# ============================================================

def recommend_destinations(
    user_id: str, similar_user_ids: list[str], all_trips: list[dict]
) -> list[dict]:
    user_dest_ids = {ut["destination"]["id"] for ut in _get_user_trips(user_id, all_trips)}
    similar_set = set(similar_user_ids)
    dest_scores: dict[str, dict] = {}
    for ut in all_trips:
        if ut["user"]["id"] not in similar_set:
            continue
        dest = ut["destination"]
        if dest["id"] in user_dest_ids:
            continue
        if dest["id"] in dest_scores:
            dest_scores[dest["id"]]["score"] += 1
        else:
            dest_scores[dest["id"]] = {"destination": dest, "score": 1}
    sorted_dests = sorted(dest_scores.values(), key=lambda x: x["score"], reverse=True)
    return [d["destination"] for d in sorted_dests[:3]]


# ============================================================
# Recommend Activities
# ============================================================

def recommend_activities(
    user_id: str, similar_user_ids: list[str], all_trips: list[dict]
) -> list[dict]:
    user_trips = _get_user_trips(user_id, all_trips)
    user = _get_user(user_id, all_trips)
    similar_set = set(similar_user_ids)

    user_avoided: set[str] = set(user.get("skipList") or [] if user else [])
    for ut in user_trips:
        user_avoided.update(ut.get("avoidedCategories", []))

    disliked_reasons  = {d["reason"] for ut in user_trips for d in ut.get("disliked", [])}
    user_liked_ids    = {a["id"] for ut in user_trips for a in ut.get("liked", [])}
    user_disliked_ids = {d["activity"]["id"] for ut in user_trips for d in ut.get("disliked", [])}
    activity_scores: dict[str, dict] = {}

    for ut in all_trips:
        if ut["user"]["id"] not in similar_set:
            continue
        for activity in ut.get("liked", []):
            aid = activity.get("id")
            if not aid or aid in user_liked_ids or aid in user_disliked_ids:
                continue
            cat = activity.get("category_id")
            if cat:
                mapped = CATEGORY_TO_SKIP_CATEGORY.get(cat)
                if mapped and mapped in user_avoided:
                    continue
            if not activity.get("recommendable", True):
                continue
            if "too_physical" in disliked_reasons and cat == "hiking":
                continue
            if "too_mainstream" in disliked_reasons and cat in ("museum", "historical_site", "architecture"):
                continue
            if "too_expensive" in disliked_reasons and (activity.get("budget") or 0) > 200:
                continue
            if "not_family_friendly" in disliked_reasons and cat in ("theme_park", "water_park", "zoo", "aquarium"):
                continue
            if aid in activity_scores:
                activity_scores[aid]["score"] += 2
            else:
                activity_scores[aid] = {"activity": activity, "score": 2}

    sorted_acts = sorted(activity_scores.values(), key=lambda x: x["score"], reverse=True)
    return [a["activity"] for a in sorted_acts[:5]]


# ============================================================
# Recommend Trip Focuses
# ============================================================

def recommend_trip_focuses(
    user_id: str, similar_user_ids: list[str], all_trips: list[dict]
) -> list[dict]:
    user_purpose_ids = {
        p["id"] for ut in _get_user_trips(user_id, all_trips) for p in ut.get("purposes", [])
    }
    similar_set = set(similar_user_ids)
    focus_scores: dict[str, dict] = {}
    for ut in all_trips:
        if ut["user"]["id"] not in similar_set:
            continue
        for purpose in ut.get("purposes", []):
            if purpose["id"] in user_purpose_ids:
                continue
            pid = purpose["id"]
            if pid in focus_scores:
                focus_scores[pid]["score"] += 1
            else:
                focus_scores[pid] = {"focus": purpose, "score": 1}
    sorted_focuses = sorted(focus_scores.values(), key=lambda x: x["score"], reverse=True)
    return [f["focus"] for f in sorted_focuses[:3]]


# ============================================================
# Main entry point
# ============================================================

def get_recommendations(user_id: str, all_trips: list[dict]) -> dict:
    similar_users = find_similar_users(user_id, all_trips)
    return {
        "userId": user_id,
        "recommendedDestinations": recommend_destinations(user_id, similar_users, all_trips),
        "recommendedActivities":   recommend_activities(user_id, similar_users, all_trips),
        "recommendedTripFocus":    recommend_trip_focuses(user_id, similar_users, all_trips),
        "similarUsers":            similar_users,
        "similarityScores":        get_similarity_scores(user_id, all_trips),
    }


