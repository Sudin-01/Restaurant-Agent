#!/bin/bash
# ── AI Restaurant Manager — Setup Script ──────────────────────────────────────

set -e

echo ""
echo "🍜  AI Restaurant Manager — Setup"
echo "══════════════════════════════════"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required. Install from https://python.org"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

echo "✅ Virtual environment created"

# Install dependencies
echo ""
echo "📥 Installing dependencies..."
pip install -r backend/requirements.txt --quiet

echo "✅ Dependencies installed"

# Copy .env if not exists
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo ""
    echo "📝 Created backend/.env from template"
    echo "   ⚠️  Please edit backend/.env with your API keys!"
fi

# Create db directory
mkdir -p db

echo ""
echo "══════════════════════════════════"
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit backend/.env with your API keys"
echo "  2. Run: source venv/bin/activate"
echo "  3. Run: cd backend && python app.py"
echo "  4. Run ngrok: ngrok http 5000"
echo "  5. Open: frontend/dashboard.html"
echo ""
echo "📖 Full guide: README.md"
echo ""
