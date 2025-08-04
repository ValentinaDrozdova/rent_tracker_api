#!/bin/sh

set -e

# Загружаем наши Cron-задания из файла в систему
echo "Loading cron jobs from /etc/cron/my_cron"
crontab /etc/cron/my_cron

# Запускаем сам сервис Cron в фоновом режиме
echo "Starting cron daemon..."
cron

echo "Starting Uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 80