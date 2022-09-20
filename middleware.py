"""FastAPI middleware.

Middleware enables requests to be intercepted and processed, e.g.
validation, and responses to be intercepted and augmented, e.g. adding
headers, and other information.
"""

from typing import Callable

import psycopg2
from fastapi import Request


async def _update_db(request: Request, call_next: Callable):
    """Update the database by one per endpoint called."""
    path = str(request.scope["path"])
    endpoints = [
        "/docs",
        "/check_balance/",
        "/check_last_transaction/",
        "/create_transaction/",
        "/fetch_upload/",
        "/validate_arweave_bag/",
    ]
    # Update database endpoint_calls by 1
    if path in endpoints:
        if path == "/docs":
            path = "root"
        else:
            # Remove first and last character
            path = path[1:-1]
        try:
            connection = psycopg2.connect(
                user="arkly", host="/var/run/postgresql/", database="arkly", port=5432
            )
            cursor = connection.cursor()
            update_endpoint_count = """UPDATE endpoint_calls
                                            SET {update_db_endpoint} = {update_db_endpoint} + 1""".format(
                update_db_endpoint=path
            )
            cursor.execute(update_endpoint_count)
            connection.commit()
            cursor.close()
        except psycopg2.DatabaseError as error:
            print(error)
    response = await call_next(request)
    return response
