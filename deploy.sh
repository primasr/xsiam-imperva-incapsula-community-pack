#!/usr/bin/env bash
# ==============================================================================
# Cortex XSIAM Content Pack Deployment & Management Automation
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACK_PATH="Packs/ImpervaIncapsula"
VENV_PATH="${SCRIPT_DIR}/venv-demisto"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_info()    { echo -e "${CYAN}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

show_help() {
    echo -e "${BOLD}Cortex XSIAM Content Pack Deployment CLI${NC}"
    echo ""
    echo -e "${BOLD}Usage:${NC} ./deploy.sh [COMMAND]"
    echo ""
    echo -e "${BOLD}Commands:${NC}"
    echo -e "  ${GREEN}dev${NC}       Validate and deploy pack to the DEVELOPMENT tenant (.env.dev / .env)"
    echo -e "  ${RED}prod${NC}      Validate and deploy pack to the PRODUCTION tenant (.env.prod)"
    echo -e "  ${BLUE}validate${NC}  Run local Demisto SDK validation checks only"
    echo -e "  ${CYAN}zip${NC}       Compile a standalone .zip package into Packs/uploadable_packs/"
    echo -e "  ${YELLOW}help${NC}      Display this help message"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  ./deploy.sh dev"
    echo "  ./deploy.sh prod"
    echo "  ./deploy.sh validate"
    echo "  ./deploy.sh zip"
    echo ""
}

# 1. Check & Activate Virtual Environment
if [ -f "${VENV_PATH}/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "${VENV_PATH}/bin/activate"
    export PATH="${VENV_PATH}/bin:${PATH}"
else
    print_error "Virtual environment not found at ${VENV_PATH}."
    print_error "Please create the venv and install demisto-sdk first."
    exit 1
fi

export DEMISTO_SDK_CONTENT_PATH="${SCRIPT_DIR}"
export DEMISTO_SDK_IGNORE_CONTENT_WARNING=True

TARGET="${1:-dev}"

case "$TARGET" in
    dev|development)
        if [ -f "${SCRIPT_DIR}/.env.dev" ]; then
            ENV_FILE="${SCRIPT_DIR}/.env.dev"
        elif [ -f "${SCRIPT_DIR}/.env" ]; then
            ENV_FILE="${SCRIPT_DIR}/.env"
        else
            print_error "No .env.dev or .env file found at ${SCRIPT_DIR}."
            exit 1
        fi

        echo -e "${CYAN}=====================================================${NC}"
        echo -e "${CYAN}  Target: ${BOLD}DEVELOPMENT TENANT${NC}"
        echo -e "${CYAN}  Env:    ${ENV_FILE}${NC}"
        echo -e "${CYAN}=====================================================${NC}"
        ;;

    prod|production)
        ENV_FILE="${SCRIPT_DIR}/.env.prod"
        if [ ! -f "${ENV_FILE}" ]; then
            print_error "Production environment file not found: ${ENV_FILE}"
            print_info "Create .env.prod with your production XSIAM API credentials."
            exit 1
        fi

        echo -e "${RED}=====================================================${NC}"
        echo -e "${RED}  ⚠️  Target: ${BOLD}PRODUCTION TENANT${NC}"
        echo -e "${RED}  Env:    ${ENV_FILE}${NC}"
        echo -e "${RED}=====================================================${NC}"
        echo ""
        read -r -p "$(echo -e "${YELLOW}Are you sure you want to deploy to PRODUCTION? [y/N]: ${NC}")" confirm
        if [[ ! "$confirm" =~ ^[yY](es)?$ ]]; then
            print_warning "Production deployment cancelled by user."
            exit 0
        fi
        ;;

    val|validate|test)
        print_info "Running validation checks on ${PACK_PATH}..."
        demisto-sdk validate -i "${PACK_PATH}"
        print_success "Validation completed successfully!"
        exit 0
        ;;

    zip|package)
        print_info "Compiling standalone pack archive..."
        mkdir -p "${SCRIPT_DIR}/Packs/uploadable_packs"
        demisto-sdk zip-packs -i "${PACK_PATH}" -o "${SCRIPT_DIR}/Packs/uploadable_packs" || true
        if [ -f "${SCRIPT_DIR}/Packs/uploadable_packs/uploadable_packs/ImpervaIncapsula.zip" ]; then
            mv "${SCRIPT_DIR}/Packs/uploadable_packs/uploadable_packs/ImpervaIncapsula.zip" "${SCRIPT_DIR}/Packs/uploadable_packs/ImpervaIncapsula.zip"
        fi
        rm -rf "${SCRIPT_DIR}/Packs/uploadable_packs/uploadable_packs" "${SCRIPT_DIR}/Packs/uploadable_packs/content_packs"
        if [ -f "${SCRIPT_DIR}/Packs/uploadable_packs/ImpervaIncapsula.zip" ]; then
            print_success "Pack compiled to Packs/uploadable_packs/ImpervaIncapsula.zip"
        else
            print_error "Failed to locate compiled pack zip."
            exit 1
        fi
        exit 0
        ;;

    help|-h|--help)
        show_help
        exit 0
        ;;

    *)
        print_error "Unknown command: ${TARGET}"
        show_help
        exit 1
        ;;
esac

# 2. Load Environment Credentials & Handle python-dotenv
ORIG_ENV_EXISTS=false
if [ -f "${SCRIPT_DIR}/.env" ]; then
    ORIG_ENV_EXISTS=true
    cp "${SCRIPT_DIR}/.env" "${SCRIPT_DIR}/.env.orig_backup"
fi
cp "${ENV_FILE}" "${SCRIPT_DIR}/.env"

cleanup_env() {
    if [ "${ORIG_ENV_EXISTS}" = true ] && [ -f "${SCRIPT_DIR}/.env.orig_backup" ]; then
        mv "${SCRIPT_DIR}/.env.orig_backup" "${SCRIPT_DIR}/.env"
    else
        rm -f "${SCRIPT_DIR}/.env" "${SCRIPT_DIR}/.env.orig_backup"
    fi
}
trap cleanup_env EXIT

# shellcheck disable=SC2046
export $(grep -v '^#' "${ENV_FILE}" 2>/dev/null | xargs -d '\n')

if [ -z "${DEMISTO_BASE_URL}" ] || [ -z "${DEMISTO_API_KEY}" ]; then
    print_error "DEMISTO_BASE_URL or DEMISTO_API_KEY is empty in ${ENV_FILE}."
    exit 1
fi

print_info "Target Host: ${DEMISTO_BASE_URL}"

# 3. Run Validation
print_info "1/2 Running Demisto SDK validation..."
demisto-sdk validate -i "${PACK_PATH}"

# 4. Upload Pack to Target Tenant
print_info "2/2 Uploading ${PACK_PATH} to Cortex XSIAM (${TARGET})..."
demisto-sdk upload -i "${PACK_PATH}" -z --xsiam --insecure

echo ""
print_success "🚀 Content pack successfully deployed to ${BOLD}${TARGET^^}${NC} tenant!"
