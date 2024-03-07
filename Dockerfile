FROM python:3.10

LABEL Maintainer="gounux <contact@guilhemallaman.net>"

WORKDIR /app
COPY . /app

ENV MASTODON_INSTANCE https://botsin.space
ENV MASTODON_ACCESS_TOKEN abcdefgh
ENV AIRPARIF_API_KEY abcdefgh

RUN pip install poetry
RUN poetry install

ENTRYPOINT ["poetry", "run"]
