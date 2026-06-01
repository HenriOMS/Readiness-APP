#-------------------------------------------------------------------------------
# MODULE DE SÉCURITÉ (Hachage, JWT et Chiffrement)
#-------------------------------------------------------------------------------
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
import bcrypt
from cryptography.fernet import Fernet
from config import settings

#-------------------------------------------------------------------------------
# GESTION DES MOTS DE PASSE (BCRYPT)
#-------------------------------------------------------------------------------

# Vérifie si le mot de passe saisi correspond au hachage stocké en base de données
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

# Génère un sel et hache le mot de passe pour un stockage sécurisé
def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

#-------------------------------------------------------------------------------
# GESTION DES TOKENS DE SESSION (JWT)
#-------------------------------------------------------------------------------

# Génère un jeton d'accès temporaire pour maintenir la session de l'athlète
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

#-------------------------------------------------------------------------------
# CHIFFREMENT DES IDENTIFIANTS TIERS (FERNET)
#-------------------------------------------------------------------------------
# Utilise une clé symétrique pour protéger les mots de passe des comptes liés (Garmin)

fernet_cipher = Fernet(settings.garmin_secret_key.encode('utf-8'))

# Chiffre le mot de passe Garmin avant l'enregistrement en base de données
def encrypt_garmin_password(plain_password: str) -> str:
    return fernet_cipher.encrypt(plain_password.encode('utf-8')).decode('utf-8')

# Déchiffre le mot de passe Garmin pour permettre la synchronisation automatique
def decrypt_garmin_password(encrypted_password: str) -> str:
    return fernet_cipher.decrypt(encrypted_password.encode('utf-8')).decode('utf-8')