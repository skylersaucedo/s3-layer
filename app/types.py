from pydantic import BaseModel
from uuid import UUID

import datetime


class BasicResponse(BaseModel):
    status: str


class Point(BaseModel):
    x: float
    y: float


class Label(BaseModel):
    label_guid: UUID | None
    label: str
    polygon: list[Point]


class Node(BaseModel):
    left: float
    top: float
    begin_frame: int
    end_frame: int


class Prediction(BaseModel):
    label: str
    confidence: float
    polygon: list[Node]


class InferenceResponse(BaseModel):
    status: str
    predictions: list[Prediction]


class Tag(BaseModel):
    tag_guid: UUID | None
    tag: str


class UploadFileResponse(BaseModel):
    status: str
    s3_object_name: str
    dataset_object_id: UUID


class DatasetFile(BaseModel):
    id: UUID
    name: str
    s3_object_name: str
    content_type: str
    upload_date: datetime.datetime
    modified_date: datetime.datetime
    file_hash_sha1: str
    tags: list[Tag]
    labels: list[Label]


class DatasetFileDetails(BaseModel):
    status: str
    file: DatasetFile


class ListFilesResponse(BaseModel):
    status: str
    files: list[DatasetFile]
    count: int
    total_count: int
