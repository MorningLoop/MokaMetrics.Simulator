#!/bin/bash

# MokaMetrics Simulator - Docker Deployment Script
# This script helps you deploy the MokaMetrics Simulator using Docker Compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Docker and Docker Compose
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        echo "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    print_success "Dependencies check passed"
}

# Function to create .env file if it doesn't exist
setup_environment() {
    if [ ! -f .env ]; then
        print_status "Creating .env file from template..."
        if [ -f .env.example ]; then
            cp .env.example .env
            print_success ".env file created from template"
            print_warning "Please edit .env file with your configuration before running again"
            print_warning "Especially set MOKAMETRICS_API_KEY if you plan to use the API"
            echo ""
            echo "Edit the .env file and run this script again:"
            echo "  nano .env"
            echo "  ./docker-deploy.sh"
            exit 0
        else
            print_warning ".env.example not found, creating basic .env file"
            cat > .env << EOF
# MokaMetrics Simulator Environment Configuration
MOKAMETRICS_API_KEY=your_api_key_here
ENABLE_API=false
LOG_LEVEL=INFO
KAFKA_BROKER=165.227.168.240:29093
EOF
            print_success "Basic .env file created"
            print_warning "Please edit .env file with your configuration"
            exit 0
        fi
    fi
    print_success "Environment configuration found"
}

# Function to create logs directory
setup_directories() {
    print_status "Setting up directories..."
    mkdir -p logs
    print_success "Directories created"
}

# Function to build and start the application
deploy() {
    local mode=${1:-production}
    
    print_status "Building Docker image..."
    if [ "$mode" = "dev" ]; then
        docker-compose -f docker-compose.dev.yml build
    else
        docker-compose build
    fi
    
    print_status "Starting MokaMetrics Simulator..."
    if [ "$mode" = "dev" ]; then
        docker-compose -f docker-compose.dev.yml up -d
    else
        docker-compose up -d
    fi
    
    # Wait for the container to start
    print_status "Waiting for container to start..."
    sleep 10
    
    # Check if container is running
    if [ "$mode" = "dev" ]; then
        container_name="mokametrics-simulator-dev"
    else
        container_name="mokametrics-simulator"
    fi
    
    if docker ps | grep -q "$container_name"; then
        print_success "MokaMetrics Simulator is running!"
        echo ""
        echo "🌐 Web Interface: http://localhost:8081"
        echo "🏥 Health Check: http://localhost:8081/health"
        echo ""
        echo "📊 To view logs:"
        echo "  docker-compose logs -f"
        echo ""
        echo "🛑 To stop:"
        echo "  docker-compose down"
        
        if [ "$mode" = "dev" ]; then
            echo ""
            echo "🎛️  Development mode features:"
            echo "  - Live code reloading"
            echo "  - Debug logging"
            echo "  - Kafka UI available (use --kafka-ui flag)"
        fi
    else
        print_error "Failed to start container"
        echo ""
        echo "Check logs with:"
        echo "  docker-compose logs"
        exit 1
    fi
}

# Function to stop the application
stop() {
    print_status "Stopping MokaMetrics Simulator..."
    docker-compose down
    print_success "MokaMetrics Simulator stopped"
}

# Function to show status
status() {
    print_status "Checking container status..."
    docker-compose ps
}

# Function to show logs
logs() {
    docker-compose logs -f
}

# Function to show help
show_help() {
    echo "MokaMetrics Simulator - Docker Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  deploy, start    Deploy and start the simulator (default)"
    echo "  dev              Deploy in development mode"
    echo "  stop             Stop the simulator"
    echo "  restart          Restart the simulator"
    echo "  status           Show container status"
    echo "  logs             Show container logs"
    echo "  clean            Stop and remove containers, networks, and images"
    echo "  help             Show this help message"
    echo ""
    echo "Options:"
    echo "  --kafka-ui       Start with Kafka UI (development mode only)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Deploy in production mode"
    echo "  $0 dev                # Deploy in development mode"
    echo "  $0 dev --kafka-ui     # Deploy in dev mode with Kafka UI"
    echo "  $0 stop               # Stop the simulator"
    echo "  $0 logs               # View logs"
}

# Main script logic
main() {
    local command=${1:-deploy}
    local kafka_ui=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --kafka-ui)
                kafka_ui=true
                shift
                ;;
            *)
                command=$1
                shift
                ;;
        esac
    done
    
    case $command in
        deploy|start)
            check_dependencies
            setup_environment
            setup_directories
            deploy production
            ;;
        dev)
            check_dependencies
            setup_environment
            setup_directories
            if [ "$kafka_ui" = true ]; then
                print_status "Starting with Kafka UI..."
                docker-compose -f docker-compose.dev.yml --profile kafka-ui up -d --build
                print_success "Development environment with Kafka UI started!"
                echo "🌐 Web Interface: http://localhost:8081"
                echo "🎛️  Kafka UI: http://localhost:8080"
            else
                deploy dev
            fi
            ;;
        stop)
            stop
            ;;
        restart)
            stop
            sleep 2
            deploy production
            ;;
        status)
            status
            ;;
        logs)
            logs
            ;;
        clean)
            print_status "Cleaning up Docker resources..."
            docker-compose down --rmi all --volumes --remove-orphans
            print_success "Cleanup completed"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
