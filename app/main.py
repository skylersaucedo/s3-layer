import dotenv
import os

dotenv.load_dotenv()

from fastapi import (
    Depends,
    FastAPI,
)

from fastapi.security import HTTPBasicCredentials
from mimetypes import init as mimetypes_init

from typing import Annotated

from .auth import authenticate_user
from .types import (
    BasicResponse,
    InferenceResponse,
    UploadFileResponse,
)
from .dataset import (
    dataset_upload_file,
    dataset_list_files,
    dataset_file_details,
    dataset_download_file,
    dataset_file_add_label,
    dataset_file_add_tag,
    dataset_file_update_label,
    dataset_file_delete_label,
    dataset_file_delete_tag,
    dataset_delete_file,
)
from .ml import model_inference
from .model import (
    model_upload_file,
    model_download_file,
    model_list_files,
    model_delete_file,
    model_file_add_tag,
    model_file_delete_tag,
)


mimetypes_init()

app = FastAPI()
app.debug = os.getenv("DEBUG", False)


@app.get("/")
def get_index() -> BasicResponse:
    """A simple health check endpoint to make sure that the API is up and running."""
    return {"status": "OK"}


@app.post("/")
def post_index(
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
) -> BasicResponse:
    """A simple health check endpoint to make sure that the API is up and running with authentication."""
    return {"status": "OK"}


app.add_api_route(
    path="/dataset",
    endpoint=dataset_list_files,
    methods=["GET"],
    summary="List files in the S3 dataset.",
    description=dataset_list_files.__doc__,
)

app.add_api_route(
    path="/dataset",
    endpoint=dataset_upload_file,
    methods=["POST"],
    summary="Upload file to the S3 dataset.",
    description=dataset_upload_file.__doc__,
    response_model=UploadFileResponse,
)

app.add_api_route(
    path="/dataset/{file_guid}/details",
    endpoint=dataset_file_details,
    methods=["GET"],
    summary="Get details of a dataset file.",
    description=dataset_file_details.__doc__,
)

app.add_api_route(
    path="/dataset/{file_guid}/labels/{label_guid}",
    endpoint=dataset_file_update_label,
    methods=["PUT"],
    response_model=BasicResponse,
    summary="Update a label in a dataset file.",
    description=dataset_file_update_label.__doc__,
)

app.add_api_route(
    path="/dataset/{file_guid}/labels/{label_guid}",
    endpoint=dataset_file_delete_label,
    methods=["DELETE"],
    response_model=BasicResponse,
    summary="Delete a label in a dataset file.",
    description=dataset_file_delete_label.__doc__,
)

app.add_api_route(
    path="/dataset/{file_guid}/labels",
    endpoint=dataset_file_add_label,
    methods=["POST"],
    summary="Add a label to a dataset file.",
    description=dataset_file_add_label.__doc__,
)

app.add_api_route(
    path="/dataset/{file_guid}",
    endpoint=dataset_download_file,
    methods=["GET"],
    summary="Download a file from the S3 dataset.",
    description=dataset_download_file.__doc__,
)

app.add_api_route(
    path="/dataset/{file_guid}",
    endpoint=dataset_delete_file,
    methods=["DELETE"],
    response_model=BasicResponse,
    summary="Delete a file from the S3 dataset.",
    description=dataset_delete_file.__doc__,
)

app.add_api_route(
    path="/dataset/{file_guid}/tags",
    endpoint=dataset_file_add_tag,
    methods=["POST"],
    summary="Add a tag to a dataset file.",
    description=dataset_file_add_tag.__doc__,
)

app.add_api_route(
    path="/dataset/{file_guid}/tags/{tag_guid}",
    endpoint=dataset_file_delete_tag,
    methods=["DELETE"],
    response_model=BasicResponse,
    summary="Delete a tag from a dataset file.",
    description=dataset_file_delete_tag.__doc__,
)

app.add_api_route(
    path="/models",
    endpoint=model_upload_file,
    methods=["POST"],
    summary="Upload model to the S3 model bucket.",
    description=model_upload_file.__doc__,
)

app.add_api_route(
    path="/models",
    endpoint=model_list_files,
    methods=["GET"],
    summary="List files in the S3 model bucket.",
    description=model_list_files.__doc__,
)

app.add_api_route(
    path="/models/{file_guid}",
    endpoint=model_download_file,
    methods=["GET"],
    summary="Download a file from the S3 model bucket.",
    description=model_download_file.__doc__,
)

app.add_api_route(
    path="/models/{file_guid}",
    endpoint=model_delete_file,
    methods=["DELETE"],
    response_model=BasicResponse,
    summary="Delete a file from the S3 model bucket.",
    description=model_delete_file.__doc__,
)

app.add_api_route(
    path="/models/{file_guid}/tags",
    endpoint=model_file_add_tag,
    methods=["POST"],
    summary="Add a tag to a model file.",
    description=model_file_add_tag.__doc__,
)

app.add_api_route(
    path="/models/{file_guid}/tags/{tag_guid}",
    endpoint=model_file_delete_tag,
    methods=["DELETE"],
    response_model=BasicResponse,
    summary="Delete a tag from a model file.",
    description=model_file_delete_tag.__doc__,
)

app.add_api_route(
    path="/models/{file_guid}/inference",
    endpoint=model_inference,
    methods=["POST"],
    summary="Infer on a model file.",
    response_model=InferenceResponse,
    description=model_inference.__doc__,
)
