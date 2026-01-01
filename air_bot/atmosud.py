import logging
import os
import time
from argparse import ArgumentParser, Namespace
from datetime import datetime

import requests

from air_bot import EXIT_CODE, AirBot, AtmoException, logger

ATMOSUD_DOWNLOAD_URL = (
    "https://widgets.atmosud.org/siam/cartes-horaires/accueil/icairh.gif"
)


class AtmoSudBot(AirBot):

    def __init__(
        self,
        instance: str,
        access_token: str,
    ) -> None:
        super().__init__(instance, access_token)

    def arguments(self) -> Namespace:
        parser = ArgumentParser(description="AtmoSud bot CLI")
        parser.add_argument(
            "action",
            help="AtmoSud action to perform: giftoday",
        )
        parser.add_argument(
            "-d",
            "--dryrun",
            action="store_true",
            default=False,
            help="Dry run, do not post on mastodon",
        )
        parser.add_argument(
            "-v", "--verbose", action="store_true", default=False, help="Verbose output"
        )
        return parser.parse_args()

    def run(self, **kwargs) -> None:
        logger.info("Running AtmoSud bot")
        arguments = self.arguments()
        if arguments.verbose:
            logger.setLevel(logging.DEBUG)
            for h in logger.handlers:
                h.setLevel(logging.DEBUG)
        logger.debug(arguments)

        dryrun = arguments.dryrun

        if arguments.action == "giftoday":
            self._gif_today(dryrun)
        else:
            raise AtmoException(f"Unknown action: {arguments.action}")

    def _gif_today(self, dryrun: bool) -> None:
        logger.info("Fetching AtmoSud day gif")

        local_filename = f"atmosud_gif_{datetime.now().strftime('%Y-%m-%d')}.gif"

        try:

            # Download the gif
            response = requests.get(ATMOSUD_DOWNLOAD_URL, stream=True)  # noqa: F821
            response.raise_for_status()

            with open(local_filename, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)

            # Post to Mastodon
            if dryrun:
                logger.info("Dry run enabled, not posting to Mastodon")
                return

            media = self.mastodon.media_post(
                media_file=local_filename,
                mime_type="image/gif",
                description=f"GIF de la qualité de l'air AtmoSud sur la région PACApour aujourd'hui ({datetime.now().strftime('%Y-%m-%d')})",
            )
            status_message = f"💨 Qualité de l'air AtmoSud sur la région PACA pour aujourd'hui ({datetime.now().strftime('%Y-%m-%d')})"

            time.sleep(10)  # let time to upload the media.
            self.mastodon.status_post(status=status_message, media_ids=[media])
            logger.info("Posted AtmoSud gif to Mastodon")

        finally:
            if os.path.exists(local_filename):
                os.remove(local_filename)
                logger.debug(f"Removed temporary file {local_filename}")


def atmosud() -> None:
    """
    AtmoSud main function
    :return: nothing but a ginseng
    """

    # retrieve environment variables
    if "MASTODON_INSTANCE" not in os.environ:
        logger.error("Error: MASTODON_INSTANCE environment variable not set")
        exit(EXIT_CODE)
    instance = os.getenv("MASTODON_INSTANCE")

    if "MASTODON_ACCESS_TOKEN" not in os.environ:
        logger.error("Error: MASTODON_ACCESS_TOKEN environment variable not set")
        exit(EXIT_CODE)
    access_token = os.getenv("MASTODON_ACCESS_TOKEN")

    try:
        atmosud_bot = AtmoSudBot(instance, access_token)
        atmosud_bot.run()
    except Exception as exc:
        logger.error(exc)
        exit(EXIT_CODE)
