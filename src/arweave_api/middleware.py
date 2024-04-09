"""FastAPI middleware.

Middleware enables requests to be intercepted and processed, e.g.
validation, and responses to be intercepted and augmented, e.g. adding
headers, and other information.
"""
import logging
from typing import Callable

import psycopg2
from fastapi import Request

logger = logging.getLogger(__name__)
