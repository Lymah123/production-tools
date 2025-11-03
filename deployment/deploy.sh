#!/usr/bin/env bash
set -euo pipefail

# ════════════════════════════════════════════════════════════════
# Multi-Platform Deployment Script
# Supports: Linux, macOS, Windows (Git Bash/WSL2)
# ════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/config"
BACKUP_DIR="$SCRIPT_DIR/backups"
LOG_FILE="$SCRIPT_DIR/deploy.log"

# Default values
ENVIRONMENT="production"
PLATFORM=""
SERVICE=""
DRY_RUN=false
BACKUP=false
ROLLBACK_VERSION=""
VERBOSE=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ────────────────────────────────────────────────────────────────
# LOGGING
# ────────────────────────────────────────────────────────────────
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$LOG_FILE"
}

# ────────────────────────────────────────────────────────────────
# PLATFORM DETECTION
# ────────────────────────────────────────────────────────────────
detect_platform() {
    if [[ -z "$PLATFORM" ]]; then
        case "$(uname -s)" in
            Linux*)   PLATFORM="linux" ;;
            Darwin*)  PLATFORM="macos" ;;
            MINGW*|MSYS*|CYGWIN*) PLATFORM="windows" ;;
            *)        
                log_error "Unsupported platform: $(uname -s)"
                exit 1
                ;;
        esac
    fi
    log "Detected platform: $PLATFORM"
}

# ────────────────────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────────────────────
load_config() {
    local config_file="$CONFIG_DIR/${PLATFORM}.conf"
    
    if [[ ! -f "$config_file" ]]; then
        log_error "Config not found: $config_file"
        exit 1
    fi
    
    log "Loading platform config: $config_file"
    # shellcheck source=/dev/null
    source "$config_file"
}

# ────────────────────────────────────────────────────────────────
# BACKUP
# ────────────────────────────────────────────────────────────────
create_backup() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/${SERVICE:-all}_${timestamp}.tar.gz"
    
    mkdir -p "$BACKUP_DIR"
    
    log "Creating backup: $backup_path"
    
    if [[ $DRY_RUN == true ]]; then
        log_info "[DRY RUN] Would create backup at: $backup_path"
        return 0
    fi
    
    # Backup current deployment (customize paths as needed)
    tar -czf "$backup_path" \
        -C "$SCRIPT_DIR/.." \
        --exclude=venv \
        --exclude=__pycache__ \
        --exclude=.git \
        . || {
        log_error "Backup failed"
        return 1
    }
    
    log "Backup created successfully: $backup_path"
    
    # Keep only last 10 backups
    ls -t "$BACKUP_DIR"/*.tar.gz | tail -n +11 | xargs -r rm -f
}

# ────────────────────────────────────────────────────────────────
# ROLLBACK
# ────────────────────────────────────────────────────────────────
perform_rollback() {
    local version="$ROLLBACK_VERSION"
    
    log "Rolling back to version: $version"
    
    # Find backup file
    local backup_file=$(ls -t "$BACKUP_DIR"/*"${version}"*.tar.gz 2>/dev/null | head -n1)
    
    if [[ -z "$backup_file" ]]; then
        log_error "Backup not found for version: $version"
        log_info "Available backups:"
        ls -lh "$BACKUP_DIR"/*.tar.gz 2>/dev/null || log_info "No backups found"
        exit 1
    fi
    
    if [[ $DRY_RUN == true ]]; then
        log_info "[DRY RUN] Would restore from: $backup_file"
        return 0
    fi
    
    log "Restoring from: $backup_file"
    
    # Create safety backup before rollback
    create_backup
    
    # Extract backup
    tar -xzf "$backup_file" -C "$SCRIPT_DIR/.." || {
        log_error "Rollback failed"
        exit 1
    }
    
    log "Rollback completed successfully"
}

# ────────────────────────────────────────────────────────────────
# DEPLOYMENT
# ────────────────────────────────────────────────────────────────
validate_environment() {
    log "Validating environment: $ENVIRONMENT"
    
    # Check required environment variables
    if [[ -z "${APP_NAME:-}" ]]; then
        log_error "APP_NAME not set in environment"
        exit 1
    fi
    
    # Validate Python dependencies
    local python_cmd="python"
    if ! command -v python &>/dev/null; then
        python_cmd="python3"
    fi
    
    if ! $python_cmd -c "import yaml, click, rich" 2>/dev/null; then
        log_error "Required Python packages not installed"
        log_info "Run: pip install -r monitoring/requirements.txt"
        exit 1
    fi
    
    log "Environment validation passed"

}

deploy_service() {
    local service="$SERVICE"
    
    log "Deploying service: ${service:-all services}"
    
    if [[ $DRY_RUN == true ]]; then
        log_info "[DRY RUN] Would deploy to: $ENVIRONMENT"
        log_info "[DRY RUN] Platform: $PLATFORM"
        log_info "[DRY RUN] Service: ${service:-all}"
        return 0
    fi
    
    # Platform-specific deployment logic
    case "$PLATFORM" in
        linux)
            deploy_linux "$service"
            ;;
        macos)
            deploy_macos "$service"
            ;;
        windows)
            deploy_windows "$service"
            ;;
    esac
    
    log "Deployment completed successfully"
}

deploy_linux() {
    local service="$1"
    log "Executing Linux deployment..."
    
    # Example: restart services
    if [[ -n "$service" ]]; then
        if command -v systemctl &>/dev/null; then
            sudo systemctl restart "$service" || log_warn "Could not restart $service"
        fi
    fi
}

deploy_macos() {
    local service="$1"
    log "Executing macOS deployment..."
    
    # Example: restart with launchctl
    if [[ -n "$service" ]]; then
        if command -v launchctl &>/dev/null; then
            launchctl kickstart -k "gui/$(id -u)/$service" 2>/dev/null || log_warn "Could not restart $service"
        fi
    fi
}

deploy_windows() {
    local service="$1"
    log "Executing Windows deployment..."
    
    # Example: restart Windows service
    if [[ -n "$service" ]]; then
        if command -v sc.exe &>/dev/null; then
            sc.exe stop "$service" 2>/dev/null || true
            sc.exe start "$service" 2>/dev/null || log_warn "Could not restart $service"
        fi
    fi
}

# ────────────────────────────────────────────────────────────────
# USAGE
# ────────────────────────────────────────────────────────────────
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Multi-platform deployment automation script.

OPTIONS:
    --env ENV           Environment (production|staging|dev) [default: production]
    --platform PLATFORM Target platform (linux|macos|windows) [auto-detected]
    --service SERVICE   Service name to deploy (optional, deploys all if omitted)
    --dry-run          Show what would be done without executing
    --backup           Create backup before deployment
    --rollback VERSION Rollback to specific version/backup
    --verbose          Enable verbose logging
    -h, --help         Show this help message

EXAMPLES:
    # Deploy to production (auto-detect platform)
    $0 --env production

    # Deploy specific service with backup
    $0 --env staging --service api-server --backup

    # Dry run deployment
    $0 --env production --platform linux --dry-run

    # Rollback to previous version
    $0 --rollback v1.2.3

ENVIRONMENT VARIABLES:
    APP_NAME           Application name (required)
    APP_ENV            Environment override (optional)

EOF
}

# ────────────────────────────────────────────────────────────────
# ARGUMENT PARSING
# ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        --service)
            SERVICE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --backup)
            BACKUP=true
            shift
            ;;
        --rollback)
            ROLLBACK_VERSION="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            set -x
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# ────────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────────
main() {
    log "═══════════════════════════════════════════════════════════"
    log "Starting Deployment"
    log "═══════════════════════════════════════════════════════════"
    
    # Handle rollback
    if [[ -n "$ROLLBACK_VERSION" ]]; then
        detect_platform
        perform_rollback
        exit 0
    fi
    
    # Normal deployment flow
    detect_platform
    load_config
    validate_environment
    
    # Create backup if requested
    if [[ $BACKUP == true ]]; then
        create_backup
    fi
    
    # Deploy
    deploy_service
    
    log "═══════════════════════════════════════════════════════════"
    log "Deployment Complete"
    log "═══════════════════════════════════════════════════════════"
}

# Run main
main