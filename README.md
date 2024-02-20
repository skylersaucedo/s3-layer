# Base S3 API for TubesML

Uses FastAPI to create a REST API for uploading assets to S3 buckets.

## Getting Started

### Prerequisites

Python 3.11 is required to run this project. It is also strongly recommended to use a virtual environment.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running the API Locally

To run the API, run the following command in the root directory:

#### Linux

```bash
uvicorn app.main:app --reload
```

#### Windows

There's a bug in Windows Cython that prevents this from working correctly. https://github.com/encode/uvicorn/issues/1972. There are no clean work-arounds short of monkey-patching Cython or uvicorn.

### Testing the API

You will need some additional dev dependencies to run the tests. Install them with the following command:

```bash
pip install -r requirements-dev.txt
```

To test the API, run the following command in the main directory:

```bash
pytest app
```

### Database

The database is in MariaDB. To generate the database schema, run the following command in the root directory:

```bash
python -m app.db.commands.generate_ddl
```

To create a test API key, run the following command in the root directory:

```bash
python -m app.db.commands.create_api_key
```

## API Documentation

The API documentation is available at `/docs` and `/redoc`. You can view the current production documentation at [https://api.tsi-mlops.com/docs](https://api.tsi-mlops.com/docs) or [https://api.tsi-mlops.com/redoc](https://api.tsi-mlops.com/redoc).

### API Examples

test.ipynb is a Jupyter notebook that contains examples of how to use the API.