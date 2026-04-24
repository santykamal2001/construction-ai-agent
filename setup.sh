#!/bin/bash
# Setup script for Construction AI Agent Demo

echo "🏗️  Setting up Construction AI Agent Demo..."
echo "============================================"

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create data directory
mkdir -p data

# Copy .env example
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  Created .env file. Add your ANTHROPIC_API_KEY to .env"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your ANTHROPIC_API_KEY"
echo "  2. Run: source venv/bin/activate"
echo "  3. Run: streamlit run app.py"
