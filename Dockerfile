FROM python:3

WORKDIR /app

COPY . /app

RUN pip install -U -r requirements.txt

CMD ["python3", "main.py"]