#-------------------------------------------------------------------------------
# SCHÉMAS DE DONNÉES (Pydantic Models - Validation & Sérialisation)
#-------------------------------------------------------------------------------
from pydantic import BaseModel, EmailStr, Field
from datetime import date, time, datetime
from typing import List, Optional, Dict

#-------------------------------------------------------------------------------
# AUTHENTIFICATION & ACCÈS
#-------------------------------------------------------------------------------

# Structure du jeton retourné après une connexion réussie
class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int

#-------------------------------------------------------------------------------
# GESTION DES UTILISATEURS (ATHLÈTES)
#-------------------------------------------------------------------------------

# Données requises pour la création d'un nouveau profil
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    firstname: str
    lastname: str
    birthdate: date
    gender: str         
    address: str         
    weight: float
    height: int
    city: str
    country: str
    notification_time: Optional[time] = time(8, 0)
    primary_sport: str

## Format de réponse complet envoyé au client
class UserResponse(BaseModel):
    id: int
    email: str
    firstname: str
    lastname: str
    weight: float
    height: int
    address: str
    city: str
    country: str
    primary_sport: Optional[str] = None
    
    class Config:
        from_attributes = True

# Données autorisées pour la mise à jour du profil
class UserUpdate(BaseModel):
    password: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    weight: Optional[float] = None
    height: Optional[int] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    primary_sport: Optional[str] = None

#-------------------------------------------------------------------------------
# MÉTRIQUES QUOTIDIENNES (CHECK-IN)
#-------------------------------------------------------------------------------

# Données brutes reçues lors du check-in matinal
class DailyMetricCreate(BaseModel):
    user_id: int 
    sleep_quality: int                             
    garmin_sleep_score: Optional[int] = None        
    sleep_duration: Optional[float] = None
    resting_hr: Optional[int] = None 
    fatigue_level: int
    motivation_level: int
    muscle_soreness: Optional[Dict[str, int]] = None
    mental_stress: int
    mood_emoji: str

# Structure complète incluant les scores calculés par l'algorithme Enduraw
class DailyMetricResponse(DailyMetricCreate):
    id: int
    date: date
    created_at: datetime
    wellness_score: Optional[float] = None
    general_readiness: Optional[float] = None

    class Config:
        from_attributes = True

#-------------------------------------------------------------------------------
# CONNEXION SERVICES TIERS
#-------------------------------------------------------------------------------

# Schéma pour l'appairage du compte Garmin Connect
class GarminConnect(BaseModel):
    user_id: int
    garmin_email: str
    garmin_password: str

#-------------------------------------------------------------------------------
# ACTIVITÉS SPORTIVES (SÉANCES)
#-------------------------------------------------------------------------------

# Structure des données d'entraînement importées ou créées
class ActivityCreate(BaseModel):
    user_id: int
    garmin_activity_id: str
    date: datetime
    sport: str
    duration_minutes: float
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    calories: Optional[float] = None
    temperature: Optional[float] = None
    sweat_loss: Optional[float] = None
    perceived_effort: Optional[float] = None
    feeling: Optional[float] = None

# Réponse incluant l'ID unique de la base de données
class ActivityResponse(ActivityCreate):
    id: int

    class Config:
        from_attributes = True