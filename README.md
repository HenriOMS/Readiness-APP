# ⚡ Readiness APP 

Readiness APP est une application Full-Stack conçue pour les athlètes afin de suivre leur état de forme quotidien, leur charge d'entraînement et leur niveau de récupération. L'application combine des données subjectives (ressenti de l'athlète) avec des données physiologiques objectives synchronisées automatiquement depuis **Garmin Connect™**.

## Accès en Ligne (Live Demo)
L'application est déployée en production et accessible publiquement via ces liens :
- **Application Utilisateur (Front-end) :** https://readiness-app-front.onrender.com
- **Documentation Interactive de l'API (Swagger) :** https://readiness-app-0ilu.onrender.com/docs

## Fonctionnalités Principales

- **Check-in Quotidien :** Suivi matinal du sommeil, de la fatigue, du stress, de la motivation et de l'état musculaire (courbatures).
- **Synchronisation Garmin Connect :** Importation automatique des données de sommeil, de la fréquence cardiaque au repos et du journal des activités sportives.
- **Algorithme de Scoring :** Calcul quotidien d'un **Score de Bien-être** (Wellness) et d'un **Score de Préparation** (Readiness) ajusté selon la charge d'entraînement aiguë.
- **Dashboard Analytique :** Visualisation graphique de l'évolution de la forme et historique détaillé des entraînements.
- **Évaluation de l'Effort (RPE) :** Complétion manuelle du ressenti et de l'effort perçu pour chaque séance importée de la montre.
- **Gestion de Profil :** Interface complète pour modifier ses informations personnelles, sports pratiqués, adresses, et gérer la connexion sécurisée à Garmin.

## Stack Technique

- **Front-end :** Python, Streamlit, Pandas, Requests.
- **Back-end :** Python, FastAPI, SQLAlchemy, Pydantic, Uvicorn.
- **Base de données :** PostgreSQL (Hébergée sur Supabase).
- **Sécurité & Authentification :** JWT (JSON Web Tokens), Bcrypt (hachage des mots de passe), Cryptography Fernet (chiffrement des identifiants Garmin).
- **Infrastructure :** Docker & Docker Compose, Hébergement sur Render.

## Installation et Lancement en Local

### Prérequis
- Docker et Docker Compose installés sur votre machine.
- Git

### 1. Cloner le dépôt
git clone https://github.com/HenriOMS/Readiness-APP.git
cd Readiness-APP

### 2. Variables d'environnement
Créez un fichier `.env` à la racine du projet et ajoutez vos variables de configuration (remplacez les valeurs par les vôtres) :

POSTGRES_USER=readiness_app_admin
POSTGRES_PASSWORD=votre_mot_de_passe
POSTGRES_DB=readiness_db
DATABASE_URL=postgresql://readiness_app_admin:votre_mot_de_passe@db:5432/readiness_db

SECRET_KEY=VOTRE_CLE_SECRETE_JWT
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
GARMIN_SECRET_KEY=VOTRE_CLE_DE_CHIFFREMENT_FERNET

### 3. Lancer l'application avec Docker
Exécutez la commande suivante à la racine du projet pour construire et démarrer les conteneurs (Base de données, Backend, Frontend) :

docker-compose up --build

### 4. Accès à l'application locale
Une fois les conteneurs démarrés, l'application est accessible via votre navigateur en local :
- **Interface Utilisateur (Streamlit) :** http://localhost:8501
- **Documentation Interactive de l'API (Swagger UI) :** http://localhost:8000/docs

## 🗂️ Structure du Projet

Readiness-APP/
├── Back_end/                 # Serveur FastAPI
│   ├── main.py               # Routes principales de l'API
│   ├── models.py             # Modèles de base de données (SQLAlchemy)
│   ├── schemas.py            # Validation des données (Pydantic)
│   ├── crud.py               # Opérations de base de données
│   ├── scoring.py            # Algorithmes de calcul Readiness/Wellness
│   ├── security.py           # Gestion JWT, Bcrypt et chiffrement
│   ├── database.py           # Connexion PostgreSQL
│   ├── config.py             # Gestion des variables d'environnement
│   └── dockerfile            # Configuration de l'image Docker Backend
├── Front_end/                # Interface utilisateur Streamlit
│   ├── app.py                # Dashboard principal et formulaires
│   └── dockerfile            # Configuration de l'image Docker Frontend
├── docker-compose.yml        # Orchestration des services
└── README.md

## Sécurité et Confidentialité
- Les mots de passe des utilisateurs sont hachés via `bcrypt` avant stockage.
- Les identifiants Garmin (nécessaires pour la synchronisation) sont chiffrés symétriquement en base de données (`cryptography.fernet`) et ne sont déchiffrés qu'à la volée lors des appels API vers les serveurs Garmin.