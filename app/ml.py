import boto3
import cv2
import io
import numpy as np
import os
import torch
import torchvision

from fastapi import (
    Depends,
    File,
    UploadFile,
    status,
)
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPBasicCredentials
from sqlalchemy import select
from typing import Annotated
from uuid import UUID

from .auth import authenticate_user
from .types import Prediction, InferenceResponse
from .db.engine import SessionLocal
from .db.models import MLModelObject


def detect_defects(image_data: cv2.typing.MatLike, model_data) -> list[Prediction]:
    image_width, image_height = image_data.shape[:2]

    resnet_model = torchvision.models.get_model(
        "retinanet_resnet50_fpn",
    )

    checkpoint = torch.load(model_data)
    resnet_model.load_state_dict(checkpoint["model"])

    device = torch.device("cpu")

    CLASSES = ["scratch", "dent", "paint", "pit", "none"]

    resnet_model.eval()
    # sticking with the CPU for now
    #    model.cuda()

    img_c = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB)

    img_t = img_c.transpose([2, 0, 1])

    img_t = np.expand_dims(img_t, axis=0)
    img_t = img_t / 255.0
    img_t = torch.FloatTensor(img_t)

    img_t = img_t.to(device)
    detections = resnet_model(img_t)[0]

    final_predictions = []

    for i in range(0, len(detections["boxes"])):
        confidence = detections["scores"][i]
        label_index = int(detections["labels"][i]) - 1
        box = detections["boxes"][i].detach().cpu().numpy()

        (startX, startY, endX, endY) = box.astype("int")

        # Just a friendly reminder we normalize the coordinates
        # to fit between 0 and 1 :)
        startX = startX / image_width
        startY = startY / image_height
        endX = endX / image_width
        endY = endY / image_height

        final_predictions.append(
            {
                "label": CLASSES[label_index],
                "confidence": float(confidence * 100),
                "polygon": [
                    {"left": startX, "top": startY, "begin_frame": 0, "end_frame": 0},
                    {"left": endX, "top": startY, "begin_frame": 0, "end_frame": 0},
                    {"left": endX, "top": endY, "begin_frame": 0, "end_frame": 0},
                    {"left": startX, "top": endY, "begin_frame": 0, "end_frame": 0},
                ],
            }
        )

    return final_predictions


def model_inference(
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    file_guid: UUID,
    file: Annotated[UploadFile, File(...)],
) -> InferenceResponse:
    with SessionLocal() as session:
        file_query = select(MLModelObject).where(MLModelObject.id == file_guid)
        file_result = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    model_file = file_result[0]  # ModelObject is in the first element of the tuple

    s3 = boto3.client("s3")

    s3_object = s3.get_object(
        Bucket=os.environ["MLMODEL_S3_BUCKET"],
        Key=model_file.s3_object_name,
    )

    model_data = io.BytesIO(s3_object["Body"].read())
    image_data = cv2.imdecode(np.frombuffer(file.file.read(), np.uint8), -1)

    predictions = detect_defects(image_data, model_data)

    return {
        "status": "OK",
        "predictions": predictions,
    }
