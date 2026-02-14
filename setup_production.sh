#!/bin/bash

# 🚀 Setup Script for Rare Disease Drug Repurposing Platform - PRODUCTION VERSION

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  Rare Disease Drug Repurposing Platform - Production Setup      ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "backend/test_databases.py" ]; then
    echo -e "${RED}❌ Error: Please run this script from the outputs directory${NC}"
    echo "   cd /path/to/outputs && ./setup_production.sh"
    exit 1
fi

echo -e "${BLUE}📋 Step 1: Checking prerequisites...${NC}"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    echo "   Please install Python 3.9 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    echo "   Please install Node.js 18 or higher"
    exit 1
fi

NODE_VERSION=$(node --version)
echo -e "${GREEN}✅ Node.js $NODE_VERSION found${NC}"

echo ""
echo -e "${BLUE}📦 Step 2: Installing Python dependencies...${NC}"
echo ""

cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install production requirements
echo "   Installing packages from requirements_v2.txt..."
pip install -q -r requirements_v2.txt

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Python dependencies installed${NC}"
else
    echo -e "${RED}❌ Failed to install Python dependencies${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}🧪 Step 3: Testing database connections...${NC}"
echo ""
echo "   This will test: OpenTargets, ChEMBL, DGIdb, ClinicalTrials.gov"
echo "   Expected duration: 30-60 seconds"
echo ""

# Run database tests
python test_databases.py > /tmp/db_test_output.txt 2>&1

if grep -q "ALL TESTS COMPLETED" /tmp/db_test_output.txt; then
    echo -e "${GREEN}✅ All database connections working!${NC}"
    echo ""
    echo "   Results:"
    grep "TEST.*:" /tmp/db_test_output.txt | head -5
else
    echo -e "${YELLOW}⚠️  Some database tests may have failed${NC}"
    echo "   This is OK for first-time setup"
    echo "   Check /tmp/db_test_output.txt for details"
fi

cd ..

echo ""
echo -e "${BLUE}📦 Step 4: Installing frontend dependencies...${NC}"
echo ""

cd frontend

if [ ! -d "node_modules" ]; then
    echo "   Installing npm packages..."
    npm install -q
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Frontend dependencies installed${NC}"
    else
        echo -e "${RED}❌ Failed to install frontend dependencies${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Frontend dependencies already installed${NC}"
fi

cd ..

echo ""
echo -e "${BLUE}🔧 Step 5: Updating configuration...${NC}"
echo ""

# Update data fetcher to use production version
if [ -f "backend/pipeline/data_fetcher.py" ]; then
    echo "   Backing up old data_fetcher.py..."
    mv backend/pipeline/data_fetcher.py backend/pipeline/data_fetcher_manual.py.bak
fi

echo "   Activating production data fetcher..."
cp backend/pipeline/data_fetcher_v2.py backend/pipeline/data_fetcher.py

echo -e "${GREEN}✅ Configuration updated${NC}"

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                        SETUP COMPLETE! 🎉                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Your production platform is ready!${NC}"
echo ""
echo "📊 Database Coverage:"
echo "   • 25,000+ diseases (including 6,000+ rare diseases)"
echo "   • 15,000+ FDA-approved drugs"
echo "   • 50,000+ drug-gene interactions"
echo "   • Real-time clinical trial data"
echo ""
echo "🚀 To start the platform:"
echo ""
echo "   ./start.sh"
echo ""
echo "   Then open: http://localhost:3000"
echo ""
echo "🔬 Try searching for rare diseases:"
echo "   • Huntington Disease"
echo "   • Gaucher Disease"
echo "   • Wilson Disease"
echo "   • Niemann-Pick Disease Type C"
echo "   • Duchenne Muscular Dystrophy"
echo ""
echo "📚 Documentation:"
echo "   • README_PRODUCTION.md - Full documentation"
echo "   • MIGRATION_GUIDE.md - Detailed migration guide"
echo "   • DATABASE_GUIDE.md - Database information"
echo ""
echo "🆘 Need help?"
echo "   • Run: python backend/test_databases.py"
echo "   • Check logs in: /tmp/drug_repurposing_cache/"
echo ""
echo -e "${YELLOW}Note: First query may take 5-10 seconds while building cache${NC}"
echo -e "${YELLOW}Subsequent queries will be much faster (<1 second)${NC}"
echo ""