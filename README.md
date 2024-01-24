# Base S3 API for TubesML

Uses FastAPI to create a REST API for uploading assets to S3 buckets.

## Getting Started

### Prerequisites

Python 3.11 is required to run this project. It is recommended to use a virtual environment to run this project.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running the API

To run the API, run the following command in the root directory:

```bash
uvicorn app.main:app --reload
```

### Testing the API

You will need some additional dev dependencies to run the tests. Install them with the following command:

```bash
pip install -r requirements-dev.txt
```

To test the API, run the following command in the main directory:

```bash
pytest app
```

## Database

The database is in MariaDB. To generate the database schema, run the following command in the root directory:

```bash
python -m app.db.commands.generate_ddl
```

To create a test API key, run the following command in the root directory:

```bash
python -m app.db.commands.create_api_key
```

## API Documentation

The API documentation is available at `/docs` and `/redoc`.