#-------------------------------------------------------------------------------
# OPÉRATIONS DE BASE DE DONNÉES (CRUD - Create, Read, Update, Delete)
#-------------------------------------------------------------------------------
from sqlalchemy.orm import Session
from datetime import date
import models
import schemas

#-------------------------------------------------------------------------------
# GESTION DES MÉTRIQUES QUOTIDIENNES (WELLNESS & READINESS)
#-------------------------------------------------------------------------------

# Enregistre un nouveau check-in en fusionnant les données saisies et les scores calculés
def create_daily_metric(db: Session, metric: schemas.DailyMetricCreate, wellness: float, readiness: float):
    metric_data = metric.model_dump()
    
    db_metric = models.DailyMetric(
        **metric_data, 
        wellness_score=wellness, 
        general_readiness=readiness
    )
    
    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)
    return db_metric

# Actualise un check-in existant (évite les doublons si l'athlète se trompe)
def update_daily_metric(db: Session, db_metric: models.DailyMetric, metric: schemas.DailyMetricCreate, wellness: float, readiness: float):
    for key, value in metric.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(db_metric, key, value)
            
    db_metric.wellness_score = wellness
    db_metric.general_readiness = readiness
    
    db.commit()
    db.refresh(db_metric)
    return db_metric

# Récupère les données historiques d'un athlète pour l'affichage des graphiques
def get_user_history(db: Session, user_id: int, limit: int = 30):
    return db.query(models.DailyMetric)\
             .filter(models.DailyMetric.user_id == user_id)\
             .order_by(models.DailyMetric.date.desc())\
             .limit(limit)\
             .all()

# Vérifie si un check-in a déjà été effectué par l'utilisateur à une date donnée
def get_metric_by_date(db: Session, user_id: int, target_date: date):
    return db.query(models.DailyMetric)\
             .filter(models.DailyMetric.user_id == user_id, models.DailyMetric.date == target_date)\
             .first()

#-------------------------------------------------------------------------------
# GESTION DES ACTIVITÉS PHYSIQUES (SÉANCES GARMIN)
#-------------------------------------------------------------------------------

# Recherche une activité spécifique par son ID unique Garmin (prévention des doublons)
def get_activity_by_garmin_id(db: Session, garmin_activity_id: str):
    return db.query(models.Activity).filter(models.Activity.garmin_activity_id == garmin_activity_id).first()

# Enregistre une nouvelle séance sport récupérée lors de la synchronisation
def create_activity(db: Session, activity: schemas.ActivityCreate):
    if get_activity_by_garmin_id(db, activity.garmin_activity_id):
        return None 

    db_activity = models.Activity(**activity.model_dump())
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)
    return db_activity

# Met à jour les détails d'une séance (utile pour ajouter le RPE ou le ressenti)
def update_activity(db: Session, db_activity: models.Activity, activity: schemas.ActivityCreate):
    update_data = activity.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_activity, key, value)
    db.commit()
    db.refresh(db_activity)
    return db_activity

# Récupère la liste chronologique des entraînements de l'athlète
def get_user_activities(db: Session, user_id: int, limit: int = 50):
    return db.query(models.Activity)\
             .filter(models.Activity.user_id == user_id)\
             .order_by(models.Activity.date.desc())\
             .limit(limit)\
             .all()