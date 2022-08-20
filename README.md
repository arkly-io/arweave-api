# Arweave API

This API allows users to upload their files permanently onto Arweave.

## Installation :star:

It is recommended to run a virtual environment locally. To do this, run the
following:

### Setting up a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

> NB. If Python 3 is already your default interpreter, then simply call
> `python`.

### Installing dependencies

Once the virtual environment is activated, the `python` interpreter will point
to the version you set it up with. Install the code's dependencies as follows:

```bash
python -m pip install -r requirements/local.txt
```

> NB. Local development is assumed. If you are not planning to develop from
> this repository, simply install `requirements/requirements.txt`.

### Deactivating the virtual environment

Once you have finished, if you need to continue to work in the same shell, you
can deactivate the virtual environment as follows:

```bash
deactivate
````

## Usage :computer:

To start the server locally, run `uvicorn main:app --reload`

To test out endpoints, run `python3 test_routes.py`

## Endpoint documentation :scroll:

Documentation for the API endpoints comes in two variants:

## Testing

In the root folder, start the server locally and then use `pytest -v` to execute the unit tests.

### OpenAPI (Swagger): Interactive API docs

* http://127.0.0.1:8000/docs/

### Redoc: Alternative API docs

* http://127.0.0.1:8000/redoc/
