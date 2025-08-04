FROM python:3.10-slim

RUN apt-get update && apt-get -y install cron

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY ./app /app/app
COPY ./worker.py /app/worker.py

COPY ./my_cron /etc/cron/my_cron
COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
