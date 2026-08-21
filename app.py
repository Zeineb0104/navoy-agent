"""app.py — Navoy Travel Recommendation System (Full User Flow)"""
import json, uuid, time
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Navoy – Travel Recommender", page_icon="🧳",
                   layout="wide", initial_sidebar_state="expanded")

SKIP_LABELS = {
    "heavy_physical":  "🏋️ Heavy Physical Exertion",
    "crowded_hotspots":"👥 Crowded Tourist Hotspots",
    "loud_nightlife":  "🎉 Loud Nightlife & Partying",
    "museums_history": "🏛️ Lots of Museums & History",
    "religious_sites": "⛪ Religious & Sacred Sites",
    "formal_dining":   "🍽️ Formal / Long Sit-down Dining",
}
TRIP_FOCUS_OPTIONS = [
    ("beach_relaxation","🏖️ Beach & Relaxation"),
    ("cultural_exploration","🏛️ Cultural Exploration"),
    ("adventure_outdoors","🏔️ Adventure & Outdoors"),
    ("family_fun","👨‍👩‍👧 Family Fun"),
    ("romantic_getaway","💑 Romantic Getaway"),
    ("business_networking","💼 Business & Networking"),
    ("nightlife_social","🎉 Nightlife & Social"),
    ("food_culinary","🍜 Food & Culinary"),
    ("wellness_retreat","🧘 Wellness & Retreat"),
    ("shopping_lifestyle","🛍️ Shopping & Lifestyle"),
    ("local_authentic","🌿 Local & Authentic"),
    ("workshops_learning","📚 Workshops & Learning"),
]
FOCUS_LABEL = {fid: lbl for fid, lbl in TRIP_FOCUS_OPTIONS}
DEST_FLAGS = {"FR":"🇫🇷","JP":"🇯🇵","US":"🇺🇸","IT":"🇮🇹","ID":"🇮🇩",
              "ES":"🇪🇸","AE":"🇦🇪","GB":"🇬🇧","AU":"🇦🇺","MA":"🇲🇦"}
TIME_ICONS = {"morning":"🌅","afternoon":"☀️","evening":"🌆","night":"🌙","anytime":"🕐"}
DISLIKE_REASONS = [
    ("not_my_style","Not my style"),("too_expensive","Too expensive"),
    ("too_mainstream","Too mainstream"),("too_physical","Too physically demanding"),
    ("not_family_friendly","Not family-friendly"),("takes_too_long","Takes too long"),
]
KNOWN_DESTINATIONS = [
    "Paris, France","Tokyo, Japan","New York, USA","Rome, Italy","Bali, Indonesia",
    "Barcelona, Spain","Dubai, UAE","London, UK","Sydney, Australia","Marrakech, Morocco",
]
SCREEN_STEPS = [
    ("onboarding","1","Onboarding"),("recommendations","2","Recommendations"),
    ("trip_form","3","Plan Trip"),("generating","4","Generating"),
    ("itinerary","5","Itinerary"),("updated_recs","6","Updated Recs"),
]

@st.cache_data
def load_seed_data():
    with open(Path(__file__).parent / "seedData.json", "r", encoding="utf-8") as f:
        return json.load(f)

ALL_TRIPS = load_seed_data()

for _k, _v in {
    "screen":"onboarding","profile":{},"trip_result":None,
    "activity_ratings":{},"rec_result":None,"updated_rec_result":None,
    "user_id":str(uuid.uuid4()),"onboarding_step":1,"trip_form_data":{},
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

def go(s):
    st.session_state["screen"] = s

def card(content, bg="#1a1a2e"):
    st.markdown(
        f"<div style='background:{bg};padding:14px;border-radius:10px;"
        f"margin-bottom:8px;'>{content}</div>",
        unsafe_allow_html=True)

def render_progress():
    screen = st.session_state["screen"]
    ids = [s[0] for s in SCREEN_STEPS]
    cur = ids.index(screen) if screen in ids else 0
    cols = st.columns(len(SCREEN_STEPS))
    for i, (sid, num, lbl) in enumerate(SCREEN_STEPS):
        color = "#4CAF50" if i < cur else ("#1E90FF" if i == cur else "#444")
        cols[i].markdown(
            f"<div style='text-align:center;padding:5px;border-radius:8px;"
            f"background:{color};color:white;font-size:0.75rem;'><b>{num}</b> {lbl}</div>",
            unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

def build_vt(profile, fd, liked_acts, disliked_acts, tid="vt"):
    return {
        "user": profile,
        "trip": {"id":tid,"mongo_id":tid,"start_date":"2026-01-01T00:00:00.000Z",
                 "end_date":"2026-01-07T00:00:00.000Z","travelers_count":1,
                 "pace":"balanced","budget":2000,"currency":"USD",
                 "budget_distribution":"balanced","group_type":"solo","status":"ready"},
        "destination": {"id":tid,"name":fd.get("destination","TBD"),
                        "city":fd.get("destination","TBD"),"country":"TBD",
                        "country_code":"XX","latitude":0,"longitude":0},
        "activities": [],
        "purposes": [{"id":f,"name":FOCUS_LABEL.get(f,f),"retired":False}
                     for f in fd.get("trip_focuses",[])],
        "preferredCategories": [],
        "avoidedCategories": profile.get("skipList",[]),
        "liked": liked_acts,
        "disliked": disliked_acts,
    }

# ── sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧳 Navoy")
    st.markdown("**Travel Recommendation System**")
    st.markdown("---")
    st.markdown(f"**Session:** `{st.session_state['user_id'][:8]}…`")
    if st.session_state["screen"] not in ("onboarding", "generating"):
        if st.button("🔄 Start Over", use_container_width=True):
            st.session_state.update({
                "profile":{},"trip_result":None,"activity_ratings":{},
                "rec_result":None,"updated_rec_result":None,
                "onboarding_step":1,"trip_form_data":{},"user_id":str(uuid.uuid4())})
            go("onboarding"); st.rerun()
    st.markdown("---")
    p = st.session_state.get("profile", {})
    if p.get("chronotype"):
        st.markdown("**Your Profile**")
        st.caption(f"🕐 {p.get('chronotype','').capitalize()}")
        st.caption(f"💰 {p.get('splurge_preference','').capitalize()}")
        st.caption(f"📋 {p.get('planning_style','').capitalize()}")
        skips = [SKIP_LABELS.get(s,s) for s in (p.get("skipList") or [])]
        if skips: st.caption("🚫 " + " · ".join(skips))
    st.markdown("---"); st.caption("📁 Offline Mode — Seed Data")

# ── header ─────────────────────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — ONBOARDING
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state["screen"] == "onboarding":
    step = st.session_state.get("onboarding_step", 1)
    st.markdown(f"## 👋 Welcome to Navoy — Step {step} of 5")
    st.caption("Tell us about yourself so we can personalize your experience.")
    if step == 1:
        st.markdown("### 🕐 Q1: When do you feel most energetic?")
        ch = {"🌅 Early Bird":"early","☀️ Standard":"standard","🌙 Night Owl":"late"}
        sel = st.radio("", list(ch.keys()), index=1)
        if st.button("Next →", use_container_width=True, type="primary"):
            st.session_state["profile"]["chronotype"] = ch[sel]
            st.session_state["onboarding_step"] = 2; st.rerun()
    elif step == 2:
        st.markdown("### 💰 Q2: What do you splurge on most?")
        ch = {"🏨 Accommodation":"accommodation","🎢 Experiences":"experiences",
              "🍽️ Dining":"dining","🚕 Convenience":"convenience"}
        sel = st.radio("", list(ch.keys()))
        c1,c2 = st.columns(2)
        if c1.button("← Back",use_container_width=True): st.session_state["onboarding_step"]=1; st.rerun()
        if c2.button("Next →",use_container_width=True,type="primary"):
            st.session_state["profile"]["splurge_preference"]=ch[sel]
            st.session_state["onboarding_step"]=3; st.rerun()
    elif step == 3:
        st.markdown("### 🚫 Q3: What would you rather skip?")
        cur_skip = set(st.session_state["profile"].get("skipList") or [])
        sel_skip = []
        cols = st.columns(2)
        for i,(sid,lbl) in enumerate(SKIP_LABELS.items()):
            if cols[i%2].checkbox(lbl, value=sid in cur_skip, key=f"sk_{sid}"):
                sel_skip.append(sid)
        c1,c2 = st.columns(2)
        if c1.button("← Back",use_container_width=True): st.session_state["onboarding_step"]=2; st.rerun()
        if c2.button("Next →",use_container_width=True,type="primary"):
            st.session_state["profile"]["skipList"]=sel_skip
            st.session_state["onboarding_step"]=4; st.rerun()
    elif step == 4:
        st.markdown("### 🍽️ Q4: Dietary restrictions & about you")
        diet_opts=["vegan","vegetarian","gluten_free","halal","kosher","alcohol_free"]
        cur_diet=set(st.session_state["profile"].get("dietaryRestrictions") or [])
        sel_diet=[]
        cols=st.columns(3)
        for i,d in enumerate(diet_opts):
            if cols[i%3].checkbox(d.replace("_"," ").title(),value=d in cur_diet,key=f"dt_{d}"):
                sel_diet.append(d)
        st.markdown("---")
        c1,c2=st.columns(2)
        age_opts=["18-24","25-34","35-44","45-54","55+"]
        cur_age=st.session_state["profile"].get("age_bracket","25-34")
        age=c1.selectbox("Age bracket",age_opts,index=age_opts.index(cur_age))
        safety=c2.toggle("🛡️ Safety-first",value=st.session_state["profile"].get("safety_first",False))
        hcity=c1.text_input("🏠 Home city",value=st.session_state["profile"].get("home_city",""))
        hcountry=c2.text_input("🌍 Home country",value=st.session_state["profile"].get("home_country",""))
        b1,b2=st.columns(2)
        if b1.button("← Back",use_container_width=True): st.session_state["onboarding_step"]=3; st.rerun()
        if b2.button("Next →",use_container_width=True,type="primary"):
            st.session_state["profile"].update({"dietaryRestrictions":sel_diet,"age_bracket":age,
                "safety_first":safety,"home_city":hcity,"home_country":hcountry})
            st.session_state["onboarding_step"]=5; st.rerun()
    elif step == 5:
        st.markdown("### 🗓️ Q5: How do you prefer to plan?")
        ch={"📋 Structured":"structured","📝 Loose":"loose","🎲 Spontaneous":"spontaneous"}
        sel=st.radio("",list(ch.keys()))
        st.markdown("---")
        p=st.session_state["profile"]
        c1,c2,c3=st.columns(3)
        c1.info(f"🕐 {p.get('chronotype','—').capitalize()}")
        c2.info(f"💰 {p.get('splurge_preference','—').capitalize()}")
        c3.info(f"👤 {p.get('age_bracket','—')}")
        skip_str=" · ".join(SKIP_LABELS.get(s,s) for s in (p.get("skipList") or [])) or "None"
        st.caption(f"🚫 Skip: {skip_str}")
        b1,b2=st.columns(2)
        if b1.button("← Back",use_container_width=True): st.session_state["onboarding_step"]=4; st.rerun()
        if b2.button("✅ Get My Recommendations",use_container_width=True,type="primary"):
            from recommender import get_recommendations
            st.session_state["profile"]["planning_style"]=ch[sel]
            st.session_state["profile"]["id"]=st.session_state["user_id"]
            vt=build_vt(st.session_state["profile"],{},[],[],"vt0")
            result=get_recommendations(st.session_state["user_id"],ALL_TRIPS+[vt])
            st.session_state["rec_result"] = result
            go("recommendations"); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 2 — RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state["screen"] == "recommendations":
    result = st.session_state.get("rec_result") or {}
    p = st.session_state["profile"]
    st.markdown("## 🌍 Your Personalized Recommendations")
    st.info(f"Based on: **{p.get('chronotype','').capitalize()}** · "
            f"**{p.get('splurge_preference','').capitalize()}** · "
            f"**{p.get('planning_style','').capitalize()}**")
    cd,ca,cf = st.columns(3)
    with cd:
        st.markdown("### 🌍 Destinations")
        for d in (result.get("recommendedDestinations") or []):
            flag=DEST_FLAGS.get(d.get("country_code",""),"🌐")
            card(f"{flag} <b>{d.get('name','')}</b><br>"
                 f"<span style='color:#aaa;font-size:0.82rem;'>{d.get('city','')}, {d.get('country','')}</span>")
        if not result.get("recommendedDestinations"): st.warning("Explore any destination!")
    with ca:
        st.markdown("### 🏃 Activities")
        for a in (result.get("recommendedActivities") or []):
            cat=(a.get("category_id") or "").replace("_"," ").title()
            budg=f"${a.get('budget')}" if a.get("budget") else "N/A"
            card(f"<b>{a.get('name','')}</b><br>"
                 f"<span style='color:#7ec891;font-size:0.8rem;'>📂 {cat}</span> "
                 f"<span style='color:#f0c040;font-size:0.8rem;'>💰 {budg}</span>",bg="#1a2a1a")
        if not result.get("recommendedActivities"): st.warning("Activities on your trip!")
    with cf:
        st.markdown("### 🎯 Trip Focuses")
        for f in (result.get("recommendedTripFocus") or []):
            card(f"🎯 <b>{f.get('name','')}</b>",bg="#2a1a2a")
        if not result.get("recommendedTripFocus"): st.warning("Choose your focus below!")
    sim = result.get("similarityScores") or {}
    if sim:
        st.markdown("---"); st.markdown("### 👥 Most Similar Travelers")
        top=sorted(sim.items(),key=lambda x:x[1],reverse=True)[:12]
        df=pd.DataFrame({"User":[u[:8]+"…" for u,_ in top],"Score":[s for _,s in top]})
        fig=px.bar(df,x="Score",y="User",orientation="h",color="Score",
                   color_continuous_scale="teal",title="Similarity Scores")
        fig.update_layout(plot_bgcolor="#0e1117",paper_bgcolor="#0e1117",
                          font_color="white",height=350,
                          yaxis={"autorange":"reversed"},coloraxis_showscale=False)
        st.plotly_chart(fig,use_container_width=True)
    st.markdown("---")
    if st.button("✈️ Start Planning My Trip →",use_container_width=True,type="primary"):
        go("trip_form"); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 3 — TRIP FORM
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state["screen"] == "trip_form":
    st.markdown("## ✈️ Plan Your Trip")
    with st.form("trip_form"):
        st.markdown("### 🎯 Trip Focus *(up to 3)*")
        fc=st.columns(4); sel_foc=[]
        for i,(fid,flbl) in enumerate(TRIP_FOCUS_OPTIONS):
            if fc[i%4].checkbox(flbl,key=f"fo_{fid}"): sel_foc.append(fid)
        st.markdown("---"); st.markdown("### 📍 Destination & Dates")
        c1,c2=st.columns(2)
        dest=c1.selectbox("Destination",KNOWN_DESTINATIONS)
        today=date.today()
        sd=c1.date_input("Start Date",value=today+timedelta(days=30),min_value=today+timedelta(days=1))
        ed=c2.date_input("End Date",  value=today+timedelta(days=37),min_value=today+timedelta(days=2))
        st.markdown("---"); st.markdown("### 👥 Group & Budget")
        g1,g2,g3=st.columns(3)
        adults=g1.number_input("Adults",min_value=1,max_value=10,value=2)
        children=g2.number_input("Children",min_value=0,max_value=10,value=0)
        budget=g3.number_input("Budget (USD)",min_value=100,max_value=500000,value=3000,step=100)
        st.markdown("---"); st.markdown("### ⚙️ Trip Style")
        p1,p2=st.columns(2)
        pace=p1.selectbox("Pace",["relaxed","balanced","packed"],
            format_func=lambda x:{"relaxed":"🌿 Relaxed","balanced":"⚖️ Balanced","packed":"⚡ Packed"}[x])
        bdist=p2.selectbox("Budget Split",["accommodation_first","balanced","experiences_first"],
            format_func=lambda x:{"accommodation_first":"🏨 Accommodation First",
                                   "balanced":"⚖️ Balanced","experiences_first":"🎢 Experiences First"}[x])
        st.markdown("---")
        addl=st.text_area("🗒️ Additional Context *(optional)*",max_chars=200,
                          placeholder="e.g. We love street food, one vegan traveler.")
        submitted=st.form_submit_button("✨ Generate My Trip",use_container_width=True,type="primary")
    if submitted:
        if len(sel_foc) > 3:
            st.error("Please select at most 3 trip focuses.")
        elif sd >= ed:
            st.error("End date must be after start date.")
        else:
            st.session_state["trip_form_data"]={
                "destination":dest,"start_date":sd,"end_date":ed,
                "trip_focuses":sel_foc or ["cultural_exploration"],
                "pace":pace,"budget":float(budget),"adults":int(adults),
                "children":int(children),"budget_distribution":bdist,"additional_context":addl,
            }
            go("generating"); st.rerun()
    if st.button("← Back to Recommendations"):
        go("recommendations"); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 4 — GENERATING
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state["screen"] == "generating":
    from trip_generator import generate_trip
    fd=st.session_state.get("trip_form_data",{})
    st.markdown("## ✨ Building Your Itinerary…")
    st.markdown(f"**{fd.get('destination')}** · {fd.get('start_date')} → {fd.get('end_date')} · "
                f"{fd.get('pace','').capitalize()} pace")
    steps_txt=["🔍 Analyzing your travel profile…","🌍 Matching destination activities…",
               "🎯 Filtering by your preferences…","🏃 Building day-by-day schedule…","✅ Finalizing!"]
    prog=st.progress(0); status=st.empty()
    for i,msg in enumerate(steps_txt):
        status.markdown(f"**{msg}**"); prog.progress((i+1)*20); time.sleep(0.4)
    trip=generate_trip(
        all_trips=ALL_TRIPS,profile=st.session_state["profile"],
        destination=fd.get("destination",""),
        start_date=fd.get("start_date",date.today()),
        end_date=fd.get("end_date",date.today()+timedelta(days=3)),
        trip_focuses=fd.get("trip_focuses",[]),pace=fd.get("pace","balanced"),
        budget_total=fd.get("budget",2000),adults=fd.get("adults",1),
        children=fd.get("children",0),additional_context=fd.get("additional_context",""),
    )
    st.session_state["trip_result"]=trip; st.session_state["activity_ratings"]={}

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 5 — ITINERARY + LIKE / DISLIKE
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state["screen"] == "itinerary":
    trip=st.session_state.get("trip_result",{})
    if not trip: go("trip_form"); st.rerun()
    fd=st.session_state.get("trip_form_data",{})
    ratings=st.session_state.setdefault("activity_ratings",{})
    st.markdown(f"## 🗺️ Your Trip to **{trip.get('destination')}**")
    h1,h2,h3,h4=st.columns(4)
    h1.metric("📅 Days",f"{(trip['end_date']-trip['start_date']).days+1}")
    h2.metric("👥 Travelers",f"{trip.get('adults',1)}A + {trip.get('children',0)}C")
    h3.metric("💰 Est. Cost",f"${trip.get('estimated_cost',0):,.0f}")
    h4.metric("⚡ Pace",trip.get("pace","balanced").capitalize())
    foc_txt=" · ".join(FOCUS_LABEL.get(f,f) for f in (trip.get("focuses") or []))
    if foc_txt: st.caption(f"🎯 {foc_txt}")
    liked_n=sum(1 for r in ratings.values() if r.get("rating")=="liked")
    dis_n=sum(1 for r in ratings.values() if r.get("rating")=="disliked")
    if liked_n+dis_n>0:
        r1,r2=st.columns(2); r1.success(f"👍 {liked_n} liked"); r2.error(f"👎 {dis_n} disliked")
    st.markdown("---"); st.markdown("### 📅 Day-by-Day Itinerary")
    st.caption("Rate activities — your feedback updates your recommendations.")
    days=trip.get("days",[])
    if not days:
        st.warning("No activities generated. Try a different destination or focus.")
    else:
        tabs=st.tabs([f"Day {d['day']}  {d['date'].strftime('%b %d')}" for d in days])
        for tab,day in zip(tabs,days):
            with tab:
                st.markdown(f"#### 📆 {day['date'].strftime('%A, %B %d')}")
                for act in day.get("activities",[]):
                    aid=act.get("id","")
                    rv=ratings.get(aid,{}).get("rating")
                    cat=(act.get("category_id") or "").replace("_"," ").title()
                    budg=f"${act.get('budget')}" if act.get("budget") else "N/A"
                    ticon=TIME_ICONS.get(act.get("time_slot","anytime"),"🕐")
                    brd=("border:2px solid #4CAF50;" if rv=="liked"
                         else "border:2px solid #f44336;" if rv=="disliked" else "")
                    st.markdown(
                        f"<div style='background:#1a1a2e;padding:12px;border-radius:8px;"
                        f"margin-bottom:6px;{brd}'><b>{ticon} {act.get('name','')}</b><br>"
                        f"<span style='color:#7ec891;font-size:0.8rem;'>📂 {cat}</span> | "
                        f"<span style='color:#f0c040;font-size:0.8rem;'>💰 {budg}</span>"
                        f"</div>",unsafe_allow_html=True)
                    b1,b2,_=st.columns([1,1,4])
                    if b1.button("👍 Like",key=f"L_{aid}",
                                 type="primary" if rv=="liked" else "secondary"):
                        ratings[aid]={"rating":"liked","reason":None,"note":""}; st.rerun()
                    if b2.button("👎 Dislike",key=f"D_{aid}",
                                 type="primary" if rv=="disliked" else "secondary"):
                        ratings[aid]={"rating":"disliked","reason":None,"note":""}; st.rerun()
                    if rv=="disliked":
                        opts=[("","Select reason…")]+DISLIKE_REASONS
                        rs=st.selectbox("Why?",[o[0] for o in opts],
                                        format_func=lambda x: dict(opts).get(x,x),key=f"R_{aid}")
                        nv=st.text_input("Note (optional)",key=f"N_{aid}",
                                         value=ratings.get(aid,{}).get("note",""))
                        if rs: ratings[aid]["reason"]=rs
                        ratings[aid]["note"]=nv
    st.markdown("---")
    n_rated=sum(1 for r in ratings.values() if r.get("rating"))
    total_acts=sum(len(d["activities"]) for d in days)
    st.markdown(f"**{n_rated} / {total_acts} activities rated**")
    ca,cb=st.columns(2)
    if ca.button("← Edit Trip",use_container_width=True): go("trip_form"); st.rerun()
    if cb.button("📊 Save & Update Recommendations →",use_container_width=True,type="primary"):
        from trip_generator import apply_ratings_to_profile
        from recommender import get_recommendations
        upd=apply_ratings_to_profile(st.session_state["profile"],ratings)
        st.session_state["profile"]=upd
        liked_acts=[{"id":aid,"name":"","budget":0,"city":"","latitude":0,"longitude":0,
                     "address":"","trip_focus_id":None,"category_id":None,
                     "activity_type_slug":None,"recommendable":True}
                    for aid,r in ratings.items() if r.get("rating")=="liked"]
        dis_acts=[{"activity":{"id":aid,"name":"","budget":0,"city":"","latitude":0,
                               "longitude":0,"address":"","trip_focus_id":None,
                               "category_id":None,"activity_type_slug":None,"recommendable":True},
                   "reason":r.get("reason") or "not_my_style","note":r.get("note","")}
                  for aid,r in ratings.items() if r.get("rating")=="disliked"]
        vt=build_vt(upd,fd,liked_acts,dis_acts,"vt2")
        res=get_recommendations(st.session_state["user_id"],ALL_TRIPS+[vt])
        st.session_state["updated_rec_result"]=res

# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 6 — UPDATED RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state["screen"] == "updated_recs":
    result=st.session_state.get("updated_rec_result") or {}
    orig=st.session_state.get("rec_result") or {}
    ratings=st.session_state.get("activity_ratings",{})
    liked_n=sum(1 for r in ratings.values() if r.get("rating")=="liked")
    dis_n=sum(1 for r in ratings.values() if r.get("rating")=="disliked")
    st.markdown("## 📊 Your Updated Recommendations")
    st.success(f"Profile updated — **{liked_n} liked** · **{dis_n} disliked**")
    p=st.session_state["profile"]
    skip_now=[SKIP_LABELS.get(s,s) for s in (p.get("skipList") or [])]
    if skip_now: st.info("🚫 Avoid list: " + " · ".join(skip_now))
    st.markdown("### 🔄 Before vs. After")
    ta,tb=st.tabs(["✨ Updated (Post-Trip)","📌 Original (Post-Onboarding)"])
    for tab,res,lbl in [(ta,result,"Updated"),(tb,orig,"Original")]:
        with tab:
            c1,c2,c3=st.columns(3)
            with c1:
                st.markdown(f"**🌍 Destinations ({lbl})**")
                for d in (res.get("recommendedDestinations") or []):
                    flag=DEST_FLAGS.get(d.get("country_code",""),"🌐")
                    card(f"{flag} <b>{d.get('name','')}</b><br>"
                         f"<span style='color:#aaa;font-size:0.8rem;'>"
                         f"{d.get('city','')}, {d.get('country','')}</span>")
                if not res.get("recommendedDestinations"): st.caption("None yet")
            with c2:
                st.markdown(f"**🏃 Activities ({lbl})**")
                for a in (res.get("recommendedActivities") or []):
                    cat=(a.get("category_id") or "").replace("_"," ").title()
                    budg=f"${a.get('budget')}" if a.get("budget") else "N/A"
                    card(f"<b>{a.get('name','')}</b><br>"
                         f"<span style='color:#7ec891;font-size:0.8rem;'>📂 {cat}</span> "
                         f"<span style='color:#f0c040;font-size:0.8rem;'>💰 {budg}</span>",bg="#1a2a1a")
                if not res.get("recommendedActivities"): st.caption("None yet")
            with c3:
                st.markdown(f"**🎯 Focuses ({lbl})**")
                for f in (res.get("recommendedTripFocus") or []):
                    card(f"🎯 <b>{f.get('name','')}</b>",bg="#2a1a2a")
                if not res.get("recommendedTripFocus"): st.caption("None yet")
    sim=result.get("similarityScores") or {}
    if sim:
        st.markdown("---")
        top=sorted(sim.items(),key=lambda x:x[1],reverse=True)[:12]
        df=pd.DataFrame({"User":[u[:8]+"…" for u,_ in top],"Score":[s for _,s in top]})
        fig=px.bar(df,x="Score",y="User",orientation="h",color="Score",
                   color_continuous_scale="teal",title="Updated Similarity Scores")
        fig.update_layout(plot_bgcolor="#0e1117",paper_bgcolor="#0e1117",
                          font_color="white",height=350,
                          yaxis={"autorange":"reversed"},coloraxis_showscale=False)
        st.plotly_chart(fig,use_container_width=True)
    if ratings:
        st.markdown("---"); st.markdown("### 📋 Your Ratings Summary")
        rows=[{"Activity ID":aid[:12]+"…",
               "Rating":"👍 Liked" if rv["rating"]=="liked" else "👎 Disliked",
               "Reason":rv.get("reason","—") or "—","Note":rv.get("note","—") or "—"}
              for aid,rv in ratings.items() if rv.get("rating")]
        if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    st.markdown("---")
    c1,c2=st.columns(2)
    if c1.button("✈️ Plan Another Trip",use_container_width=True,type="primary"):
        st.session_state.update({"activity_ratings":{},"trip_result":None})
        go("trip_form"); st.rerun()
    if c2.button("🔄 Start Fresh",use_container_width=True):
        st.session_state.update({"profile":{},"trip_result":None,"activity_ratings":{},
            "rec_result":None,"updated_rec_result":None,"onboarding_step":1,
            "trip_form_data":{},"user_id":str(uuid.uuid4())})
        go("onboarding"); st.rerun()

# ── footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:grey;font-size:0.75rem;'>"
    "Navoy Travel Recommendation System · Streamlit Demo · "
    "Collaborative Filtering + Graph-based + LLM-enhanced</p>",
    unsafe_allow_html=True)

