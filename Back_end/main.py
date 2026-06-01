#-------------------------------------------------------------------------------
# CONFIGURATION ET IMPORTS
#-------------------------------------------------------------------------------
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import date, timedelta, datetime 
from typing import List
from fastapi.security import OAuth2PasswordRequestForm
from garminconnect import Garmin

import crud, schemas, security, models
from database import engine, Base, get_db
from config import settings
from scoring import calculate_readiness_scores

# Initialisation de la base de données
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Enduraw Readiness API")

# Configuration CORS (Autorise le Frontend à communiquer avec le Backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#-------------------------------------------------------------------------------
# UTILS / FONCTIONS SUPPORTS
#-------------------------------------------------------------------------------
# Calcule l'âge exact de l'utilisateur à partir de sa date de naissance
def calculate_age(birthdate: date):
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

#-------------------------------------------------------------------------------
# GESTION DES SESSIONS GARMIN (RAM CACHE)
#-------------------------------------------------------------------------------
garmin_sessions = {} 

# Gère le cycle de vie de la session Garmin (création, réutilisation ou reconnexion en cas d'expiration)
def get_garmin_client(user_id: int, email: str, plain_pwd: str):
    if user_id in garmin_sessions:
        try:
            client = garmin_sessions[user_id]
            client.get_full_name() 
            print(f"✅ Session Garmin réutilisée pour l'utilisateur {user_id}")
            return client
        except Exception:
            print(f"⚠️ Session expirée pour {user_id}, reconnexion...")
            garmin_sessions.pop(user_id, None)

    print(f"🔌 Nouvelle connexion à Garmin pour l'utilisateur {user_id}")
    client = Garmin(email, plain_pwd)
    client.login()
    garmin_sessions[user_id] = client
    return client

#-------------------------------------------------------------------------------
# AUTHENTIFICATION ET UTILISATEURS
#-------------------------------------------------------------------------------
# Enregistre un nouvel athlète en hachant son mot de passe et en calculant son âge
@app.post("/users/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    
    hashed_pwd = security.get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        hashed_password=hashed_pwd,
        firstname=user.firstname,
        lastname=user.lastname,
        birthdate=user.birthdate,
        age=calculate_age(user.birthdate),           
        gender=user.gender,     
        address=user.address, 
        weight=user.weight,
        height=user.height,
        city=user.city,
        country=user.country,
        notification_time=user.notification_time,
        primary_sport=user.primary_sport
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# Vérifie les identifiants de l'athlète et génère un jeton JWT d'accès sécurisé
@app.post("/users/login", response_model=schemas.Token)
def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id}

#-------------------------------------------------------------------------------
# CONNEXION ET STATUT GARMIN
#-------------------------------------------------------------------------------
# Chiffre le mot de passe Garmin fourni et valide la connexion avec l'API officielle
@app.post("/users/garmin/connect")
def connect_garmin_account(credentials: schemas.GarminConnect, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == credentials.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    try:
        get_garmin_client(user.id, credentials.garmin_email, credentials.garmin_password)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Identifiants Garmin incorrects")
        
    user.garmin_email = credentials.garmin_email
    user.garmin_encrypted_password = security.encrypt_garmin_password(credentials.garmin_password)
    db.commit()
    return {"message": "Compte Garmin lié avec succès !"}

# Vérifie si l'utilisateur possède un compte Garmin actuellement connecté et actif
@app.get("/users/{user_id}/garmin-status")
def get_garmin_status(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    
    is_linked = user.garmin_email is not None and user.garmin_encrypted_password is not None
    return {"garmin_linked": is_linked}

#-------------------------------------------------------------------------------
# GESTION DU CHECK-IN QUOTIDIEN (READINESS & WELLNESS)
#-------------------------------------------------------------------------------
# Récupère l'état de forme enregistré pour la journée en cours
@app.get("/checkin/today/{user_id}", response_model=schemas.DailyMetricResponse)
def get_today_checkin(user_id: int, db: Session = Depends(get_db)):
    metric = crud.get_metric_by_date(db, user_id, date.today())
    if not metric:
        raise HTTPException(status_code=404, detail="Pas de check-in aujourd'hui")
    return metric

# Intercepte le check-in, extrait silencieusement les données Garmin de la nuit, calcule les algorithmes de score puis crée ou met à jour la ligne en BDD
@app.post("/checkin", response_model=schemas.DailyMetricResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_checkin(metric: schemas.DailyMetricCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == metric.user_id).first()
    
    # Récupération automatique des données Garmin si le compte est lié
    if user and user.garmin_email and user.garmin_encrypted_password:
        try:
            plain_pwd = security.decrypt_garmin_password(user.garmin_encrypted_password)
            client = get_garmin_client(user.id, user.garmin_email, plain_pwd)
            today_str = date.today().isoformat()
            
            stats = client.get_stats(today_str)
            if stats and stats.get('restingHeartRate'):
                metric.resting_hr = stats['restingHeartRate'] 
            
            sleep_data = client.get_sleep_data(today_str)
            if sleep_data and sleep_data.get('dailySleepDTO'):
                sleep_seconds = sleep_data['dailySleepDTO'].get('sleepTimeSeconds')
                if sleep_seconds is not None and sleep_seconds > 0:
                    metric.sleep_duration = round(sleep_seconds / 3600, 1)
                
                try:
                    score = sleep_data['dailySleepDTO'].get('sleepScores', {}).get('overall', {}).get('value')
                    if score:
                        metric.garmin_sleep_score = round(score / 10)
                except: pass
        except Exception as e:
            print(f"Échec Garmin silencieux : {e}")
    
    # Calcul des scores Wellness et Readiness via l'algorithme
    final_wellness, final_readiness = calculate_readiness_scores(metric, db)
        
    existing_metric = crud.get_metric_by_date(db, metric.user_id, date.today())
    
    if existing_metric:
        return crud.update_daily_metric(db, existing_metric, metric, final_wellness, final_readiness)
    else:
        return crud.create_daily_metric(db, metric, final_wellness, final_readiness)

#-------------------------------------------------------------------------------
# HISTORIQUE ET ANALYSES
#-------------------------------------------------------------------------------
# Récupère l'historique chronologique des données de forme sur une période définie
@app.get("/history/{user_id}", response_model=List[schemas.DailyMetricResponse])
def read_history(user_id: int, limit: int = 30, db: Session = Depends(get_db)):
    return crud.get_user_history(db, user_id=user_id, limit=limit)

#-------------------------------------------------------------------------------
# SYNCHRONISATION DES ACTIVITÉS SPORTIVES
#-------------------------------------------------------------------------------
# Télécharge les 10 dernières activités Garmin de l'athlète et liste celles qui nécessitent une évaluation subjective (RPE/Feeling)
@app.post("/sync/activities/{user_id}")
def sync_garmin_activities(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.garmin_email or not user.garmin_encrypted_password:
        raise HTTPException(status_code=400, detail="Compte Garmin non lié")

    try:
        plain_pwd = security.decrypt_garmin_password(user.garmin_encrypted_password)
        client = get_garmin_client(user.id, user.garmin_email, plain_pwd)
        
        activities = client.get_activities(0, 10)
        saved_count = 0
        updated_count = 0
        incomplete_activities = [] 
        
        for act in activities:
            act_date_str = act.get("startTimeLocal")
            act_date = datetime.strptime(act_date_str, "%Y-%m-%d %H:%M:%S") if act_date_str else datetime.now()
            
            activity_data = schemas.ActivityCreate(
                user_id=user_id,
                garmin_activity_id=str(act.get("activityId")),
                date=act_date,
                sport=act.get("activityType", {}).get("typeKey", "unknown"),
                duration_minutes=round(act.get("duration", 0) / 60, 1),
                avg_hr=act.get("averageHR"),
                max_hr=act.get("maxHR"),
                calories=act.get("calories"),
                temperature=act.get("maxTemperature"), 
                sweat_loss=act.get("waterEstimated"),  
                perceived_effort=act.get("perceivedExertion") or act.get("atpActivitySelfExertion"),
                feeling=act.get("feeling") or act.get("atpActivitySelfFeeling")
            )
            
            existing_act = crud.get_activity_by_garmin_id(db, activity_data.garmin_activity_id)
            
            if existing_act:
                crud.update_activity(db, existing_act, activity_data)
                final_act = existing_act
                updated_count += 1
            else:
                final_act = crud.create_activity(db=db, activity=activity_data)
                saved_count += 1
                
            if act_date.date() >= date.today() - timedelta(days=1):
                if final_act.perceived_effort is None or final_act.feeling is None:
                    incomplete_activities.append({
                        "id": final_act.id,
                        "date": final_act.date.strftime("%d/%m"),
                        "sport": final_act.sport,
                        "duration": final_act.duration_minutes
                    })
                
        return {
            "message": f"Sync terminée : {saved_count} nouvelles, {updated_count} mises à jour.",
            "needs_review": incomplete_activities
        }
        
    except Exception as e:
        print(f"Erreur Sync Garmin: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Permet à l'athlète de compléter manuellement l'effort ressenti (RPE) et le ressenti d'une séance spécifique
@app.patch("/activities/{activity_id}/review")
def review_activity(activity_id: int, rpe: float, feeling: float, db: Session = Depends(get_db)):
    db_act = db.query(models.Activity).filter(models.Activity.id == activity_id).first()
    if not db_act: 
        raise HTTPException(status_code=404, detail="Activité introuvable")
    db_act.perceived_effort = rpe
    db_act.feeling = feeling
    db.commit()
    return {"status": "updated"}

# Récupère la liste de toutes les activités physiques enregistrées pour un athlète
@app.get("/activities/{user_id}", response_model=List[schemas.ActivityResponse])
def read_activities(user_id: int, limit: int = 50, db: Session = Depends(get_db)):
    return crud.get_user_activities(db, user_id=user_id, limit=limit)

#-------------------------------------------------------------------------------
# POINTS D'ENTRÉE SYSTÈME
#-------------------------------------------------------------------------------
@app.get("/")
def read_root():
    return {"message": "Welcome to Enduraw Readiness API v1"}