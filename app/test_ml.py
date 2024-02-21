from fastapi.testclient import TestClient
from moto import mock_s3

import boto3
import cv2
import io
import os

from .db.commands.create_api_key import create_api_key
from .main import app
from .ml import detect_defects

TEST_PATH = os.path.dirname(os.path.realpath(__file__))

client = TestClient(app)


def test_detect_defects():
    """Test the detect_defects function actually runs. We're not testing the
    accuracy of the model, just that it functions as expected.
    """
    image = cv2.imread(os.path.join(TEST_PATH, "test_fixtures", "110.bmp"))

    model_path = os.path.join(TEST_PATH, "test_fixtures", "model.pth")

    with open(model_path, "rb") as f:
        predictions = detect_defects(image, f)

    print(predictions)

    assert len(predictions) > 0

    for prediction in predictions:
        assert "label" in prediction
        assert "confidence" in prediction
        assert "polygon" in prediction
        assert len(prediction["polygon"]) == 4
        for point in prediction["polygon"]:
            assert "left" in point
            assert "top" in point
            assert "begin_frame" in point
            assert "end_frame" in point


@mock_s3
def test_model_file_inference():
    api_key, secret = create_api_key("test_model_file_inference")

    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=os.environ["MLMODEL_S3_BUCKET"])

    model_path = os.path.join(TEST_PATH, "test_fixtures", "model.pth")

    with open(model_path, "rb") as f:
        model_contents = f.read()

    response = client.post(
        "/models",
        files={"file": ("test_model.pth", model_contents)},
        data={"tags": ["test"]},
        auth=(api_key, secret),
    )

    assert response.status_code == 200
    response_json = response.json()

    assert response_json["status"] == "OK"

    model_object_id = response_json["model_object_id"]

    image_path = os.path.join(TEST_PATH, "test_fixtures", "110.bmp")

    with open(image_path, "rb") as f:
        image_contents = f.read()

    response = client.post(
        f"/models/{model_object_id}/inference",
        files={"file": ("test_image.bmp", image_contents)},
        auth=(api_key, secret),
    )

    assert response.status_code == 200

    response_json = response.json()

    assert response_json["status"] == "OK"
    assert len(response_json["predictions"]) == 8
