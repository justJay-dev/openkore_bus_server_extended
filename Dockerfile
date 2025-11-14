FROM python:3.10-bullseye

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

#python3 main.py --port 8020 --api-port 9020
CMD ["python3", "main.py", "--port", "8020", "--api-port", "9020"]