from pydantic import BaseModel
from uuid import UUID


class BasicResponse(BaseModel):
    status: str


class Label(BaseModel):
    label: str
    polygon: str


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


class TagRow(BaseModel):
    tag_guid: UUID | None
    tag: str


class Tag(BaseModel):
    tag: str
