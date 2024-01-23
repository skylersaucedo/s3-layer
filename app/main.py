from typing import Annotated
import boto3
from fastapi import FastAPI, Form, File, UploadFile
from uuid import uuid4

from .config import get_settings

app = FastAPI()

s3 = boto3.client("s3")
settings = get_settings()


@app.get("/")
def index():
    return {"status": "OK"}


@app.post("/dataset/upload-file")
async def dataset_upload_file(
    file: Annotated[UploadFile, File(...)],
    tags: Annotated[list[str], Form(...)],
):
    file_name = file.filename
    content_type = file.content_type

    upload_file_name = f"{uuid4()}-{file_name}"

    s3.upload_fileobj(
        file.file,
        settings.dataset_s3_bucket,
        upload_file_name,
    )

    return {
        "status": "OK",
        "uploaded_file_name": upload_file_name,
    }


@app.get("/dataset/download-file/{file_guid}")
async def download_file(file_guid: str):
    return {"message": "File downloaded successfully!"}


@app.get("/dataset/list-files")
def list_files():
    return {"message": "List of files!"}
