#-------------------------------------------------------------------------------
# CONFIGURATION ET STYLE DE L'APPLICATION
#-------------------------------------------------------------------------------
import streamlit as st
import os
import requests
import pandas as pd
from datetime import date

# Configuration de la page (doit être la première commande Streamlit)
st.set_page_config(page_title="Readiness APP", page_icon="⚡", layout="centered")

# Injection de CSS personnalisé pour une interface moderne et épurée
st.markdown("""
    <style>
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; font-weight: 800 !important; letter-spacing: -0.5px; }
    div[data-testid="stMetricValue"] { color: #00D2D3 !important; font-weight: 900; font-size: 2.5rem !important; }
    div.stButton > button { border-radius: 6px; font-weight: bold; transition: all 0.2s ease-in-out; }
    div.stButton > button:hover { transform: scale(1.02); box-shadow: 0 4px 12px rgba(0, 210, 211, 0.3); }
    </style>
""", unsafe_allow_html=True)

# 1. On cherche d'abord la variable d'environnement (Render)
API_URL = os.getenv("API_URL")

# 2. Si on ne trouve rien sur Render, on cherche dans les secrets Streamlit sans faire planter l'app
if not API_URL:
    try:
        API_URL = st.secrets.get("API_URL")
    except Exception:
        API_URL = None

# 3. Si on n'a toujours rien (cas du test local), on met localhost
if not API_URL:
    API_URL = "http://localhost:8000"

# Nettoyage de l'URL
API_URL = API_URL.rstrip("/")

SPORTS_LIST = ["Cyclisme", "Course à pied", "Natation", "Trail", "Triathlon", "Musculation", "Tennis", "Autre"]

#-------------------------------------------------------------------------------
# GESTION DE L'ÉTAT DE SESSION (Session State)
#-------------------------------------------------------------------------------
if "token" not in st.session_state: st.session_state.token = None
if "user_id" not in st.session_state: st.session_state.user_id = None
if "edit_mode" not in st.session_state: st.session_state.edit_mode = False
if "auth_mode" not in st.session_state: st.session_state.auth_mode = "login"
if "garmin_linked" not in st.session_state: st.session_state.garmin_linked = False
if "needs_review" not in st.session_state: st.session_state.needs_review = []

def logout():
    """Réinitialise totalement la session utilisateur"""
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

#-------------------------------------------------------------------------------
# 1. INTERFACE D'AUTHENTIFICATION (LOGIN / REGISTER)
#-------------------------------------------------------------------------------
if not st.session_state.token:
    st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>⚡ Readiness APP</h1>", unsafe_allow_html=True)
    
    # Formulaire de Connexion
    if st.session_state.auth_mode == "login":
        st.subheader("Connexion")
        with st.form("login_form"):
            login_email = st.text_input("Email")
            login_password = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("Connexion", use_container_width=True):
                res = requests.post(f"{API_URL}/users/login", data={"username": login_email, "password": login_password})
                if res.status_code == 200:
                    data = res.json()
                    st.session_state.token = data["access_token"]
                    st.session_state.user_id = data["user_id"]
                    status_res = requests.get(f"{API_URL}/users/{data['user_id']}/garmin-status")
                    if status_res.status_code == 200:
                        st.session_state.garmin_linked = status_res.json().get("garmin_linked", False)
                    st.rerun()
                else: st.error("Email ou mot de passe incorrect.")
        if st.button("Créer un profil athlète", use_container_width=True):
            st.session_state.auth_mode = "register"; st.rerun()
            
    # Formulaire d'Inscription
    elif st.session_state.auth_mode == "register":
        st.subheader("Nouveau profil athlète")
        with st.form("register_form"):
            col1, col2 = st.columns(2)
            reg_firstname, reg_lastname = col1.text_input("Prénom"), col2.text_input("Nom")
            reg_email, reg_password = st.text_input("Email"), st.text_input("Mot de passe", type="password")
            reg_gender = st.selectbox("Sexe", ["Homme", "Femme", "Autre"])
            reg_birthdate = st.date_input("Date de naissance", value=date(1995, 1, 1))
            reg_weight = col1.number_input("Poids (kg)", value=70.0)
            reg_height = col2.number_input("Taille (cm)", value=175)
            reg_city, reg_country = col1.text_input("Ville"), col2.text_input("Pays")
            st.write("---")
            reg_sport_choices = st.multiselect("Sports pratiqués", SPORTS_LIST)
            final_sports = [s for s in reg_sport_choices if s != "Autre"]
            
            if st.form_submit_button("Valider l'inscription", use_container_width=True):
                sports_str = ", ".join(final_sports) if final_sports else "Non renseigné"
                payload = {
                    "email": reg_email, "password": reg_password, "firstname": reg_firstname, 
                    "lastname": reg_lastname, "birthdate": str(reg_birthdate), "gender": reg_gender, 
                    "address": "N/A", "weight": reg_weight, "height": reg_height, 
                    "city": reg_city, "country": reg_country, "primary_sport": sports_str
                }
                if requests.post(f"{API_URL}/users/register", json=payload).status_code == 200:
                    st.toast("🚀 Compte créé !", icon="✅")
                    st.session_state.auth_mode = "login"; st.rerun()
                else: st.error("Erreur lors de la création.")
        if st.button("Retour à la connexion", use_container_width=True):
            st.session_state.auth_mode = "login"; st.rerun()

#-------------------------------------------------------------------------------
# 2. DASHBOARD PRINCIPAL (UTILISATEUR CONNECTÉ)
#-------------------------------------------------------------------------------
else:
    # Rappel subjectif des séances importées de Garmin sans RPE/Sensation
    if st.session_state.needs_review:
        st.warning("🎯 **Analyse de séance nécessaire**")
        for item in list(st.session_state.needs_review):
            with st.container(border=True):
                st.markdown(f"**{item['sport'].upper()}** — {item['date']} ({item['duration']} min)")
                c1, c2 = st.columns(2)
                rpe = c1.select_slider("Effort (1-10)", options=range(1, 11), value=5, key=f"rpe_{item['id']}")
                feel = c2.select_slider("Sensation (1-10)", options=range(1, 11), value=5, key=f"feel_{item['id']}")
                if st.button("Valider", key=f"btn_{item['id']}", use_container_width=True):
                    res = requests.patch(f"{API_URL}/activities/{item['id']}/review?rpe={rpe}&feeling={feel}")
                    if res.status_code == 200:
                        st.session_state.needs_review = [i for i in st.session_state.needs_review if i['id'] != item['id']]
                        st.rerun()
        if st.button("Plus tard", use_container_width=True):
            st.session_state.needs_review = []; st.rerun()
        st.divider()

    # Organisation du Dashboard en onglets
    tab_home, tab_trends, tab_settings = st.tabs(["🏠 Accueil", "📈 Historique des données", "⚙️ Paramètres"])

    # --- ONGLET ACCUEIL (CHECK-IN) ---
    with tab_home:
        today_res = requests.get(f"{API_URL}/checkin/today/{st.session_state.user_id}")
        if today_res.status_code != 200 or st.session_state.edit_mode:
            st.title("Check-in Quotidien")
            with st.form("readiness_form"):
                col1, col2 = st.columns(2)
                sq = col1.select_slider("Qualité du sommeil", options=range(1, 11), value=7)
                sd = col2.number_input("Sommeil estimé (h)", value=8.0, step=0.5)
                fatigue, motivation = st.slider("Fatigue", 1, 10, 3), st.slider("Motivation", 1, 10, 8)
                stress = st.slider("Stress / Charge mentale", 1, 10, 2)
                mood = st.selectbox("Humeur", ["😁 Très joyeux", "🙂 Content", "😐 Neutre", "😔 Triste", "😠 Irrité"])
                
                st.subheader("🦵 État Musculaire")
                muscles = ["Cuisses", "Mollets", "Dos", "Épaules", "Bras", "Abdos", "Fessiers"]
                soreness_data = {}
                with st.expander("Signaler des courbatures", expanded=False):
                    c1, c2 = st.columns(2)
                    for i, muscle in enumerate(muscles):
                        col = c1 if i % 2 == 0 else c2 
                        val = col.select_slider(muscle, options=[0,1,2,3,4,5], value=0, key=f"s_{muscle}")
                        if val > 0: soreness_data[muscle] = val

                if st.form_submit_button("Envoyer mon rapport", use_container_width=True):
                    payload = {
                        "user_id": st.session_state.user_id, "sleep_quality": sq, "sleep_duration": sd,
                        "fatigue_level": fatigue, "motivation_level": motivation, "mental_stress": stress, 
                        "mood_emoji": mood, "muscle_soreness": soreness_data  
                    }
                    requests.post(f"{API_URL}/checkin", json=payload)
                    st.session_state.edit_mode = False; st.rerun()
        else:
            data = today_res.json()
            st.title("Ma forme du jour")
            c1, c2, c3 = st.columns(3)
            c1.metric("Wellness", f"{data.get('wellness_score', '--')}/10")
            c2.metric("Sommeil", f"{data['sleep_duration']}h")
            soreness = data.get('muscle_soreness')
            if soreness:
                c3.metric("Douleur Musc.", f"{max(soreness.values())}/5", ", ".join(soreness.keys()), delta_color="inverse")
            else:
                c3.metric("Douleur Musc.", "Aucune", "Récupération OK")
            if st.button("Modifier mon check-in"): st.session_state.edit_mode = True; st.rerun()

    # --- ONGLET HISTORIQUE & ANALYSE ---
    with tab_trends:
        st.title("Analyse Long Terme")
        sub_tab1, sub_tab2 = st.tabs(["📊 Évolution des scores", "🏃‍♂️ Journal des activités"])
        with sub_tab1:
            hist_res = requests.get(f"{API_URL}/history/{st.session_state.user_id}")
            if hist_res.status_code == 200 and hist_res.json():
                df = pd.DataFrame(hist_res.json())
                df['date'] = pd.to_datetime(df['date'])
                metrics = {"🌟 Score de Wellness": "wellness_score", "💤 Sommeil (h)": "sleep_duration", "🔋 Fatigue": "fatigue_level", "🧠 Stress": "mental_stress"}
                sel_col = metrics[st.selectbox("Indicateur à visualiser", list(metrics.keys()))]
                st.bar_chart(df.set_index('date')[sel_col], color="#00D2D3")
            else: st.info("Historique vide.")
        with sub_tab2:
            act_res = requests.get(f"{API_URL}/activities/{st.session_state.user_id}")
            if act_res.status_code == 200:
                for act in act_res.json():
                    with st.expander(f"{act['sport'].upper()} — {act['date'][:10]}"):
                        st.write(f"Durée: {act['duration_minutes']}min | FC Moy: {act['avg_hr']}")
                        if act['perceived_effort']: st.caption(f"🎯 RPE: {act['perceived_effort']}/10 | Feeling: {act['feeling']}/10")

    # --- ONGLET PARAMÈTRES & GARMIN ---
    with tab_settings:
        st.title("Réglages")
        st.subheader("Connexion Garmin Connect™")
        if st.session_state.garmin_linked:
            st.success("✅ Compte Garmin synchronisé")
            if st.button("Déconnecter Garmin"): st.session_state.garmin_linked = False; st.rerun()
        else:
            with st.form("garmin_form"):
                g_email, g_pwd = st.text_input("Email Garmin"), st.text_input("Mot de passe", type="password")
                if st.form_submit_button("Lier ma montre"):
                    if requests.post(f"{API_URL}/users/garmin/connect", json={"user_id": st.session_state.user_id, "garmin_email": g_email, "garmin_password": g_pwd}).status_code == 200:
                        st.session_state.garmin_linked = True; st.rerun()
        
        st.divider()
        if st.button("🔄 Synchroniser mes activités", use_container_width=True):
            with st.spinner("Importation des données..."):
                sync_res = requests.post(f"{API_URL}/sync/activities/{st.session_state.user_id}")
                if sync_res.status_code == 200:
                    st.session_state.needs_review = sync_res.json().get("needs_review", [])
                    st.rerun() if st.session_state.needs_review else st.success("✅ À jour !")
                else: st.error("Erreur de synchro.")
                    
        st.divider()
        st.button("Se déconnecter", type="primary", on_click=logout, use_container_width=True)