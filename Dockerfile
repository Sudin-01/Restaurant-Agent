# ── Restaurant Agent — Docker image for Render / any Docker host ──────────────
# Binds to $PORT if the host sets one (Render does), else defaults to 7860.

FROM python:3.12-slim

# Install dependencies first so this layer is cached across code changes.
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy the rest of the project. app.py resolves ../frontend and ../db relative
# to itself, so the backend/ and frontend/ layout must be preserved.
COPY . /app

# Run as an unprivileged user. uid 1000 also keeps /app/db writable on hosts
# (like HF Spaces) that run the container as that uid.
RUN useradd -m -u 1000 user && chown -R user:user /app
USER user

WORKDIR /app/backend
ENV PORT=7860
EXPOSE 7860

# Shell form so $PORT expands. Render injects its own $PORT; elsewhere it falls
# back to 7860. --timeout 120 leaves room for slow Gemini replies. wsgi:app runs
# init_db() on import (see wsgi.py).
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 wsgi:app
