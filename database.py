import os
import mysql.connector

# --- KONFIGURASI DATABASE ---
db_config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'spc_user'),
    'password': os.environ.get('DB_PASSWORD', 'spc_password'),
    'database': os.environ.get('DB_NAME', 'spc_database')
}

def get_db_connection():
    return mysql.connector.connect(**db_config)
