import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "bankuser"),
    "password": os.getenv("DB_PASSWORD", "bank123"),
    "database": os.getenv("DB_NAME", "bankdb")
}