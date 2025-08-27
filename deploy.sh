#!/bin/bash
set -e

# Production deployment script for kiro-project
echo "🚀 Starting production deployment for kiro-project..."

# Configuration
IMAGE_NAME="kiro-project"
CONTAINER_NAME="kiro-processor"
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    if [ ! -f ".env" ]; then
        warning ".env file not found. Creating from template..."
        cat > .env << EOF
# Application Configuration
SOURCE_FOLDER=/app/data/source
SAVED_FOLDER=/app/data/saved
ERROR_FOLDER=/app/data/error
LOG_LEVEL=INFO

# RAG Store Configuration
GOOGLE_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
EOF
        warning "Please edit .env file with your actual API keys before running"
    fi
    
    success "Prerequisites check completed"
}

# Backup existing data
backup_data() {
    if [ -d "data" ] && [ "$(ls -A data)" ]; then
        log "Creating backup of existing data..."
        mkdir -p "$BACKUP_DIR"
        cp -r data logs "$BACKUP_DIR/" 2>/dev/null || true
        success "Backup created at $BACKUP_DIR"
    fi
}

# Build and deploy
deploy() {
    log "Building Docker image..."
    docker-compose build --no-cache
    
    log "Stopping existing containers..."
    docker-compose down --remove-orphans
    
    log "Starting new deployment..."
    docker-compose up -d
    
    # Wait for health check
    log "Waiting for application to be healthy..."
    for i in {1..30}; do
        if docker-compose ps --format json | jq -e '.[] | select(.Service=="kiro-app" and .Health=="healthy")' > /dev/null 2>&1; then
            success "Application is healthy and running!"
            break
        fi
        if [ $i -eq 30 ]; then
            error "Application failed to become healthy within 5 minutes"
            docker-compose logs kiro-app
            exit 1
        fi
        sleep 10
    done
}

# Show deployment status
show_status() {
    log "Deployment Status:"
    docker-compose ps
    echo
    log "Application logs (last 20 lines):"
    docker-compose logs --tail=20 kiro-app
}

# Cleanup old images
cleanup() {
    log "Cleaning up old Docker images..."
    docker image prune -f
    success "Cleanup completed"
}

# Main deployment flow
main() {
    check_prerequisites
    backup_data
    deploy
    show_status
    cleanup
    
    success "🎉 Production deployment completed successfully!"
    echo
    log "Useful commands:"
    echo "  View logs:     docker-compose logs -f kiro-app"
    echo "  Stop service:  docker-compose down"
    echo "  Restart:       docker-compose restart kiro-app"
    echo "  Enter shell:   docker-compose exec kiro-app /bin/bash"
}

# Handle script arguments
case "${1:-deploy}" in
    deploy)
        main
        ;;
    status)
        show_status
        ;;
    logs)
        docker-compose logs -f kiro-app
        ;;
    stop)
        log "Stopping services..."
        docker-compose down
        success "Services stopped"
        ;;
    restart)
        log "Restarting services..."
        docker-compose restart
        success "Services restarted"
        ;;
    backup)
        backup_data
        ;;
    *)
        echo "Usage: $0 {deploy|status|logs|stop|restart|backup}"
        echo
        echo "Commands:"
        echo "  deploy   - Full deployment (default)"
        echo "  status   - Show current status"
        echo "  logs     - Follow application logs"
        echo "  stop     - Stop all services"
        echo "  restart  - Restart services"
        echo "  backup   - Backup data only"
        exit 1
        ;;
esac
