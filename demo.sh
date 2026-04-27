#!/bin/bash
# Demo Runner for Claims Reconciliation Agent
# This script runs a complete demo of the reconciliation pipeline.

set -e  # Exit on error

echo "🏥 Claims Reconciliation Agent - Demo"
echo "======================================"
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Must run from project root directory"
    exit 1
fi

# Step 1: Generate sample data if not present
echo "📁 Step 1: Checking sample data..."
if [ ! -f "src/data/sample_claims.csv" ] || [ ! -f "src/data/sample_payments.csv" ]; then
    echo "   Generating sample data..."
    uv run python scripts/generate_sample_data.py
else
    echo "   ✅ Sample data already exists"
fi

# Step 2: Run reconciliation CLI
echo ""
echo "🔍 Step 2: Running reconciliation..."
uv run python src/app/cli.py \
    --claims src/data/sample_claims.csv \
    --payments src/data/sample_payments.csv \
    --format all

# Step 3: Show generated reports
echo ""
echo "📄 Step 3: Generated reports:"
ls -lh reports/*.csv reports/*.json reports/*.pdf 2>/dev/null || echo "   (some formats may be missing if dependencies not installed)"

echo ""
echo "✅ Demo complete!"
echo ""
echo "💡 To explore further:"
echo "   - Run Streamlit UI: uv run streamlit run src/app/streamlit_app.py"
echo "   - Run tests:      uv run pytest"
echo "   - Clean reports:  make clean"
