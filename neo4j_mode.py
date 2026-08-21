"""
neo4j_mode.py

Live Neo4j query module for the Navoy Streamlit app.
Queries the graph using Cypher logic from tripRepository.ts.
"""

from __future__ import annotations

ACTIVITY_CATEGORY_TO_SKIP_CATEGORY: dict[str, str] = {
    "hiking": "heavy_physical", "water_sports": "heavy_physical",
    "cycling": "heavy_physical", "climbing": "heavy_physical",
    "winter_sports": "heavy_physical", "bar_hopping": "loud_nightlife",
    "nightclub": "loud_nightlife", "rooftop_drinks": "loud_nightlife",
    "beach_club": "loud_nightlife", "religious_site": "religious_sites",
    "museum": "museums_history", "historical_site": "museums_history",
    "architecture": "museums_history", "fine_dining": "formal_dining",
    "business_dining": "formal_dining", "theme_park": "crowded_hotspots",
    "water_park": "crowded_hotspots", "festival": "crowded_hotspots",
    "trade_show": "crowded_hotspots",
}


def test_connection(uri: str, user: str, password: str) -> tuple[bool, str]:
    """Test Neo4j connectivity. Returns (success, message)."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        driver.close()
        return True, "Connected successfully"
    except Exception as e:
        return False, str(e)


def get_all_user_ids(uri: str, user: str, password: str) -> list[str]:
    """Fetch all User IDs from the graph."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run(
                "MATCH (u:User) RETURN coalesce(u.id, u.user_id) AS uid LIMIT 200"
            )
            ids = [r["uid"] for r in result if r["uid"]]
        driver.close()
        return ids
    except Exception:
        return []


def get_user_profile(uri: str, user: str, password: str, user_id: str) -> dict:
    """Fetch a user's profile from Neo4j."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run(
                """
                MATCH (u:User) WHERE u.id = $uid OR u.user_id = $uid
                RETURN u.id AS id, u.user_id AS user_id,
                       u.age_bracket AS age_bracket,
                       u.chronotype AS chronotype,
                       u.planning_style AS planning_style,
                       u.splurge_preference AS splurge_preference,
                       u.safety_first AS safety_first,
                       u.home_city AS home_city,
                       u.home_country AS home_country
                LIMIT 1
                """,
                {"uid": user_id},
            )
            record = result.single()
            if record:
                return dict(record)
        driver.close()
    except Exception:
        pass
    return {}


def get_neo4j_recommendations(uri: str, user: str, password: str, user_id: str) -> dict:
    """Query Neo4j for recommendations."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(uri, auth=(user, password))
        session = driver.session()

        # Check user exists
        exists_res = session.run(
            "MATCH (u:User) WHERE u.id = $uid OR u.user_id = $uid RETURN count(u) AS c",
            {"uid": user_id},
        )
        if (exists_res.single() or {}).get("c", 0) == 0:
            session.close(); driver.close()
            return {"error": f"User '{user_id}' not found in Neo4j."}

        # Top TripFocus preferences
        focus_rows = list(session.run(
            "MATCH (u:User) WHERE u.id=$uid OR u.user_id=$uid "
            "MATCH (u)-[p:PREFERS]->(f:TripFocus) WHERE coalesce(p.weight,0)>0 "
            "RETURN f.id AS focusId, f.name AS focusName ORDER BY coalesce(p.weight,0) DESC",
            {"uid": user_id},
        ))
        focus_ids   = [r["focusId"]   for r in focus_rows]
        focus_names = [r["focusName"] for r in focus_rows]

        # Top ActivityCategory preferences
        cat_rows = list(session.run(
            "MATCH (u:User) WHERE u.id=$uid OR u.user_id=$uid "
            "MATCH (u)-[p:PREFERS]->(c:ActivityCategory) WHERE coalesce(p.weight,0)>0 "
            "RETURN c.id AS categoryId, coalesce(c.label,c.id) AS categoryLabel "
            "ORDER BY coalesce(p.weight,0) DESC",
            {"uid": user_id},
        ))
        cat_ids    = [r["categoryId"]    for r in cat_rows]
        cat_labels = [r["categoryLabel"] for r in cat_rows]

        # Seen / disliked activity IDs
        seen_res = session.run(
            "MATCH (u:User) WHERE u.id=$uid OR u.user_id=$uid "
            "OPTIONAL MATCH (u)-[:GENERATED]->(:Trip)-[:INCLUDES]->(ia:Activity) "
            "OPTIONAL MATCH (u)-[:DISLIKED]->(da:Activity) "
            "RETURN collect(DISTINCT ia.id)+collect(DISTINCT da.id) AS seenIds",
            {"uid": user_id},
        )
        seen_ids = [i for i in ((seen_res.single() or {}).get("seenIds") or []) if i]

        # Avoided skip categories
        avoids_res = session.run(
            "MATCH (u:User) WHERE u.id=$uid OR u.user_id=$uid "
            "MATCH (u)-[av:AVOIDS]->(sc:SkipCategory) WHERE coalesce(av.weight,0)>0 "
            "RETURN collect(DISTINCT sc.id) AS avoided",
            {"uid": user_id},
        )
        avoided_cats = (avoids_res.single() or {}).get("avoided") or []

        recommended_destinations = _query_destinations(session, user_id)
        recommended_activities = _query_activities(
            session, user_id, focus_ids, cat_ids, seen_ids, avoided_cats
        )
        similar_users = _query_similar_users(session, user_id)

        session.close(); driver.close()

        return {
            "recommendedDestinations": recommended_destinations,
            "recommendedActivities":   recommended_activities,
            "recommendedTripFocus":    [{"name": n} for n in focus_names[:3]],
            "topCategories":           cat_labels,
            "similarUsers":            similar_users,
            "error": None,
        }
    except Exception as exc:
        return {"error": str(exc)}


def _query_destinations(session, user_id: str) -> list[dict]:
    res = session.run(
        """
        MATCH (u:User) WHERE u.id=$uid OR u.user_id=$uid
        MATCH (u)-[:GENERATED]->(:Trip)-[:DESTINED_FOR]->(myD:Destination)
        WITH u, collect(DISTINCT myD.id) AS myDestIds
        MATCH (other:User)-[:GENERATED]->(:Trip)-[:DESTINED_FOR]->(d:Destination)
        WHERE other.id <> u.id AND NOT d.id IN myDestIds
        RETURN d.id AS destId, d.name AS destName,
               d.country AS country, d.city AS city, count(*) AS score
        ORDER BY score DESC LIMIT 5
        """,
        {"uid": user_id},
    )
    return [
        {"id": r["destId"], "name": r["destName"],
         "country": r["country"], "city": r["city"], "score": r["score"]}
        for r in res
    ]


def _query_activities(
    session, user_id: str,
    focus_ids: list, cat_ids: list,
    seen_ids: list, avoided_cats: list,
) -> list[dict]:
    if not focus_ids and not cat_ids:
        return []
    res = session.run(
        """
        MATCH (a:Activity) WHERE coalesce(a.recommendable,true)=true
        OPTIONAL MATCH (a)-[:HAS_FOCUS]->(f:TripFocus)
        OPTIONAL MATCH (a)-[:IN_CATEGORY]->(c:ActivityCategory)
        WITH a, f, c
        WHERE ((f.id IN $focusIds AND f.id IS NOT NULL)
            OR (c.id IN $catIds   AND c.id IS NOT NULL))
          AND NOT a.id IN $seenIds
        OPTIONAL MATCH (u:User) WHERE u.id=$uid OR u.user_id=$uid
        OPTIONAL MATCH (u)-[pf:PREFERS]->(f)
        OPTIONAL MATCH (u)-[pc:PREFERS]->(c)
        WITH a, c, coalesce(pf.weight,0)+coalesce(pc.weight,0) AS rel
        RETURN a.id AS activityId, a.name AS activityName,
               a.category_id AS categoryId,
               coalesce(c.label, a.category_id) AS categoryLabel,
               a.trip_focus_id AS tripFocusId,
               a.budget AS budget, a.address AS address, rel AS relevanceScore
        ORDER BY relevanceScore DESC, activityName LIMIT 20
        """,
        {"uid": user_id, "focusIds": focus_ids,
         "catIds": cat_ids, "seenIds": seen_ids},
    )
    activities = []
    for r in res:
        mapped = ACTIVITY_CATEGORY_TO_SKIP_CATEGORY.get(r["categoryId"] or "", "")
        if mapped and mapped in avoided_cats:
            continue
        activities.append({
            "id": r["activityId"], "name": r["activityName"],
            "category_id": r["categoryId"],
            "category_label": r["categoryLabel"],
            "trip_focus_id": r["tripFocusId"],
            "budget": r["budget"], "address": r["address"],
            "relevanceScore": r["relevanceScore"],
        })
    return activities[:10]


def _query_similar_users(session, user_id: str) -> list[str]:
    res = session.run(
        """
        MATCH (u:User) WHERE u.id=$uid OR u.user_id=$uid
        MATCH (u)-[:GENERATED]->(:Trip)-[:DESTINED_FOR]->(d:Destination)
              <-[:DESTINED_FOR]-(:Trip)<-[:GENERATED]-(other:User)
        WHERE other.id <> u.id
        RETURN coalesce(other.id, other.user_id) AS otherId, count(*) AS overlap
        ORDER BY overlap DESC LIMIT 10
        """,
        {"uid": user_id},
    )
    return [r["otherId"] for r in res if r["otherId"]]


