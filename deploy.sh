#!/bin/bash

# Deployment script for Discord Bot

echo "Starting deployment of Discord Bot..."

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Please create one with DISCORD_TOKEN and AIML_API_KEY"
fi

# Run the bot using Gunicorn
echo "Starting bot with Gunicorn..."
gunicorn main:run -c gunicorn.conf.py