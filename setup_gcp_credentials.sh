#!/bin/bash
# Script to help set up Google Cloud credentials for REanna Router

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}REanna Router - Google Cloud Credentials Setup${NC}"
echo "This script will help set up Google Cloud credentials for the application."
echo

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed.${NC}"
    echo "Please install the Google Cloud SDK from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is logged in to gcloud
echo "Checking if you're logged in to Google Cloud..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo -e "${YELLOW}You need to log in to Google Cloud first.${NC}"
    echo "Running: gcloud auth login"
    gcloud auth login
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to log in to Google Cloud.${NC}"
        exit 1
    fi
fi

# Get current project
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
echo -e "${GREEN}Current GCP Project:${NC} $CURRENT_PROJECT"

# Ask if user wants to use a different project
read -p "Do you want to use a different project? (y/N): " change_project
if [[ $change_project =~ ^[Yy]$ ]]; then
    # List available projects
    echo "Available projects:"
    gcloud projects list --format="table(projectId,name)"
    
    # Ask for project ID
    read -p "Enter the project ID you want to use: " project_id
    gcloud config set project $project_id
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to set project.${NC}"
        exit 1
    fi
    CURRENT_PROJECT=$project_id
fi

# Check if required APIs are enabled
echo "Checking if required APIs are enabled..."
REQUIRED_APIS=("maps.googleapis.com" "routes.googleapis.com" "routeoptimization.googleapis.com")
APIS_TO_ENABLE=()

for api in "${REQUIRED_APIS[@]}"; do
    if ! gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
        APIS_TO_ENABLE+=($api)
    fi
done

# Enable required APIs if needed
if [ ${#APIS_TO_ENABLE[@]} -gt 0 ]; then
    echo -e "${YELLOW}The following APIs need to be enabled:${NC}"
    for api in "${APIS_TO_ENABLE[@]}"; do
        echo "  - $api"
    done
    
    read -p "Do you want to enable these APIs now? (Y/n): " enable_apis
    if [[ ! $enable_apis =~ ^[Nn]$ ]]; then
        for api in "${APIS_TO_ENABLE[@]}"; do
            echo "Enabling $api..."
            gcloud services enable $api
            if [ $? -ne 0 ]; then
                echo -e "${RED}Failed to enable $api.${NC}"
                exit 1
            fi
        done
    else
        echo -e "${YELLOW}Please enable these APIs manually in the Google Cloud Console.${NC}"
    fi
fi

# Ask if user wants to create a service account
echo
echo "For production use, it's recommended to create a service account with limited permissions."
read -p "Do you want to create a new service account? (Y/n): " create_sa
if [[ ! $create_sa =~ ^[Nn]$ ]]; then
    # Ask for service account name
    read -p "Enter a name for the service account (e.g., reanna-router): " sa_name
    
    # Create service account
    echo "Creating service account $sa_name..."
    gcloud iam service-accounts create $sa_name \
        --display-name="REanna Router Service Account"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to create service account.${NC}"
        exit 1
    fi
    
    # Get service account email
    SA_EMAIL="$sa_name@$CURRENT_PROJECT.iam.gserviceaccount.com"
    
    # Grant necessary roles
    echo "Granting necessary roles to the service account..."
    ROLES=("roles/maps.routeOptimizer" "roles/maps.routesUser" "roles/maps.viewer")
    
    for role in "${ROLES[@]}"; do
        gcloud projects add-iam-policy-binding $CURRENT_PROJECT \
            --member="serviceAccount:$SA_EMAIL" \
            --role="$role"
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to grant $role to the service account.${NC}"
            exit 1
        fi
    done
    
    # Create and download key
    echo "Creating and downloading service account key..."
    mkdir -p keys
    gcloud iam service-accounts keys create ./google-credentials.json \
        --iam-account=$SA_EMAIL
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to create service account key.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Service account key saved to ./google-credentials.json${NC}"
    echo "Make sure to keep this file secure and never commit it to version control."
    
    # Update .env file
    if [ -f .env ]; then
        if grep -q "GOOGLE_APPLICATION_CREDENTIALS" .env; then
            sed -i.bak "s|GOOGLE_APPLICATION_CREDENTIALS=.*|GOOGLE_APPLICATION_CREDENTIALS=./google-credentials.json|" .env
        else
            echo "GOOGLE_APPLICATION_CREDENTIALS=./google-credentials.json" >> .env
        fi
        echo -e "${GREEN}Updated .env file with credentials path.${NC}"
    else
        echo "GOOGLE_APPLICATION_CREDENTIALS=./google-credentials.json" > .env
        echo -e "${GREEN}Created .env file with credentials path.${NC}"
    fi
else
    # Use application default credentials
    echo "Setting up application default credentials..."
    gcloud auth application-default login
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to set up application default credentials.${NC}"
        exit 1
    fi
    
    # Get the path to the application default credentials
    ADC_PATH=$(gcloud info --format="value(config.paths.global_config_dir)")/application_default_credentials.json
    
    # Update .env file
    if [ -f .env ]; then
        if grep -q "GOOGLE_APPLICATION_CREDENTIALS" .env; then
            sed -i.bak "s|GOOGLE_APPLICATION_CREDENTIALS=.*|GOOGLE_APPLICATION_CREDENTIALS=$ADC_PATH|" .env
        else
            echo "GOOGLE_APPLICATION_CREDENTIALS=$ADC_PATH" >> .env
        fi
        echo -e "${GREEN}Updated .env file with credentials path.${NC}"
    else
        echo "GOOGLE_APPLICATION_CREDENTIALS=$ADC_PATH" > .env
        echo -e "${GREEN}Created .env file with credentials path.${NC}"
    fi
fi

echo
echo -e "${GREEN}Setup complete!${NC}"
echo "You can now run the application with Docker Compose:"
echo "  docker-compose up -d"
echo
echo "If you need to update your Google Cloud credentials in the future, run this script again."
