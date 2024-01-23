import boto3
from fastapi.testclient import TestClient
from moto import mock_s3
import io

from .main import app
from .config import get_settings

client = TestClient(app)
settings = get_settings()


def test_index():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


@mock_s3
def test_dataset_upload_file():
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=settings.dataset_s3_bucket)

    file_contents = io.BytesIO(b"some test data")

    response = client.post(
        "/dataset/upload-file",
        files={"file": ("test_file.csv", file_contents)},
        data={"tags": ["test"]},
    )

    assert response.status_code == 200
    resonse_json = response.json()

    assert resonse_json["status"] == "OK"
