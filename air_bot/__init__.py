import logging
import sys
from abc import ABC
from argparse import Namespace

import colorlog
from mastodon import Mastodon

# logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = colorlog.ColoredFormatter(
    "%(yellow)s%(asctime)s %(log_color)s[%(levelname)s]%(reset)s %(purple)s[%(name)s %(module)s]%(reset)s %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


class AirParifException(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class AirBot(ABC):
    """
    Abstract bot class that any implementation should override (AirParif...)
    """

    mastodon: Mastodon

    def __init__(self, instance: str, access_token: str) -> None:
        self.mastodon = Mastodon(api_base_url=instance, access_token=access_token)
        self.me = self.mastodon.me()

    def arguments(self) -> Namespace:
        """
        Build CLI arguments needed by the program
        :return: Namespace for CLI arg's definition
        """
        raise NotImplementedError("Not implemented")

    def run(self, **kwargs) -> None:
        """
        Run the bot
        :param args:
        :param kwargs:
        :return:
        """
        raise NotImplementedError("Not implemented")
