# Air Bot - Air quality bot, posts map predictions on mapstodon.space

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

## Install

The program uses [poetry](https://python-poetry.org/), that can be installed like this :

```shell
python3 -m pip install poetry
```

## Setup

Install dependencies :

```shell
poetry install
```

Install pre-commits :

```shell
poetry run pre-commit install
```

## Configure

Some environment variables are needed and can be found in the `.env.example file`

```shell
cp .env.example .env
```

Then update var values with accurate ones

## Run

```shell
poetry run airparif now
poetry run airparif today
poetry run airparif tomorrow
```

### Run using docker image

Create local docker image:

```bash
docker build -t air_bot:$(poetry version --short) -t air_bot:latest .
```

Run local docker image:

```bash
source .env
docker run \
  -e MASTODON_INSTANCE=${MASTODON_INSTANCE} \
  -e MASTODON_ACCESS_TOKEN=${MASTODON_ACCESS_TOKEN} \
  -e AIRPARIF_API_KEY=${AIRPARIF_API_KEY} \
  air_bot:latest airparif now
```

## Contribute

To create a bot for publishing [ATMO](https://www.atmo-france.org/) data (exemple: "service"), those steps can be followed :

- add a new poetry script in the `pyproject.toml` file :

```toml
[tool.poetry.scripts]
service = "air_bot.service:service"
```

- create a new `.py` file in the `air_bot` folder : `touch service.py`

- inherit the generic `AirBot` class :

```python
import logging
from argparse import ArgumentParser, Namespace
from air_bot import AirBot, logger

class ServiceBot(AirBot):

    def __init__( self, instance: str, access_token: str,) -> None:
        super().__init__(instance, access_token)

    def arguments(self) -> Namespace:
        # declare here the CLI arguments
        parser = ArgumentParser(description="AirParif bot CLI")
        parser.add_argument(
            "-v", "--verbose", action="store_true", default=False, help="Verbose output"
        )
        return parser.parse_args()

    def run(self, **kwargs) -> None:

        logger.info("Running Service bot")
        # retrieve CLI arguments
        arguments = self.arguments()
        # set verbose if needed
        if arguments.verbose:
            logger.setLevel(logging.DEBUG)
            for h in logger.handlers:
                h.setLevel(logging.DEBUG)
        # run the processing here: get ATMO data, post to mastodon ...
```

- create a `service` function at the bottom of the file :

```python
import os
from air_bot import logger, ServiceBot

def service() -> None:
    """
    main function
    :return: nothing
    """

    # retrieve environment variables
    if "MASTODON_INSTANCE" not in os.environ:
        logger.error("Error: MASTODON_INSTANCE environment variable not set")
        exit(1)
    instance = os.getenv("MASTODON_INSTANCE")

    if "MASTODON_ACCESS_TOKEN" not in os.environ:
        logger.error("Error: MASTODON_ACCESS_TOKEN environment variable not set")
        exit(1)
    access_token = os.getenv("MASTODON_ACCESS_TOKEN")

    try:
        bot = ServiceBot(instance, access_token)
        bot.run()
    except Exception as exc:
        logger.error(exc)
        exit(1)
```

## Implementations

- [airbot](https://mapstodon.space/@air_bot) on [mapstodon.space](https://mapstodon.space/about), posts ATMO data from:
  - [AirParif](https://www.airparif.fr/)
