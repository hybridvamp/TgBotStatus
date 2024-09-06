FROM python:3

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip
RUN pip install -U -r requirements.txt
RUN mkdir files

CMD ["python3", "main.py"]