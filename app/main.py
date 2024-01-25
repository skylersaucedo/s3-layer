import boto3
from fastapi import Depends, FastAPI, Form, File, UploadFile, status
from fastapi.exceptions import HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasicCredentials
from sqlalchemy import insert, select
from typing import Annotated
from uuid import uuid4, UUID

from .db.models import DatasetObject, DatasetObjectTag
from .db.engine import SessionLocal
from .auth import authenticate_user
from .config import get_settings

app = FastAPI()


settings = get_settings()


@app.get("/")
def get_index():
    """A simple health check endpoint to make sure that the API is up and running."""
    return {"status": "OK"}


@app.post("/")
def post_index(
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
):
    """A simple health check endpoint to make sure that the API is up and running with authentication."""
    return {"status": "OK"}


@app.post("/dataset/upload-file")
def dataset_upload_file(
    file: Annotated[UploadFile, File(...)],
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    tags: Annotated[list[str], Form(...)] = None,
):
    s3 = boto3.client("s3")

    file_name = file.filename
    content_type = file.content_type

    s3_object_name = f"{uuid4()}-{file_name}"

    s3.upload_fileobj(
        file.file,
        settings.dataset_s3_bucket,
        s3_object_name,
    )

    session = SessionLocal()

    dso_result = session.execute(
        insert(DatasetObject).values(
            id=uuid4(),
            name=file_name,
            s3_object_name=s3_object_name,
            content_type=content_type,
        )
    )

    dso_id = dso_result.inserted_primary_key[0]

    if tags:
        for tag in tags:
            session.execute(
                insert(DatasetObjectTag).values(
                    id=uuid4(),
                    dataset_object_id=dso_id,
                    tag=tag,
                )
            )

    session.commit()
    session.close()

    return {
        "status": "OK",
        "s3_object_name": s3_object_name,
        "dataset_object_id": dso_id,
    }


@app.get("/dataset/download-file/{file_guid}")
def dataset_download_file(
    file_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
):
    session = SessionLocal()
    file_query = select(DatasetObject).where(DatasetObject.id == file_guid)
    file_result = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    file = file_result[0]  # DatasetObject is in the first element of the tuple

    s3 = boto3.client("s3")

    s3_object = s3.get_object(
        Bucket=settings.dataset_s3_bucket,
        Key=file.s3_object_name,
    )

    return StreamingResponse(content=s3_object["Body"].iter_chunks())


@app.get("/dataset/list-files")
def dataset_list_files(
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    search_tags: Annotated[list[str], Form(...)] = None,
):
    """List all files in the dataset."""
    session = SessionLocal()

    files_query = select(DatasetObject).order_by("name")
    files_result = session.execute(files_query).all()

    session.close()

    files_list = []
    search_tags_set = frozenset(search_tags) if search_tags else {}

    for row in files_result:
        file = row[0]  # DatasetObject is in the first element of the tuple
        tags = frozenset([t[0].tag for t in file.tags(session=session)])

        if search_tags and len(tags.intersection(search_tags_set)) > 0:
            continue

        files_list.append(
            {
                "id": file.id,
                "name": file.name,
                "s3_object_name": file.s3_object_name,
                "content_type": file.content_type,
                "tags": tags,
            }
        )

    return {
        "status": "OK",
        "files": files_list,
        "count": len(files_list),
    }
