"""Entry-point for the Arkly Arweave API."""

import argparse
import logging
import sys
import time

import uvicorn

from src.arweave_api.version import get_version

logging.basicConfig(
    format="%(asctime)-15s %(levelname)s :: %(filename)s:%(lineno)s:%(funcName)s() :: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level="INFO",
)

logging.Formatter.converter = time.gmtime

logger = logging.getLogger(__name__)


def main():
    """Primary entry point for this script."""

    parser = argparse.ArgumentParser(
        prog="arweave_api",
        description="Arkly Arweave API",
        epilog="for more information visit https://arkly.io",
    )

    parser.add_argument(
        "--port",
        help="provide a port on which to run the app",
        required=False,
        default=8000,
    )

    parser.add_argument(
        "--version",
        help="return the version of the app",
        required=False,
        action="store_true",
    )

    args = parser.parse_args()

    if args.version:
        print(f"{get_version()}")
        sys.exit(0)

    uvicorn.run(
        "src.arweave_api.main:app",
        host="0.0.0.0",
        port=int(args.port),
        access_log=False,
        log_level="info",
        reload=True,
    )


if __name__ == "__main__":
    main()
