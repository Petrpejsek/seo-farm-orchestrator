#!/bin/bash
# 🔍 PRE-DEPLOYMENT VALIDATION CHECKS

set -e

echo "🔍 AUTOMATED PRE-DEPLOYMENT CHECKS:"

# Check 1: Python syntax validation
echo "1️⃣ Python syntax validation..."
find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*" | while read file; do
    python3 -m py_compile "$file" || {
        echo "❌ Python syntax error in: $file"
        exit 1
    }
done
echo "✅ Python syntax OK"

# Check 2: Import consistency check
echo "2️⃣ Import consistency check..."
IMPORT_ERRORS=$(grep -r "from api\." . --include="*.py" | grep -v venv | grep -v __pycache__ || true)
if [ ! -z "$IMPORT_ERRORS" ]; then
    echo "❌ CHYBA: Nalezeny 'from api.' importy místo 'from backend.api.'"
    echo "$IMPORT_ERRORS"
    exit 1
fi
echo "✅ Imports OK"

# Check 3: Environment files validation
echo "3️⃣ Environment configuration check..."
if [ ! -f ".env" ]; then
    echo "❌ CHYBA: Root .env soubor neexistuje"
    exit 1
fi

if [ ! -f "backend/.env" ]; then
    echo "❌ CHYBA: Backend .env soubor neexistuje"
    exit 1
fi

# Check required environment variables
REQUIRED_VARS="DATABASE_URL OPENAI_API_KEY"
for var in $REQUIRED_VARS; do
    if ! grep -q "$var=" .env; then
        echo "❌ CHYBA: Chybí povinná proměnná $var v .env"
        exit 1
    fi
done
echo "✅ Environment configuration OK"

# Check 4: Frontend build test (if Node.js is available)
echo "4️⃣ Frontend build test..."
if command -v npm &> /dev/null; then
    cd web-frontend
    if [ -f "package.json" ]; then
        echo "🔧 Testing frontend build..."
        npm install --silent || {
            echo "❌ npm install failed"
            exit 1
        }
        npm run build || {
            echo "❌ Frontend build failed"
            exit 1
        }
        echo "✅ Frontend build OK"
    else
        echo "⚠️ package.json not found, skipping frontend test"
    fi
    cd ..
else
    echo "⚠️ npm not available, skipping frontend test"
fi

# Check 5: Required files validation
echo "5️⃣ Required files validation..."
REQUIRED_FILES=(
    "backend/main.py"
    "production_worker.py"
    "requirements.txt"
    "activities/safe_assistant_activities.py"
    "workflows/assistant_pipeline_workflow.py"
    "backend/api/routes/workflow_run.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ CHYBA: Povinný soubor neexistuje: $file"
        exit 1
    fi
done
echo "✅ Required files OK"

# Check 6: Database schema validation (if prisma is available)
echo "6️⃣ Database schema validation..."
if command -v npx &> /dev/null; then
    cd backend
    if [ -f "prisma/schema.prisma" ]; then
        npx prisma validate || {
            echo "❌ Prisma schema validation failed"
            exit 1
        }
        echo "✅ Database schema OK"
    else
        echo "⚠️ Prisma schema not found, skipping validation"
    fi
    cd ..
else
    echo "⚠️ npx not available, skipping schema validation"
fi

# Check 7: Git status check
echo "7️⃣ Git status check..."
if [ -d ".git" ]; then
    if [ ! -z "$(git status --porcelain)" ]; then
        echo "⚠️ WARNING: Uncommitted changes detected"
        git status --short
        echo "💡 Consider committing changes before deployment"
    else
        echo "✅ Git status clean"
    fi
else
    echo "⚠️ Not a git repository, skipping git check"
fi

echo ""
echo "🎉 ALL PRE-DEPLOYMENT CHECKS PASSED!"
echo "✅ Ready for deployment"

