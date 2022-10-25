# Arweave API

This API allows users to upload their files permanently onto Arweave.

## Installation :star:

It is recommended to run a virtual environment locally. To do this, run the
following:

### Setting up a virtual environment :house_with_garden:

```bash
python3 -m venv venv
source venv/bin/activate
```

> NB. If Python 3 is already your default interpreter, then simply call
> `python`.

### Installing dependencies :signal_strength:

Once the virtual environment is activated, the `python` interpreter will point
to the version you set it up with. Install the code's dependencies as follows:

```bash
python -m pip install -r requirements/local.txt
```

> NB. Local development is assumed. If you are not planning to develop from
> this repository, simply install `requirements/requirements.txt`.

### Deactivating the virtual environment :fire_extinguisher:

Once you have finished, if you need to continue to work in the same shell, you
can deactivate the virtual environment as follows:

```bash
deactivate
```

## Usage :computer:

To start the server locally, run:
 ```bash
 uvicorn main:app --reload
 ```

## Testing :gear:

In the root folder, start the server locally and then use:
```bash
tox -e py310` 
```

to execute the unit tests.

## Endpoint documentation :scroll:

Documentation for the API endpoints comes in two variants:

### OpenAPI (Swagger): Interactive API docs

* http://127.0.0.1:8000/docs/

### Redoc: Alternative API docs

* http://127.0.0.1:8000/redoc/

# Database (PostgreSQL) :elephant:

To access the Postgres prompt:
```postgresql
psql
```

To connect to our database:
```postgresql
\c arkly
```

To show tables:
```postgresql
\dt
```

To display info on our endpoint info table:
```postgresql
\d endpoint_calls
```

To display values held by each column:
```sql
SELECT * FROM endpoint_calls;
```

To quit the Postgres prompt:
```postgresql
\q
```