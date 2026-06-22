FROM projectdiscovery/nuclei:latest

USER root

RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

EXPOSE 10000

CMD gunicorn app:app --bind 0.0.0.0:10000
