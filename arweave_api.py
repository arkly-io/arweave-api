"""Entry-point for the Arkly Arweave API."""

import logging
import time

from src.arweave_api.arweave_api import main as arweave_app

logging.basicConfig(
    format="%(asctime)-15s %(levelname)s :: %(filename)s:%(lineno)s:%(funcName)s() :: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level="INFO",
)

logging.Formatter.converter = time.gmtime

logger = logging.getLogger(__name__)


def main():
    """Primary entry point for this script."""
    arweave_app()


if __name__ == "__main__":
    main()
