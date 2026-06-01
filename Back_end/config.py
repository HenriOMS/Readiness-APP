#-------------------------------------------------------------------------------
# CONFIGURATION GLOBALE (Gestion des variables d'environnement)
#-------------------------------------------------------------------------------
from pydantic_settings import BaseSettings, SettingsConfigDict

#-------------------------------------------------------------------------------
# CLASSE DE RÉGLAGES (Pydantic Settings)
#-------------------------------------------------------------------------------
# Centralise toutes les variables sensibles pour éviter de les coder "en dur"
class Settings(BaseSettings):
    
    # Configuration Base de données (Supabase)
    postgres_user: str
    postgres_password: str
    postgres_db: str
    database_url: str
    
    # Sécurité JWT (Authentification des sessions)
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440 # Par défaut 24h
    
    # Sécurité Tiers (Chiffrement des accès Garmin)
    garmin_secret_key: str

    #---------------------------------------------------------------------------
    # LECTURE AUTOMATIQUE DU FICHIER .ENV
    #---------------------------------------------------------------------------
    # Charge les valeurs depuis le fichier .env présent à la racine du projet
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8"
    )

# Instanciation unique pour être utilisée partout dans l'application
settings = Settings()