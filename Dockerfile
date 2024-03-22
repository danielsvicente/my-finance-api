FROM python:3.10

WORKDIR /my-finance

COPY ./requirements.txt /my-finance/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /my-finance/requirements.txt

COPY ./app /my-finance/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]