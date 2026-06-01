from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models
import schemas

#-------------------------------------------------------------------------------
# CONFIGURATION DES SCORES ET CONSTANTES
#-------------------------------------------------------------------------------
# Conversion des émotions en scores numériques pour l'algorithme
MOOD_SCORES = {
    "😁 Très joyeux": 10, 
    "🙂 Content": 8, 
    "😐 Neutre": 6, 
    "😔 Triste": 4, 
    "😠 Irrité": 2
}

#-------------------------------------------------------------------------------
# ALGORITHME DE CALCUL DES SCORES (LOGIQUE MÉTIER)
#-------------------------------------------------------------------------------
# Calcule les deux scores piliers (Wellness et Readiness) en croisant les données subjectives et physiologiques
def calculate_readiness_scores(metric: schemas.DailyMetricCreate, db: Session):
  
    # 1. CALCUL DU WELLNESS SCORE (Basé sur le ressenti de l'athlète)
    # La pondération est à améliorer en fonction de l'impact de chacune des variables aprés analyse plus approfondie

    if metric.muscle_soreness:
        max_pain = max(metric.muscle_soreness.values())
    else:
        max_pain = 1
        
    score_soreness = 12 - (max_pain * 2) 
    score_fatigue = 11 - metric.fatigue_level
    score_stress = 11 - metric.mental_stress
    score_mood = MOOD_SCORES.get(metric.mood_emoji, 6)
    
    wellness_score = (metric.sleep_quality + score_fatigue + score_stress + score_mood + score_soreness) / 5
    
    # 2. CALCUL DE LA GENERAL READINESS (Basé sur la charge réelle)
    yesterday = datetime.now() - timedelta(days=1)
    
    # On cherche les activités de l'athlète des dernières 24h
    recent_activities = db.query(models.Activity).filter(
        models.Activity.user_id == metric.user_id,
        models.Activity.date >= yesterday
    ).all()
    
    acute_load = 0
    for act in recent_activities:
        rpe = act.perceived_effort if act.perceived_effort else 0 
        duration = act.duration_minutes if act.duration_minutes else 0
        acute_load += (duration * rpe)
    
    fatigue_penalty = min(acute_load / 2000, 0.40) 
    readiness_score = wellness_score * (1 - fatigue_penalty)
    
    # On retourne les deux scores arrondis proprement
    return round(wellness_score, 1), round(readiness_score, 1)