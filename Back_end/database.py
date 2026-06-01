import json
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings

#-------------------------------------------------------------------------------
# CONFIGURATION DE L'ENGINE (Le connecteur PostgreSQL)
#-------------------------------------------------------------------------------
# On configure le moteur pour gérer correctement les données JSON (accents/emojis)
engine = create_engine(
    settings.database_url,
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False)
)

#-------------------------------------------------------------------------------
# GESTION DES SESSIONS
#-------------------------------------------------------------------------------
# Création de l'usine à sessions pour interagir avec la base de données
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe de base pour la création de tous nos modèles (Table DailyMetric, User, etc.)
Base = declarative_base()

#-------------------------------------------------------------------------------
# DÉPENDANCE DE SESSION (Dependency Injection)
#-------------------------------------------------------------------------------
# Assure l'ouverture et la fermeture propre de la base de données à chaque requête API
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()