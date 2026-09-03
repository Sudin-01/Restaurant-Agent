# ── Restaurant Agent — Hugging Face Spaces (Docker SDK) ───────────────────────
# HF Spaces expects the app to listen on port 7860.

FROM python:3.12-slim

# Install dependencies first so this layer is cached across code changes.
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy the rest of the project. app.py resolves ../frontend and ../db relative
# to itself, so the backend/ and frontend/ layout must be preserved.
COPY . /app

# HF Spaces runs the container as uid 1000. Give that user ownership so the
# SQLite database (created under /app/db at runtime) is writable.
RUN useradd -m -u 1000 user && chown -R user:user /app
USER user

WORKDIR /app/backend
EXPOSE 7860

# 2 workers is plenty for a demo. --timeout 120 leaves room for slow Gemini
# replies. wsgi:app runs init_db() on import (see wsgi.py).
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "2", "--timeout", "120", "wsgi:app"]
