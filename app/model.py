import boto3
import os

from fastapi import (
    Depends,
    Form,
    File,
    UploadFile,
    status,
)
from fastapi.exceptions import HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasicCredentials
from sqlalchemy import insert, select
from sqlalchemy.orm import Session
from typing import Annotated
from uuid import uuid4, UUID

from .auth import authenticate_user
from .db.engine import get_local_session
from .db.models import (
    MLModelObject,
    MLModelObjectTag,
)
from .types import BasicResponse


def model_upload_file(
    file: Annotated[UploadFile, File(...)],
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    session: Annotated[Session, Depends(get_local_session)],
    tags: Annotated[list[str], Form(...)] = None,
):
    s3 = boto3.client("s3")

    file_name = file.filename
    content_type = file.content_type

    s3_object_name = f"{uuid4()}-{file_name}"

    s3.upload_fileobj(
        file.file,
        os.environ["MLMODEL_S3_BUCKET"],
        s3_object_name,
    )

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


def model_download_file(
    file_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    session: Annotated[Session, Depends(get_local_session)],
):
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
        Bucket=os.environ["MLMODEL_S3_BUCKET"],
        Key=file.s3_object_name,
    )

    return StreamingResponse(content=s3_object["Body"].iter_chunks())


def model_list_files(
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    session: Annotated[Session, Depends(get_local_session)],
    search_tags: Annotated[list[str], Form(...)] = None,
):
    """List all files in the model."""
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


def model_delete_file(
    file_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    session: Annotated[Session, Depends(get_local_session)],
) -> BasicResponse:
    file_query = select(MLModelObject).where(MLModelObject.id == file_guid)
    file_result = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    file_object = file_result[0]  # ModelObject is in the first element of the tuple

    s3 = boto3.client("s3")

    s3.delete_object(
        Bucket=os.environ["MLMODEL_S3_BUCKET"],
        Key=file_object.s3_object_name,
    )

    session.execute(
        MLModelObjectTag.__table__.delete().where(
            MLModelObjectTag.mlmodel_object_id == file_guid,
        )
    )
    session.commit()

    session.execute(
        MLModelObject.__table__.delete().where(MLModelObject.id == file_guid)
    )
    session.commit()

    return {"status": "OK"}


def model_file_add_tag(
    file_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    session: Annotated[Session, Depends(get_local_session)],
    tag: Annotated[str, Form(...)],
):
    file_query = select(MLModelObject).where(MLModelObject.id == file_guid)
    file_result = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    tag_guid = uuid4()
    session.execute(
        insert(MLModelObjectTag).values(
            id=tag_guid,
            mlmodel_object_id=file_guid,
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


def model_file_delete_tag(
    file_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    session: Annotated[Session, Depends(get_local_session)],
    tag_guid: UUID,
) -> BasicResponse:
    file_query = select(MLModelObject).where(MLModelObject.id == file_guid)
    file_result = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    tag_query = select(MLModelObjectTag).where(
        MLModelObjectTag.mlmodel_object_id == file_guid,
        MLModelObjectTag.id == tag_guid,
    )
    tag_result = session.execute(tag_query).one_or_none()

    if not tag_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )

    session.execute(
        MLModelObjectTag.__table__.delete().where(
            MLModelObjectTag.mlmodel_object_id == file_guid,
            MLModelObjectTag.id == tag_guid,
        )
    )
    session.commit()

    return {"status": "OK"}
