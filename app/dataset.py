import boto3
import hashlib
import json
import logging
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
from mimetypes import guess_type
from sqlalchemy import insert, select, func
from sqlalchemy.orm import Session
from typing import Annotated
from uuid import uuid4, UUID

from .auth import authenticate_user
from .db.engine import get_local_session
from .db.models import (
    DatasetObject,
    DatasetObjectLabel,
    DatasetObjectTag,
)
from .types import (
    BasicResponse,
    UploadFileResponse,
    DatasetFileDetails,
    ListFilesResponse,
)


logger = logging.getLogger(__name__)


def dataset_upload_file(
    file: Annotated[UploadFile, File(...)],
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    session: Annotated[Session, Depends(get_local_session)],
    tags: Annotated[list[str], Form(...)] = None,
) -> UploadFileResponse:
    s3 = boto3.client("s3")

    file_name = file.filename
    content_type, encoding = guess_type(file.filename)

    # calculate the file's sha1 hash
    sha1 = hashlib.sha1()

    while True:
        data = file.file.read(65536)
        if not data:
            break
        sha1.update(data)

    # seek back to the beginning of the file
    file.file.seek(0)

    # see if a file with this hash already exists
    file_query = select(DatasetObject).where(
        DatasetObject.file_hash_sha1 == sha1.hexdigest()
    )
    file_result = session.execute(file_query).all()

    if len(file_result) > 0 and len(file_result[0]) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File already exists",
        )

    s3_object_name = f"{uuid4()}-{file_name}"

    s3.upload_fileobj(
        file.file,
        os.environ["DATASET_S3_BUCKET"],
        s3_object_name,
    )

    dso_result = session.execute(
        insert(DatasetObject).values(
            id=uuid4(),
            name=file_name,
            s3_object_name=s3_object_name,
            content_type=content_type,
            file_hash_sha1=sha1.hexdigest(),
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


def dataset_download_file(
    file_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    session: Annotated[Session, Depends(get_local_session)],
):
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
        Bucket=os.environ["DATASET_S3_BUCKET"],
        Key=file.s3_object_name,
    )

    return StreamingResponse(content=s3_object["Body"].iter_chunks())


def dataset_delete_file(
    file_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    session: Annotated[Session, Depends(get_local_session)],
) -> BasicResponse:
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
        Bucket=os.environ["DATASET_S3_BUCKET"],
        Key=file_object.s3_object_name,
    )

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


def dataset_file_add_tag(
    file_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    session: Annotated[Session, Depends(get_local_session)],
    tag: Annotated[str, Form(...)] = None,
):
    file_query = select(DatasetObject).where(DatasetObject.id == file_guid)
    file_result = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    existing_tags = file_result[0].tags(session=session)

    if tag in [t[0].tag for t in existing_tags]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag already exists",
        )

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


def dataset_file_delete_tag(
    file_guid: UUID,
    tag_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    session: Annotated[Session, Depends(get_local_session)],
) -> BasicResponse:
    file_query = select(DatasetObject).where(DatasetObject.id == file_guid)
    file_result = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

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

    session.execute(
        DatasetObjectTag.__table__.delete().where(
            DatasetObjectTag.dataset_object_id == file_guid,
            DatasetObjectTag.id == tag_guid,
        )
    )

    session.commit()

    return {"status": "OK"}


def dataset_file_add_label(
    file_guid: UUID,
    label: Annotated[str, Form(...)],
    polygon: Annotated[str, Form(...)],
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    session: Annotated[Session, Depends(get_local_session)],
):
    """Add a label to a file in the dataset. The polygon is a JSON string with a list of nodes in the form of {"x": 0.0, "y": 0.0}.
    X and Y are represented as a percentage of the width and height of the image or video.
    """
    file_query = select(DatasetObject).where(DatasetObject.id == file_guid)
    file_result: DatasetObject = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    try:
        polygon_parsed = json.loads(polygon)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid polygon",
        )

    for node in polygon_parsed:
        if "left" in node:
            node["x"] = node["left"]
            node.pop("left")

        if "top" in node:
            node["y"] = node["top"]
            node.pop("top")

        if "x" not in node or "y" not in node:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid polygon: missing x or y",
            )

    existing_labels = file_result[0].labels(session=session)

    for existing_label in existing_labels:
        if existing_label[0].label == label:
            if existing_label[0].polygon == polygon:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Label already exists",
                )

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
            "polygon": polygon_parsed,
        },
    }


def dataset_file_delete_label(
    file_guid: UUID,
    label_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    session: Annotated[Session, Depends(get_local_session)],
) -> BasicResponse:
    file_query = select(DatasetObject).where(DatasetObject.id == file_guid)
    file_result = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

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

    session.execute(
        DatasetObjectLabel.__table__.delete().where(
            DatasetObjectLabel.dataset_object_id == file_guid,
            DatasetObjectLabel.id == label_guid,
        )
    )

    session.commit()

    return {"status": "OK"}


def dataset_file_update_label(
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    session: Annotated[Session, Depends(get_local_session)],
    file_guid: UUID,
    label_guid: UUID,
    label: Annotated[str, Form(...)],
    polygon: Annotated[str, Form(...)],
) -> BasicResponse:
    file_query = select(DatasetObject).where(DatasetObject.id == file_guid)
    file_result = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

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

    try:
        polygon_parsed = json.loads(polygon)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid polygon",
        )

    for node in polygon_parsed:
        if "left" in node:
            node["x"] = node["left"]
            node.pop("left")

        if "top" in node:
            node["y"] = node["top"]
            node.pop("top")

        if "x" not in node or "y" not in node:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid polygon: missing x or y",
            )

    session.execute(
        DatasetObjectLabel.__table__.update()
        .where(
            DatasetObjectLabel.dataset_object_id == file_guid,
            DatasetObjectLabel.id == label_guid,
        )
        .values(
            label=label,
            polygon=polygon,
        )
    )
    session.commit()

    return {"status": "OK"}


def dataset_file_details(
    file_guid: UUID,
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    session: Annotated[Session, Depends(get_local_session)],
) -> DatasetFileDetails:
    file_query = select(DatasetObject).where(DatasetObject.id == file_guid)
    file_result = session.execute(file_query).one_or_none()

    file = file_result[0]  # DatasetObject is in the first element of the tuple

    file_as_dict = file.as_dict(session=session)

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    return {
        "status": "OK",
        "file": file_as_dict,
    }


def dataset_list_files(
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    session: Annotated[Session, Depends(get_local_session)],
    search_tags: str = None,
    limit: int = None,
    offset: int = None,
) -> ListFilesResponse:
    """
    List all files in the dataset. Search tags is a comma separated list of tags
    to filter the files by. Limit is the number of files to return. Offset is the
    number of files to skip.
    """

    total_files = session.query(func.count(DatasetObject.id)).scalar()

    files_query = select(DatasetObject).order_by("name")

    if limit:
        files_query = files_query.limit(limit)

    if offset:
        files_query = files_query.offset(offset)

    files_result = session.execute(files_query).all()

    files_list = []

    search_tags_set = frozenset(search_tags.split(",")) if search_tags else {}

    for row in files_result:
        file = row[0]  # DatasetObject is in the first element of the tuple
        tags = frozenset([t[0].tag for t in file.tags(session=session)])

        if search_tags and len(tags.intersection(search_tags_set)) > 0:
            continue

        files_list.append(file.as_dict(session=session))

    return {
        "status": "OK",
        "files": files_list,
        "count": len(files_list),
        "total_count": total_files,
    }
