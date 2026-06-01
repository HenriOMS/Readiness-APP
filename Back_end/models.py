#-------------------------------------------------------------------------------
# MODÈLES DE BASE DE DONNÉES (SQLAlchemy - PostgreSQL)
#-------------------------------------------------------------------------------
from sqlalchemy import Column, Integer, Float, String, Date, DateTime, JSON, Time, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

#-------------------------------------------------------------------------------
# TABLE UTILISATEURS (PROFIL ATHLÈTE)
#-------------------------------------------------------------------------------
# Stocke l'identité, les données physiologiques de base et les accès Garmin chiffrés
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    firstname = Column(String, nullable=False)
    lastname = Column(String, nullable=False)
    birthdate = Column(Date, nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    address = Column(String, nullable=False)
    weight = Column(Float, nullable=False)
    height = Column(Integer, nullable=False)
    city = Column(String, nullable=False)
    country = Column(String, nullable=False)
    notification_time = Column(Time, default="08:00:00")
    primary_sport = Column(String)

    # Identifiants Garmin (chiffrés côté Backend)
    garmin_email = Column(String, nullable=True)
    garmin_encrypted_password = Column(String, nullable=True)

    # Relations SQLAlchemy pour lier les données à l'utilisateur
    metrics = relationship("DailyMetric", back_populates="owner")
    activities = relationship("Activity", back_populates="owner")

#-------------------------------------------------------------------------------
# TABLE MÉTRIQUES QUOTIDIENNES (WELLNESS & READINESS)
#-------------------------------------------------------------------------------
# Enregistre le ressenti matinal et fusionne les scores Garmin avec l'algorithme interne
class DailyMetric(Base):
    __tablename__ = "daily_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, default=func.current_date(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # --- SOMMEIL (Double perspective : Subjectif vs Objectif) ---
    sleep_quality = Column(Integer, nullable=False)         # Ressenti utilisateur (1-10)
    garmin_sleep_score = Column(Integer, nullable=True)     # Score calculé par la montre (/100 ramené à /10)
    sleep_duration = Column(Float, nullable=True)           # Durée réelle extraite de Garmin (heures)
    
    # --- SIGNES VITAUX ET ÉTAT PHYSIQUE ---
    resting_hr = Column(Integer, nullable=True)             # FC au repos (BPM)
    fatigue_level = Column(Integer, nullable=False)         # Niveau de fatigue (1-10)
    motivation_level = Column(Integer, nullable=False)      # Envie de s'entraîner (1-10)
    mental_stress = Column(Integer, nullable=False)         # Charge mentale (1-10)
    mood_emoji = Column(String, nullable=False)             # État émotionnel choisi
    muscle_soreness = Column(JSON, nullable=True)           # Zones douloureuses (ex: {"Mollets": 3})

    # --- SCORES DE PERFORMANCE ENDURAW ---
    wellness_score = Column(Float, nullable=False)          # Score de forme basé sur le ressenti matinal
    general_readiness = Column(Float, nullable=True)        # Score de préparation final (Pondéré par la charge)
    
    owner = relationship("User", back_populates="metrics")

#-------------------------------------------------------------------------------
# TABLE ACTIVITÉS (SÉANCES SPORTIVES)
#-------------------------------------------------------------------------------
# Historique des entraînements récupérés via l'API Garmin Connect
class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Identifiant unique Garmin pour éviter les doublons lors des synchronisations
    garmin_activity_id = Column(String, unique=True, index=True, nullable=False)
    date = Column(DateTime, nullable=False)
    sport = Column(String, nullable=False)
    
    # Métriques de performance brutes
    duration_minutes = Column(Float, nullable=False)
    avg_hr = Column(Integer, nullable=True)
    max_hr = Column(Integer, nullable=True)
    calories = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    sweat_loss = Column(Float, nullable=True)
    
    # Évaluation de la séance (Subjective / RPE)
    perceived_effort = Column(Float, nullable=True) 
    feeling = Column(Float, nullable=True)

    owner = relationship("User", back_populates="activities")