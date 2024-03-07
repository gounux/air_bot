import logging
import os
import shutil
from argparse import ArgumentParser, Namespace
from datetime import datetime
from typing import Tuple

import requests
from requests import Response

from air_bot import AirBot, AirParifException, logger

AIRPARIF_API_BASE_URL = "https://api.airparif.asso.fr"
AIRPARIF_WMS_BASE_URL = "https://magellan.airparif.asso.fr/geoserver/siteweb/wms"
WMS_LAYER_TODAY = "siteweb:vue_indice_atmo_2020_com"
WMS_LAYER_TOMORROW = "siteweb:vue_indice_atmo_2020_com_jp1"
MIME_PNG = "image/png"
EXIT_CODE = 666

TOOT_BULLETIN_TEMPLATE = """💨 Bulletin #AirParif {day} ({date}) :

\"{message}\"

Concentrations des polluants:
{pollutants}"""

TOOT_EPISODE_TEMPLATE = """💨 #AirParif épisode de pollution demain :

\"{message}\"

Concentrations des polluants:
{pollutants}"""


class AirParifBot(AirBot):
    api_key: str

    def __init__(
        self,
        instance: str,
        access_token: str,
        api_key: str,
    ) -> None:
        super().__init__(instance, access_token)
        self.api_key = api_key

    def arguments(self) -> Namespace:
        parser = ArgumentParser(description="AirParif bot CLI")
        parser.add_argument(
            "action",
            help="AirParif action to perform: now, today, tomorrow, episode",
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
        logger.info("Running AirParif bot")
        arguments = self.arguments()
        if arguments.verbose:
            logger.setLevel(logging.DEBUG)
            for h in logger.handlers:
                h.setLevel(logging.DEBUG)
        logger.debug(arguments)

        dryrun = arguments.dryrun

        if arguments.action == "now":
            self._now(dryrun)
        elif arguments.action == "today":
            self._today(dryrun)
        elif arguments.action == "tomorrow":
            self._tomorrow(dryrun)
        elif arguments.action == "episode":
            self._episode(dryrun)
        else:
            raise AirParifException(f"Unknown action: {arguments.action}")

    def _check_http_response(self, r: Response, expected: int = 200) -> None:
        """
        Utilitary method that checks if an HTTP response has expected status.
        If not, an AirParifException is raised
        :param r: HTTP response
        :param expected: expected status_code
        :return: nothing but a ginseng
        """
        if r.status_code != expected:
            logger.error(r.reason)
            raise AirParifException(f"The response {r} does not have expected status")

    def _generate_map_image(
        self,
        wms_layer: str,
        width: int = 600,
        height: int = 500,
        path: str = f"airparif_idf_{datetime.now().strftime('%Y%m%d%H%M%S')}.png",
    ) -> Tuple[str, datetime]:
        """
        Generates an image of current AirParif map using WMS stream
        :param width: image width, requested in WMS request (default: 600)
        :param height: image height, requested in WMS request (default: 600)
        :return: Tuple with image path and datetime of generation
        """
        r: Response = requests.get(
            AIRPARIF_WMS_BASE_URL,
            params={
                "service": "WMS",
                "version": "1.1.0",
                "request": "GetMap",
                "layers": f"{wms_layer},Administratif:comm_idf,siteweb:idf_dept",
                "styles": "siteweb:nouvel_indice_polygones,poly_trait_blanc,poly_trait_blanc_50",
                "bbox": "530000.0,2335000.0,695000.0,2475000.0",
                "width": width,
                "height": height,
                "srs": "EPSG:27572",
                "format": MIME_PNG,
                "format_options": "layout:bulletin",
            },
            stream=True,
        )
        self._check_http_response(r)

        with open(path, "wb") as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)
            return path, datetime.now()

    def _now(self, dryrun: bool) -> None:
        img_path, dt = self._generate_map_image(wms_layer=WMS_LAYER_TODAY)
        if dryrun:
            return
        try:
            self.mastodon.status_post(
                "💨 Carte de la qualité de l'air mesurée par #AirParif en ce moment",
                media_ids=[
                    self.mastodon.media_post(
                        img_path,
                        mime_type=MIME_PNG,
                        description=f"Carte de la qualité de l'air mesurée par AirParif à {dt.strftime('%Hh%M')}",
                    )
                ],
                visibility="unlisted",
                language="fr",
            )
        finally:
            os.remove(img_path)

    def _bulletin(self, day: str, day_key: str) -> str:
        """
        Generates a bulletin toot with today or tomorrow's predictions
        :param day: "aujourd'hui" or "demain"
        :param day_key: "jour" or "demain"
        :return: templated and formatted toot text
        """
        r: Response = requests.get(
            f"{AIRPARIF_API_BASE_URL}/indices/prevision/bulletin",
            headers={"X-Api-Key": self.api_key},
        )
        self._check_http_response(r)

        data = r.json()
        if not data[day_key]["disponible"]:
            raise AirParifException(
                f"Bulletin ({day} is not available. Please come back later"
            )

        toot = TOOT_BULLETIN_TEMPLATE.format(
            day=day,
            date=datetime.strftime(
                datetime.strptime(data[day_key]["date"], "%Y-%m-%d"), "%d.%m.%Y"
            ),
            message=data[day_key]["bulletin"]["fr"],
            pollutants="\n".join(
                [
                    f"👉 {p[0]}: de {p[1]:.0f} à {p[2]:.0f} µg/m³"
                    for p in data[day_key]["concentrations"]
                ]
            ),
        )
        return toot

    def _today(self, dryrun: bool) -> None:
        toot = self._bulletin("aujourd'hui", "jour")
        img_path, _ = self._generate_map_image(wms_layer=WMS_LAYER_TODAY)
        if dryrun:
            return
        try:
            self.mastodon.status_post(
                toot,
                media_ids=[
                    self.mastodon.media_post(
                        img_path,
                        mime_type=MIME_PNG,
                        description="Carte de la qualité de l'air mesurée par AirParif aujourd'hui",
                    )
                ],
                visibility="unlisted",
                language="fr",
            )
        finally:
            os.remove(img_path)

    def _tomorrow(self, dryrun: bool) -> None:
        toot = self._bulletin("demain", "demain")
        img_path, _ = self._generate_map_image(wms_layer=WMS_LAYER_TOMORROW)
        if dryrun:
            return
        try:
            self.mastodon.status_post(
                toot,
                media_ids=[
                    self.mastodon.media_post(
                        img_path,
                        mime_type=MIME_PNG,
                        description="Carte de la qualité de l'air mesurée par AirParif demain",
                    )
                ],
                visibility="unlisted",
                language="fr",
            )
        finally:
            os.remove(img_path)

    def _episode(self, dryrun: bool) -> None:
        r: Response = requests.get(
            f"{AIRPARIF_API_BASE_URL}/episodes/en-cours-et-prevus",
            headers={"X-Api-Key": self.api_key},
        )
        self._check_http_response(r)

        data = r.json()
        if not data["actif"]:
            raise AirParifException("No pollution episode today or tomorrow")
        if not data["demain"]["actif"]:
            raise AirParifException("No pollution episode tomorrow")
        if dryrun:
            return

        toot = TOOT_EPISODE_TEMPLATE.format(
            message=data["message"]["fr"],
            pollutants="\n".join(
                [
                    f"👉 {p['nom']}: {p['niveau']} µg/m³"
                    for p in data["demain"]["polluants"]
                ]
            ),
        )
        self.mastodon.status_post(
            toot,
            visibility="unlisted",
            language="fr",
        )


def airparif() -> None:
    """
    AirParif main function
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

    # retrieve environment variables
    if "AIRPARIF_API_KEY" not in os.environ:
        logger.error("Error: AIRPARIF_API_KEY environment variable not set")
        exit(EXIT_CODE)
    airparif_key = os.getenv("AIRPARIF_API_KEY")

    try:
        ap_bot = AirParifBot(instance, access_token, airparif_key)
        ap_bot.run(key=airparif_key)
    except Exception as exc:
        logger.error(exc)
        exit(EXIT_CODE)
