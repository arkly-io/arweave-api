"""Entry-point for the Arkly Arweave API."""

import argparse
import importlib
import logging
import sys
import time

import uvicorn

try:
    from src.arweave_api.version import get_version
except ModuleNotFoundError:
    from arweave_api.version import get_version

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
        prog="arweave-api",
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

    # Enable worker reload in Uvicorn by importing from string.
    import_str = "src.arweave_api.api"
    try:
        importlib.import_module(import_str)
        import_str = "src.arweave_api.api:app"
    except ModuleNotFoundError:
        import_str = "arweave_api.api:app"
        logger.info("importing from %s", import_str)

    logger.info(
        "attempting API startup, try setting `--port` arg if there are any issues"
    )

    uvicorn.run(
        import_str,
        host="0.0.0.0",
        port=int(args.port),
        access_log=False,
        log_level="info",
        reload=True,
    )


if __name__ == "__main__":
    main()
