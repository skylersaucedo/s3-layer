import boto3
import io
import os


from fastapi.testclient import TestClient
from moto import mock_s3

from .main import app
from .db.commands.create_api_key import create_api_key

client = TestClient(app)


@mock_s3
def test_model_upload_file():
    api_key, secret = create_api_key("test_model_upload_file")

    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=os.environ["MLMODEL_S3_BUCKET"])

    file_contents = io.BytesIO(b"some test data")

    response = client.post(
        "/models",
        files={"file": ("test_file.csv", file_contents)},
        data={"tags": ["test"]},
        auth=(api_key, secret),
    )

    assert response.status_code == 200
    response_json = response.json()

    assert response_json["status"] == "OK"

    s3_object_name = response_json["s3_object_name"]

    s3_object = s3_client.get_object(
        Bucket=os.environ["MLMODEL_S3_BUCKET"],
        Key=s3_object_name,
    )

    assert s3_object["Body"].read() == b"some test data"


@mock_s3
def test_model_upload_file_no_auth():
    response = client.post(
        "/models",
        files={"file": ("test_file.csv", b"some test data")},
    )

    assert response.status_code == 401
    response_json = response.json()

    assert response_json["detail"] == "Not authenticated"


@mock_s3
def test_model_upload_file_no_file():
    api_key, secret = create_api_key("test_model_upload_file")

    response = client.post(
        "/models",
        auth=(api_key, secret),
    )

    assert response.status_code == 422
    response_json = response.json()

    assert response_json["detail"][0]["msg"] == "Field required"


@mock_s3
def test_model_download_file():
    api_key, secret = create_api_key("test_model_upload_file")

    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=os.environ["MLMODEL_S3_BUCKET"])

    file_contents = io.BytesIO(b"some test data")

    response = client.post(
        "/models",
        files={"file": ("test_file.csv", file_contents)},
        data={"tags": ["test"]},
        auth=(api_key, secret),
    )

    assert response.status_code == 200
    response_json = response.json()

    assert response_json["status"] == "OK"

    model_object_id = response_json["model_object_id"]

    response = client.get(
        f"/models/{model_object_id}",
        auth=(api_key, secret),
    )

    assert response.status_code == 200
    assert response.content == b"some test data"


@mock_s3
def test_model_list_files():
    api_key, secret = create_api_key("test_list_files")

    response = client.get(
        "/models",
        auth=(api_key, secret),
    )

    assert response.status_code == 200
    response_json = response.json()

    assert response_json["status"] == "OK"
    assert len(response_json["files"]) == response_json["count"]

    response = client.get(
        "/models",
        params={"tags": ["test"]},
        auth=(api_key, secret),
    )

    assert response.status_code == 200
    response_json = response.json()

    assert response_json["status"] == "OK"
    assert len(response_json["files"]) == response_json["count"]
