import boto3
import dotenv
import io
import json
import os

dotenv.load_dotenv()

from fastapi.testclient import TestClient
from moto import mock_s3

from .main import app
from .db.commands.create_api_key import create_api_key

client = TestClient(app)


def test_index():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


@mock_s3
def test_dataset_upload_file():
    api_key, secret = create_api_key("test_dataset_upload_file")

    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=os.environ["DATASET_S3_BUCKET"])

    file_contents = io.BytesIO(b"some test data")

    response = client.post(
        "/dataset",
        files={"file": ("test_file.csv", file_contents)},
        data={"tags": ["test"]},
        auth=(api_key, secret),
    )

    assert response.status_code == 200
    response_json = response.json()

    assert response_json["status"] == "OK"

    s3_object_name = response_json["s3_object_name"]

    s3_object = s3_client.get_object(
        Bucket=os.environ["DATASET_S3_BUCKET"],
        Key=s3_object_name,
    )

    assert s3_object["Body"].read() == b"some test data"


@mock_s3
def test_dataset_upload_file_no_auth():
    response = client.post(
        "/dataset",
        files={"file": ("test_file.csv", b"some test data")},
    )

    assert response.status_code == 401
    response_json = response.json()

    assert response_json["detail"] == "Not authenticated"


@mock_s3
def test_dataset_upload_file_no_file():
    api_key, secret = create_api_key("test_dataset_upload_file")

    response = client.post(
        "/dataset",
        auth=(api_key, secret),
    )

    assert response.status_code == 422
    response_json = response.json()

    assert response_json["detail"][0]["msg"] == "Field required"


@mock_s3
def test_dataset_download_file():
    api_key, secret = create_api_key("test_dataset_upload_file")

    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=os.environ["DATASET_S3_BUCKET"])

    file_contents = io.BytesIO(b"some test data")

    response = client.post(
        "/dataset",
        files={"file": ("test_file.csv", file_contents)},
        data={"tags": ["test"]},
        auth=(api_key, secret),
    )

    assert response.status_code == 200
    response_json = response.json()

    assert response_json["status"] == "OK"

    dataset_object_id = response_json["dataset_object_id"]

    response = client.get(
        f"/dataset/{dataset_object_id}",
        auth=(api_key, secret),
    )

    assert response.status_code == 200
    assert response.content == b"some test data"


@mock_s3
def test_dataset_delete_file():
    api_key, secret = create_api_key("test_dataset_upload_file")

    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=os.environ["DATASET_S3_BUCKET"])

    file_contents = io.BytesIO(b"some test data")

    response = client.post(
        "/dataset",
        files={"file": ("test_file.csv", file_contents)},
        data={"tags": ["test"]},
        auth=(api_key, secret),
    )

    assert response.status_code == 200

    response_json = response.json()

    assert response_json["status"] == "OK"

    dataset_object_id = response_json["dataset_object_id"]

    response = client.delete(
        f"/dataset/{dataset_object_id}",
        auth=(api_key, secret),
    )

    assert response.status_code == 200
    response_json = response.json()

    assert response_json["status"] == "OK"

    response = client.get(
        f"/dataset/{dataset_object_id}",
        auth=(api_key, secret),
    )

    assert response.status_code == 404
    response_json = response.json()

    assert response_json["detail"] == "File not found"


@mock_s3
def test_dataset_file_details():
    api_key, secret = create_api_key("test_dataset_file_details")

    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=os.environ["DATASET_S3_BUCKET"])

    file_contents = io.BytesIO(b"some test data")

    upload_response = client.post(
        "/dataset",
        files={"file": ("test_file.csv", file_contents)},
        data={"tags": ["test"]},
        auth=(api_key, secret),
    )

    assert upload_response.status_code == 200
    upload_response_json = upload_response.json()

    assert upload_response_json["status"] == "OK"
    dataset_object_id = upload_response_json["dataset_object_id"]

    details_response = client.get(
        f"/dataset/{dataset_object_id}/details",
        auth=(api_key, secret),
    )

    assert details_response.status_code == 200
    details_response_json = details_response.json()

    assert details_response_json["status"] == "OK"
    assert details_response_json["file"]["id"] == dataset_object_id
    assert details_response_json["file"]["name"] == "test_file.csv"
    assert details_response_json["file"]["content_type"] == "application/vnd.ms-excel"
    assert details_response_json["file"]["file_hash_sha1"] == "123456"
    assert details_response_json["file"]["tags"][0]["tag"] == "test"
    assert (
        details_response_json["file"]["s3_object_name"]
        == upload_response_json["s3_object_name"]
    )
    assert details_response_json["file"]["labels"] == []


@mock_s3
def test_dataset_file_add_tags():
    api_key, secret = create_api_key("test_dataset_file_add_tags")

    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=os.environ["DATASET_S3_BUCKET"])

    file_contents = io.BytesIO(b"some test data")

    upload_response = client.post(
        "/dataset",
        files={"file": ("test_file.csv", file_contents)},
        data={"tags": ["test"]},
        auth=(api_key, secret),
    )

    assert upload_response.status_code == 200
    upload_response_json = upload_response.json()

    assert upload_response_json["status"] == "OK"
    dataset_object_id = upload_response_json["dataset_object_id"]

    add_tags_response = client.post(
        f"/dataset/{dataset_object_id}/tags",
        data={"tag": "test tag"},
        auth=(api_key, secret),
    )

    assert add_tags_response.status_code == 200
    add_tags_response_json = add_tags_response.json()

    assert add_tags_response_json["status"] == "OK"
    assert add_tags_response_json["tag"]["tag"] == "test tag"

    details_response = client.get(
        f"/dataset/{dataset_object_id}/details",
        auth=(api_key, secret),
    )

    assert details_response.status_code == 200
    details_response_json = details_response.json()

    assert "test" in details_response_json["file"]["tags"][0]["tag"]
    assert "test tag" in details_response_json["file"]["tags"][1]["tag"]


@mock_s3
def test_dataset_file_delete_tag():
    api_key, secret = create_api_key("test_dataset_file_delete_tags")

    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=os.environ["DATASET_S3_BUCKET"])

    file_contents = io.BytesIO(b"some test data")

    upload_response = client.post(
        "/dataset",
        files={"file": ("test_file.csv", file_contents)},
        data={"tags": ["test", "test tag"]},
        auth=(api_key, secret),
    )

    assert upload_response.status_code == 200
    upload_response_json = upload_response.json()

    assert upload_response_json["status"] == "OK"
    dataset_object_id = upload_response_json["dataset_object_id"]

    details_response = client.get(
        f"/dataset/{dataset_object_id}/details",
        auth=(api_key, secret),
    )

    assert details_response.status_code == 200
    details_response_json = details_response.json()

    tag_guid = details_response_json["file"]["tags"][0]["tag_guid"]

    delete_tags_response = client.delete(
        f"/dataset/{dataset_object_id}/tags/{tag_guid}",
        auth=(api_key, secret),
    )

    assert delete_tags_response.status_code == 200
    delete_tags_response_json = delete_tags_response.json()

    assert delete_tags_response_json["status"] == "OK"

    details_response = client.get(
        f"/dataset/{dataset_object_id}/details",
        auth=(api_key, secret),
    )

    assert details_response.status_code == 200
    details_response_json = details_response.json()

    assert len(details_response_json["file"]["tags"]) == 1


@mock_s3
def test_dataset_file_add_label():
    api_key, secret = create_api_key("test_dataset_file_add_label")

    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=os.environ["DATASET_S3_BUCKET"])

    file_contents = io.BytesIO(b"some test data")

    upload_response = client.post(
        "/dataset",
        files={"file": ("test_file.csv", file_contents)},
        data={"tags": ["test"]},
        auth=(api_key, secret),
    )

    assert upload_response.status_code == 200
    upload_response_json = upload_response.json()

    assert upload_response_json["status"] == "OK"
    dataset_object_id = upload_response_json["dataset_object_id"]

    add_label_response = client.post(
        f"/dataset/{dataset_object_id}/labels",
        data={
            "label": "test label",
            "polygon": json.dumps(
                [
                    {"x": 0.1, "y": 0.1},
                    {"x": 0.9, "y": 0.1},
                ]
            ),
        },
        auth=(api_key, secret),
    )

    assert add_label_response.status_code == 200
    add_label_response_json = add_label_response.json()

    assert add_label_response_json["status"] == "OK"
    assert add_label_response_json["label"]["label"] == "test label"
    assert len(add_label_response_json["label"]["polygon"]) == 2

    assert add_label_response_json["label"]["polygon"][0] == {
        "x": 0.1,
        "y": 0.1,
    }
    assert add_label_response_json["label"]["polygon"][1] == {
        "x": 0.9,
        "y": 0.1,
    }

    details_response = client.get(
        f"/dataset/{dataset_object_id}/details",
        auth=(api_key, secret),
    )

    assert details_response.status_code == 200
    details_response_json = details_response.json()

    assert len(details_response_json["file"]["labels"]) == 1
    assert details_response_json["file"]["labels"][0]["label"] == "test label"


@mock_s3
def test_dataset_file_delete_label():
    api_key, secret = create_api_key("test_dataset_file_add_label")

    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=os.environ["DATASET_S3_BUCKET"])

    file_contents = io.BytesIO(b"some test data")

    upload_response = client.post(
        "/dataset",
        files={"file": ("test_file.csv", file_contents)},
        data={"tags": ["test"]},
        auth=(api_key, secret),
    )

    assert upload_response.status_code == 200
    upload_response_json = upload_response.json()

    assert upload_response_json["status"] == "OK"
    dataset_object_id = upload_response_json["dataset_object_id"]

    add_label_response = client.post(
        f"/dataset/{dataset_object_id}/labels",
        data={
            "label": "test label",
            "polygon": json.dumps(
                [
                    {
                        "x": 0.1,
                        "y": 0.1,
                    },
                    {
                        "x": 0.9,
                        "y": 0.1,
                    },
                ]
            ),
        },
        auth=(api_key, secret),
    )

    assert add_label_response.status_code == 200
    add_label_response_json = add_label_response.json()

    assert add_label_response_json["status"] == "OK"
    assert add_label_response_json["label"]["label"] == "test label"
    assert len(add_label_response_json["label"]["polygon"]) == 2

    assert add_label_response_json["label"]["polygon"][0] == {
        "x": 0.1,
        "y": 0.1,
    }
    assert add_label_response_json["label"]["polygon"][1] == {
        "x": 0.9,
        "y": 0.1,
    }

    details_response = client.get(
        f"/dataset/{dataset_object_id}/details",
        auth=(api_key, secret),
    )

    assert details_response.status_code == 200
    details_response_json = details_response.json()

    assert len(details_response_json["file"]["labels"]) == 1
    assert details_response_json["file"]["labels"][0]["label"] == "test label"
    label_guid = details_response_json["file"]["labels"][0]["label_guid"]

    delete_label_response = client.delete(
        f"/dataset/{dataset_object_id}/labels/{label_guid}",
        auth=(api_key, secret),
    )

    assert delete_label_response.status_code == 200
    delete_label_response_json = delete_label_response.json()

    assert delete_label_response_json["status"] == "OK"

    details_response = client.get(
        f"/dataset/{dataset_object_id}/details",
        auth=(api_key, secret),
    )

    assert details_response.status_code == 200
    details_response_json = details_response.json()

    assert len(details_response_json["file"]["labels"]) == 0


def test_dataset_list_files():
    api_key, secret = create_api_key("test_list_files")

    response = client.get(
        "/dataset",
        auth=(api_key, secret),
    )

    assert response.status_code == 200
    response_json = response.json()

    assert response_json["status"] == "OK"
    assert len(response_json["files"]) == response_json["count"]

    response = client.get(
        "/dataset",
        params={"tags": ["test"]},
        auth=(api_key, secret),
    )

    assert response.status_code == 200
    response_json = response.json()

    assert response_json["status"] == "OK"
    assert len(response_json["files"]) == response_json["count"]


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
