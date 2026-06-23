FROM projectdiscovery/nuclei:latest

WORKDIR /app

COPY requirements.txt .

RUN apk add --no-cache python3 py3-pip \
    && pip3 install --break-system-packages -r requirements.txt

COPY . .

RUN mkdir -p results

ENV PORT=10000

CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120
