"""
trip_generator.py — Offline trip generation for the Navoy Streamlit app.
"""
from __future__ import annotations
import random
from datetime import date, timedelta
from recommender import CATEGORY_TO_SKIP_CATEGORY

PACE_ACTIVITIES = {"relaxed": 2, "balanced": 3, "packed": 4}

DEST_ID_MAP = {
    "paris": "paris-fr", "france": "paris-fr",
    "tokyo": "tokyo-jp", "japan": "tokyo-jp",
    "new york": "new-york-us", "usa": "new-york-us",
    "rome": "rome-it", "italy": "rome-it",
    "bali": "bali-id", "indonesia": "bali-id",
    "barcelona": "barcelona-es", "spain": "barcelona-es",
    "dubai": "dubai-ae", "uae": "dubai-ae",
    "london": "london-gb", "uk": "london-gb",
    "sydney": "sydney-au", "australia": "sydney-au",
    "marrakech": "marrakech-ma", "morocco": "marrakech-ma",
}


def _resolve_dest_id(text: str) -> str | None:
    key = text.lower().strip()
    for k, v in DEST_ID_MAP.items():
        if k in key:
            return v
    return None


def _is_blocked(act: dict, skip_set: set, dislike_reasons: set) -> bool:
    cat = act.get("category_id") or ""
    mapped = CATEGORY_TO_SKIP_CATEGORY.get(cat, "")
    if mapped and mapped in skip_set:
        return True
    if not act.get("recommendable", True):
        return True
    if "too_physical" in dislike_reasons and cat == "hiking":
        return True
    if "too_mainstream" in dislike_reasons and cat in ("museum", "historical_site", "architecture"):
        return True
    if "too_expensive" in dislike_reasons and (act.get("budget") or 0) > 200:
        return True
    return False


def _collect(all_trips, dest_id, destination, skip_set, dislike_reasons,
             require_dest=False, require_focus=False, focuses=None):
    out, seen = [], set()
    for ut in all_trips:
        d = ut.get("destination", {})
        dest_ok = (
            (dest_id and d.get("id") == dest_id)
            or destination.lower() in (d.get("name", "") + " " + d.get("country", "")).lower()
        )
        if require_dest and not dest_ok:
            continue
        for act in ut.get("activities", []):
            aid = act.get("id")
            if not aid or aid in seen:
                continue
            if _is_blocked(act, skip_set, dislike_reasons):
                continue
            if require_focus and (focuses is None or act.get("trip_focus_id") not in focuses):
                continue
            out.append(act)
            seen.add(aid)
    return out


def generate_trip(
    all_trips: list[dict],
    profile: dict,
    destination: str,
    start_date: date,
    end_date: date,
    trip_focuses: list[str],
    pace: str = "balanced",
    budget_total: float = 2000,
    adults: int = 1,
    children: int = 0,
    additional_context: str = "",
) -> dict:
    skip_set = set(profile.get("skipList") or [])
    dislike_reasons = set(profile.get("_dislike_reasons") or [])
    acts_per_day = PACE_ACTIVITIES.get(pace, 3)
    num_days = max(1, (end_date - start_date).days + 1)
    dest_id = _resolve_dest_id(destination)
    budget_per_act = (budget_total / max(1, adults + children)) / max(1, num_days * acts_per_day)

    needed = acts_per_day * num_days
    candidates = _collect(all_trips, dest_id, destination, skip_set, dislike_reasons, require_dest=True)
    existing_ids = {a["id"] for a in candidates}
    if len(candidates) < needed:
        extra = _collect(all_trips, dest_id, destination, skip_set, dislike_reasons,
                         require_focus=True, focuses=trip_focuses)
        candidates += [a for a in extra if a["id"] not in existing_ids]
        existing_ids = {a["id"] for a in candidates}
    if len(candidates) < needed:
        extra = _collect(all_trips, dest_id, destination, skip_set, dislike_reasons)
        candidates += [a for a in extra if a["id"] not in existing_ids]

    def score(act):
        s = 10.0 if act.get("trip_focus_id") in trip_focuses else 0.0
        b = act.get("budget") or 0
        if b > 0 and budget_per_act > 0:
            s -= abs(b - budget_per_act) / budget_per_act
        return s

    candidates.sort(key=score, reverse=True)
    time_slots = ["morning", "afternoon", "evening", "morning", "afternoon"]
    days, used = [], set()
    random.seed(42)

    for day_idx in range(num_days):
        day_acts = []
        for slot_idx in range(acts_per_day):
            chosen = next((a for a in candidates if a["id"] not in used), None)
            if not chosen:
                break
            used.add(chosen["id"])
            enriched = dict(chosen)
            enriched["time_slot"] = chosen.get("best_time") or time_slots[slot_idx % len(time_slots)]
            enriched["sequence"] = slot_idx + 1
            day_acts.append(enriched)
        days.append({"day": day_idx + 1, "date": start_date + timedelta(days=day_idx), "activities": day_acts})

    estimated = round(
        sum(a.get("budget", 0) for d in days for a in d["activities"]) * (adults + children), 2
    )
    return {
        "destination": destination, "start_date": start_date, "end_date": end_date,
        "days": days, "estimated_cost": estimated, "pace": pace,
        "focuses": trip_focuses, "adults": adults, "children": children,
        "additional_context": additional_context,
    }


def apply_ratings_to_profile(profile: dict, ratings: dict) -> dict:
    """Update profile skipList based on collected dislike reasons from activity ratings."""
    updated = dict(profile)
    dislike_reasons = [
        v.get("reason") for v in ratings.values()
        if v.get("rating") == "disliked" and v.get("reason")
    ]
    reason_to_skip = {
        "too_physical": "heavy_physical",
        "too_mainstream": "crowded_hotspots",
    }
    current_skip = set(updated.get("skipList") or [])
    for r in dislike_reasons:
        mapped = reason_to_skip.get(r)
        if mapped:
            current_skip.add(mapped)
    updated["skipList"] = list(current_skip)
    updated["_dislike_reasons"] = list(set(dislike_reasons))
    return updated

