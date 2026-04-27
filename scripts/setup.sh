#!/bin/bash
# Quick setup script for Claims Reconciliation Agent

echo "🏥 Claims Reconciliation Agent - Setup"
echo "======================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10+ from python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Python $PYTHON_VERSION found"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment exists"
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install dev dependencies (optional)
echo "🔨 Installing dev tools..."
pip install -e ".[dev]" 2>/dev/null || true

# Generate sample data
echo "🧪 Generating sample data..."
python scripts/generate_sample_data.py

# Create directories
mkdir -p reports logs

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Next steps:"
echo "   1. Run the Streamlit app:"
echo "      streamlit run src/app/streamlit_app.py"
echo ""
echo "   2. Or use the CLI:"
echo "      python src/app/cli.py --claims src/data/sample_claims.csv --payments src/data/sample_payments.csv"
echo ""
echo "📚 Read the docs:"
echo "   - docs/demo_guide.md"
echo "   - docs/architecture.md"
echo "   - README.md"
echo ""
