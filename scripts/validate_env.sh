#!/bin/bash
# Validate environment variables

# Check if python is available
if ! command -v python &> /dev/null; then
    echo "Error: Python is not installed"
    exit 1
fi

# Create a temporary Python script to validate env variables
cat << EOF > /tmp/validate_env.py
from ModularMind.API.config.settings import get_settings
import sys

try:
    settings = get_settings()
    print(f"Environment validation successful!")
    print(f"Application: {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"Debug mode: {'Enabled' if settings.DEBUG else 'Disabled'}")
    print(f"Database: {settings.DATABASE_URL}")
    print(f"Redis: {settings.REDIS_URL}")
    print(f"Vector DB: {settings.VECTOR_DB_TYPE}")
    print(f"Upload directory: {settings.UPLOAD_DIR}")
    print(f"Log level: {settings.LOG_LEVEL}")
    sys.exit(0)
except Exception as e:
    print(f"Error validating environment variables: {e}")
    sys.exit(1)
EOF

# Run the validation script
python /tmp/validate_env.py
exit_code=$?

# Clean up
rm /tmp/validate_env.py

# Exit with the script's exit code
exit $exit_code