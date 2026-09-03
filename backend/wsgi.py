"""
Production entrypoint for Gunicorn.

app.py only calls init_db() under `if __name__ == "__main__"`, which does not
run when Gunicorn imports the app. Importing through this module guarantees the
SQLite tables exist before the first request is served.

Run with:  gunicorn wsgi:app
"""

from app import app, init_db

init_db()
