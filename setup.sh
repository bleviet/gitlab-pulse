#!/usr/bin/env bash
set -e

# ANSI Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ----------------------------------------------------
# LOGGING HELPERS
# ----------------------------------------------------
log_step() {
    echo -e "\n${CYAN}→ $1${NC}"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

log_error() {
    echo -e "${RED}Error: $1${NC}"
}

log_info() {
    echo -e "$1"
}

# ----------------------------------------------------
# SETUP FUNCTIONS
# ----------------------------------------------------
check_prerequisites() {
    log_step "Checking prerequisites..."
    if ! command -v python3 &> /dev/null; then
        log_error "python3 is required but not installed."
        exit 1
    fi
    log_success "Found python3"

    if ! command -v uv &> /dev/null; then
        log_error "'uv' package manager is required. Please install it: https://docs.astral.sh/uv/"
        exit 1
    fi
    log_success "Found uv"
}

install_dependencies() {
    log_step "Installing dependencies..."
    
    # [COMMAND] Install python dependencies
    uv sync
    
    log_success "Dependencies installed successfully."
}

setup_environment() {
    log_step "Checking environment configuration..."
    
    if [ -f .env ]; then
        log_success ".env already exists. Preserving your configuration."
    else
        if [ -f .env.example ]; then
            # [COMMAND] Copy environment template
            cp .env.example .env
            log_success "Created .env from .env.example template."
        else
            log_warning ".env.example not found. Skipping .env creation."
        fi
    fi
}

generate_test_data() {
    log_info "\n${CYAN}Generating synthetic data...${NC}"
    # [COMMAND] Run Seeder
    uv run python tools/seeder.py --count 1000 --inject-errors
    log_success "Synthetic data generated."
    
    log_info "\n${CYAN}Running analytics processor...${NC}"
    # [COMMAND] Run Processor
    uv run python app/processor/main.py
    log_success "Data processing complete."
}

setup_local_data() {
    log_step "Local Demo Setup"
    
    if ls data/processed/issues_*.parquet 1> /dev/null 2>&1; then
        log_success "Local test data already exists."
        read -p "Would you like to remove and regenerate it? [y/N]: " regen_choice
        
        if [[ "$regen_choice" =~ ^[Yy]$ ]]; then
            log_info "\n${CYAN}Removing old data...${NC}"
            # [COMMAND] Clear previous parquets
            rm -f data/processed/issues_*.parquet
            rm -f data/analytics/*.parquet
            generate_test_data
        fi
        print_success_local
    else
        log_info "Would you like to seed synthetic test data to explore the dashboard locally?"
        log_warning "Note: This is recommended if you don't have a GitLab instance ready."
        read -p "Generate synthetic data now? [y/N]: " seed_choice

        if [[ "$seed_choice" =~ ^[Yy]$ ]]; then
            generate_test_data
            print_success_local
        else
            log_warning "Skipped synthetic data generation."
            print_success_manual
        fi
    fi
}

# ----------------------------------------------------
# FINAL OUTPUTS
# ----------------------------------------------------
print_success_local() {
    echo -e "\n${GREEN}=======================================${NC}"
    echo -e "${GREEN}           Setup Complete!             ${NC}"
    echo -e "${GREEN}=======================================${NC}"
    echo -e "\nTo start the dashboard, run:"
    echo -e "  ${CYAN}uv run streamlit run app/dashboard/main.py${NC}"
    echo -e "\nThen open http://localhost:8501 in your browser."
    echo -e "\nFor full documentation, see README.md."
}

print_success_manual() {
    echo -e "\n${GREEN}=======================================${NC}"
    echo -e "${GREEN}           Setup Complete!             ${NC}"
    echo -e "${GREEN}=======================================${NC}"
    echo -e "\nNext steps for live GitLab sync:"
    echo -e "1. Edit ${CYAN}.env${NC} and add your GITLAB_URL, GITLAB_TOKEN, and PROJECT_IDS."
    echo -e "2. Run the collector: ${CYAN}uv run python app/collector/orchestrator.py${NC}"
    echo -e "3. Run the processor: ${CYAN}uv run python app/processor/main.py${NC}"
    echo -e "4. Start the dashboard: ${CYAN}uv run streamlit run app/dashboard/main.py${NC}"
    echo -e "\nFor full documentation, see README.md."
}

# ----------------------------------------------------
# MAIN EXECUTION
# ----------------------------------------------------
echo -e "${CYAN}=======================================${NC}"
echo -e "${CYAN}       GitLab Pulse Setup Script      ${NC}"
echo -e "${CYAN}=======================================${NC}"

check_prerequisites
install_dependencies
setup_environment
setup_local_data
