FROM python:3.9.6-alpine

WORKDIR /codeapp

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV HOME=/home/codeapp
ENV CODEAPP_HOME=/home/codeapp/web
# Create the codeapp user and home directory
RUN addgroup -S codeapp && adduser -S codeapp -G codeapp
RUN mkdir -p $CODEAPP_HOME/static && chown -R codeapp:codeapp $HOME

COPY ./requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

USER codeapp

