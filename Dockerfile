FROM python:3.5
ENV PYTHONUNBUFFERED 1
ADD . /code
WORKDIR /code
RUN pip3 install -r requirements.txt