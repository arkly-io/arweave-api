# Arweave API

This API allows users to upload their files permanently onto Arweave.

# Table of contents

- [Arweave API](#arweave-api)
  - [Install from package :package:](#install-from-package-package)
  - [Install for development :star:](#install-for-development-star)
  - [Usage :computer:](#usage-computer)
  - [Testing :gear:](#testing-gear)
  - [Endpoint documentation :scroll:](#endpoint-documentation-scroll)

## Install from package :package:

Once you have selected a package from the releases, take for example
`arweave_api-2023.9.7.1`:

Install with:

```sh
# Setup a virtual environment
python3 -m venv venv
# Activate the virtual environment
source venv/bin/activate
# Install using python-pip
python -m pip install -r arweave_api-2023.9.7.1-py3-none-any.whl
```

### To show startup options:

```sh
arweave-api -h
```

### To run on the default port:

```sh
arweave-api
```

## Install for development :star:

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
````

## Usage :computer:

To start the server locally, run `python -m src.arweave_api.arweave_api`

## Testing :gear:

In the root folder, start the server locally and then use `tox -e py310` to
execute the unit tests.

## Endpoint documentation :scroll:

Documentation for the API endpoints comes in two variants:

### OpenAPI (Swagger): Interactive API docs

* http://127.0.0.1:8000/docs/

### Redoc: Alternative API docs

* http://127.0.0.1:8000/redoc/
