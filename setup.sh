#!/usr/bin/env bash
set -e

# ANSI Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}=======================================${NC}"
echo -e "${CYAN}       GitLabInsight Setup Script      ${NC}"
echo -e "${CYAN}=======================================${NC}\n"

# 1. Check prerequisites
echo -e "${CYAN}→ Checking prerequisites...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is required but not installed.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Found python3${NC}"

if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: 'uv' package manager is required. Please install it: https://docs.astral.sh/uv/${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Found uv${NC}\n"

# 2. Install dependencies
echo -e "${CYAN}→ Installing dependencies...${NC}"
uv sync --dev
echo -e "${GREEN}✓ Dependencies installed successfully.${NC}\n"

# 3. Environment configuration
echo -e "${CYAN}→ Checking environment configuration...${NC}"
if [ -f .env ]; then
    echo -e "${GREEN}✓ .env already exists. Preserving your configuration.${NC}\n"
else
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env from .env.example template.${NC}\n"
    else
        echo -e "${YELLOW}⚠ .env.example not found. Skipping .env creation.${NC}\n"
    fi
fi

# 4. Local Demo Setup (Optional)
echo -e "${CYAN}→ Local Demo Setup${NC}"
echo "Would you like to seed synthetic test data to explore the dashboard locally?"
echo -e "${YELLOW}Note: This is recommended if you don't have a GitLab instance ready.${NC}"
read -p "Generate synthetic data now? [y/N]: " seed_choice

if [[ "$seed_choice" =~ ^[Yy]$ ]]; then
    echo -e "\n${CYAN}Generating synthetic data...${NC}"
    uv run python tools/seeder.py --count 1000 --inject-errors
    echo -e "${GREEN}✓ Synthetic data generated.${NC}\n"
    
    echo -e "${CYAN}Running analytics processor...${NC}"
    uv run python app/processor/main.py
    echo -e "${GREEN}✓ Data processing complete.${NC}\n"
    
    echo -e "${GREEN}=======================================${NC}"
    echo -e "${GREEN}           Setup Complete!             ${NC}"
    echo -e "${GREEN}=======================================${NC}"
    echo -e "\nTo start the dashboard, run:"
    echo -e "  ${CYAN}uv run streamlit run app/dashboard/main.py${NC}"
    echo -e "\nThen open http://localhost:8501 in your browser."
else
    echo -e "\n${YELLOW}Skipped synthetic data generation.${NC}\n"
    echo -e "${GREEN}=======================================${NC}"
    echo -e "${GREEN}           Setup Complete!             ${NC}"
    echo -e "${GREEN}=======================================${NC}"
    echo -e "\nNext steps for live GitLab sync:"
    echo -e "1. Edit ${CYAN}.env${NC} and add your GITLAB_URL, GITLAB_TOKEN, and PROJECT_IDS."
    echo -e "2. Run the collector: ${CYAN}uv run python app/collector/orchestrator.py${NC}"
    echo -e "3. Run the processor: ${CYAN}uv run python app/processor/main.py${NC}"
    echo -e "4. Start the dashboard: ${CYAN}uv run streamlit run app/dashboard/main.py${NC}"
fi

echo -e "\nFor full documentation, see README.md."
