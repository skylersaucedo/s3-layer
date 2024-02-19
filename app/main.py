import boto3
from fastapi import Depends, FastAPI, Form, File, UploadFile, status
from fastapi.exceptions import HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasicCredentials
from sqlalchemy import insert, select
from typing import Annotated
from uuid import uuid4, UUID

from .db.models import (
    DatasetObject,
    DatasetObjectLabel,
    DatasetObjectTag,
    MLModelObject,
    MLModelObjectTag,
)
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


@app.post("/dataset")
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

    with SessionLocal() as session:
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

    return {
        "status": "OK",
        "s3_object_name": s3_object_name,
        "dataset_object_id": dso_id,
    }


@app.get("/dataset/{file_guid}")
def dataset_download_file(
    file_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
):
    with SessionLocal() as session:
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


@app.delete("/dataset/{file_guid}")
def dataset_delete_file(
    file_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
):
    with SessionLocal() as session:
        file_query = select(DatasetObject).where(DatasetObject.id == file_guid)
        file_result = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    file_object = file_result[0]  # DatasetObject is in the first element of the tuple

    s3 = boto3.client("s3")

    s3.delete_object(
        Bucket=settings.dataset_s3_bucket,
        Key=file_object.s3_object_name,
    )

    with SessionLocal() as session:
        session.execute(
            DatasetObjectTag.__table__.delete().where(
                DatasetObjectTag.dataset_object_id == file_guid,
            )
        )
        session.commit()

        session.execute(
            DatasetObject.__table__.delete().where(DatasetObject.id == file_guid)
        )
        session.commit()

    return {"status": "OK"}


@app.post("/dataset/{file_guid}/tags")
def dataset_file_add_tag(
    file_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    tag: Annotated[str, Form(...)],
):
    with SessionLocal() as session:
        file_query = select(DatasetObject).where(DatasetObject.id == file_guid)
        file_result = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    with SessionLocal() as session:
        tag_guid = uuid4()
        session.execute(
            insert(DatasetObjectTag).values(
                id=tag_guid,
                dataset_object_id=file_guid,
                tag=tag,
            )
        )

        session.commit()

    return {
        "status": "OK",
        "tag": {
            "tag_guid": tag_guid,
            "tag": tag,
        },
    }


@app.delete("/dataset/{file_guid}/tags/{tag_guid}")
def dataset_file_delete_tag(
    file_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    tag_guid: UUID,
):
    with SessionLocal() as session:
        file_query = select(DatasetObject).where(DatasetObject.id == file_guid)
        file_result = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    with SessionLocal() as session:
        tag_query = select(DatasetObjectTag).where(
            DatasetObjectTag.dataset_object_id == file_guid,
            DatasetObjectTag.id == tag_guid,
        )
        tag_result = session.execute(tag_query).one_or_none()

    if not tag_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )

    with SessionLocal() as session:
        session.execute(
            DatasetObjectTag.__table__.delete().where(
                DatasetObjectTag.dataset_object_id == file_guid,
                DatasetObjectTag.id == tag_guid,
            )
        )
        session.commit()

    return {"status": "OK"}


@app.post("/dataset/{file_guid}/labels")
def dataset_file_add_label(
    file_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    label: Annotated[str, Form(...)],
    polygon: Annotated[str, Form(...)],
):
    with SessionLocal() as session:
        file_query = select(DatasetObject).where(DatasetObject.id == file_guid)
        file_result = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    with SessionLocal() as session:
        label_guid = uuid4()
        session.execute(
            insert(DatasetObjectLabel).values(
                id=label_guid,
                dataset_object_id=file_guid,
                label=label,
                polygon=polygon,
            )
        )

        session.commit()

    return {
        "status": "OK",
        "label": {
            "label_guid": label_guid,
            "label": label,
            "polygon": polygon,
        },
    }


@app.delete("/dataset/{file_guid}/labels/{label_guid}")
def dataset_file_delete_label(
    file_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    label_guid: UUID,
):
    with SessionLocal() as session:
        file_query = select(DatasetObject).where(DatasetObject.id == file_guid)
        file_result = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    with SessionLocal() as session:
        label_query = select(DatasetObjectLabel).where(
            DatasetObjectLabel.dataset_object_id == file_guid,
            DatasetObjectLabel.id == label_guid,
        )
        label_result = session.execute(label_query).one_or_none()

    if not label_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Label not found",
        )

    with SessionLocal() as session:
        session.execute(
            DatasetObjectLabel.__table__.delete().where(
                DatasetObjectLabel.dataset_object_id == file_guid,
                DatasetObjectLabel.id == label_guid,
            )
        )
        session.commit()

    return {"status": "OK"}


@app.get("/dataset/{file_guid}/details")
def dataset_file_details(
    file_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
):
    with SessionLocal() as session:
        file_query = select(DatasetObject).where(DatasetObject.id == file_guid)
        file_result = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    file = file_result[0]  # DatasetObject is in the first element of the tuple

    return {
        "status": "OK",
        "file": file.as_dict(session=session),
    }


@app.get("/dataset")
def dataset_list_files(
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    search_tags: Annotated[list[str], Form(...)] = None,
):
    """List all files in the dataset."""
    with SessionLocal() as session:
        files_query = select(DatasetObject).order_by("name")
        files_result = session.execute(files_query).all()

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


@app.post("/models")
def model_upload_file(
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
        settings.mlmodel_s3_bucket,
        s3_object_name,
    )

    with SessionLocal() as session:
        mo_result = session.execute(
            insert(MLModelObject).values(
                id=uuid4(),
                name=file_name,
                s3_object_name=s3_object_name,
                content_type=content_type,
            )
        )

        mo_id = mo_result.inserted_primary_key[0]

        if tags:
            for tag in tags:
                session.execute(
                    insert(MLModelObjectTag).values(
                        id=uuid4(),
                        mlmodel_object_id=mo_id,
                        tag=tag,
                    )
                )

        session.commit()

    return {
        "status": "OK",
        "s3_object_name": s3_object_name,
        "model_object_id": mo_id,
    }


@app.get("/models/{file_guid}")
def model_download_file(
    file_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
):
    with SessionLocal() as session:
        file_query = select(MLModelObject).where(MLModelObject.id == file_guid)
        file_result = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    file = file_result[0]  # ModelObject is in the first element of the tuple

    s3 = boto3.client("s3")

    s3_object = s3.get_object(
        Bucket=settings.mlmodel_s3_bucket,
        Key=file.s3_object_name,
    )

    return StreamingResponse(content=s3_object["Body"].iter_chunks())


@app.get("/models")
def model_list_files(
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    search_tags: Annotated[list[str], Form(...)] = None,
):
    """List all files in the model."""
    with SessionLocal() as session:
        files_query = select(MLModelObject).order_by("name")
        files_result = session.execute(files_query).all()

    files_list = []
    search_tags_set = frozenset(search_tags) if search_tags else {}

    for row in files_result:
        file = row[0]  # ModelObject is in the first element of the tuple
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
