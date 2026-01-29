@echo off
REM Deployment batch script for Discord Bot on Windows

echo Starting deployment of Discord Bot...

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Check if .env file exists
if not exist ".env" (
    echo Warning: .env file not found. Please create one with DISCORD_TOKEN and AIML_API_KEY
)

REM Run the bot using Gunicorn
echo Starting bot with Gunicorn...
gunicorn main:run -c gunicorn.conf.py

pause