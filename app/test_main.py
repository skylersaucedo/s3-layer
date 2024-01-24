import boto3
from fastapi.testclient import TestClient
from moto import mock_s3
import io

from .main import app
from .config import get_settings
from .db.commands.create_api_key import create_api_key

client = TestClient(app)
settings = get_settings()


def test_index():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


@mock_s3
def test_dataset_upload_file():
    api_key, secret = create_api_key("test_dataset_upload_file")

    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=settings.dataset_s3_bucket)

    file_contents = io.BytesIO(b"some test data")

    response = client.post(
        "/dataset/upload-file",
        files={"file": ("test_file.csv", file_contents)},
        data={"tags": ["test"]},
        auth=(api_key, secret),
    )

    assert response.status_code == 200
    resonse_json = response.json()

    assert resonse_json["status"] == "OK"

    s3_object_name = resonse_json["s3_object_name"]

    s3_object = s3_client.get_object(
        Bucket=settings.dataset_s3_bucket,
        Key=s3_object_name,
    )

    assert s3_object["Body"].read() == b"some test data"


def test_dataset_upload_file_no_auth():
    response = client.post(
        "/dataset/upload-file",
        files={"file": ("test_file.csv", b"some test data")},
    )

    assert response.status_code == 401
    resonse_json = response.json()

    assert resonse_json["detail"] == "Not authenticated"


@mock_s3
def test_dataset_upload_file_no_file():
    api_key, secret = create_api_key("test_dataset_upload_file")

    response = client.post(
        "/dataset/upload-file",
        auth=(api_key, secret),
    )

    assert response.status_code == 422
    resonse_json = response.json()

    assert resonse_json["detail"][0]["msg"] == "Field required"


@mock_s3
def test_dataset_download_file():
    api_key, secret = create_api_key("test_dataset_upload_file")

    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=settings.dataset_s3_bucket)

    file_contents = io.BytesIO(b"some test data")

    response = client.post(
        "/dataset/upload-file",
        files={"file": ("test_file.csv", file_contents)},
        data={"tags": ["test"]},
        auth=(api_key, secret),
    )

    assert response.status_code == 200
    resonse_json = response.json()

    assert resonse_json["status"] == "OK"

    dataset_object_id = resonse_json["dataset_object_id"]

    response = client.get(
        f"/dataset/download-file/{dataset_object_id}",
        auth=(api_key, secret),
    )

    assert response.status_code == 200
    assert response.content == b"some test data"


def test_dataset_list_files():
    api_key, secret = create_api_key("test_list_files")

    response = client.get(
        "/dataset/list-files",
        auth=(api_key, secret),
    )

    assert response.status_code == 200
    resonse_json = response.json()

    assert resonse_json["status"] == "OK"
    assert len(resonse_json["files"]) == resonse_json["count"]
