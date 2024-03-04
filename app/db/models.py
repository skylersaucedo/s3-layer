import hashlib
import json
import logging
import os
import uuid

from sqlalchemy import select, String, Text, UUID, DateTime
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy import sql


from .engine import Base

logger = logging.getLogger(__name__)


class APICredentials(Base):
    __tablename__ = "api_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True
    )
    friendly_name: Mapped[str] = mapped_column(String(30))
    api_key: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    api_secret: Mapped[str] = mapped_column(String(64))
    salt: Mapped[str] = mapped_column(String(30))

    def __repr__(self):
        return f"<APICredentials(friendly_name={self.friendly_name}, api_key={self.api_key}>"

    def __str__(self):
        return f"<APICredentials(friendly_name={self.friendly_name}, api_key={self.api_key}>"

    @classmethod
    def hash_password(self, password: str, salt: str) -> str:
        salted_password = password + salt + os.environ["SECRET_KEY"]
        hashed_password = hashlib.sha256(salted_password.encode("utf8")).hexdigest()

        return hashed_password

    def validate_password(self, password: str) -> bool:
        hashed_password = self.hash_password(password, self.salt)

        return hashed_password == self.api_secret


class DatasetObject(Base):
    __tablename__ = "dataset_objects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True
    )
    name: Mapped[str] = mapped_column(String(512))
    s3_object_name: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    content_type = mapped_column(String(128))
    upload_date = mapped_column(DateTime(timezone=True), server_default=sql.func.now())
    modified_date = mapped_column(
        DateTime(timezone=True), onupdate=sql.func.now(), default=sql.func.now()
    )
    file_hash_sha1 = mapped_column(
        String(40)
    )  # SHA1 hash of the file to prevent duplicates

    def __repr__(self):
        return f"<Dataset(name={self.name}, s3_object_name={self.s3_object_name}>"

    def __str__(self):
        return f"<Dataset(name={self.name}, s3_object_name={self.s3_object_name}>"

    @classmethod
    def polygon_string_to_json(cls, polygon_string: str) -> list[dict]:
        try:
            polygon_list = json.loads(polygon_string)
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON string: {polygon_string}")
            polygon_list = []
        except TypeError:
            logger.error(f"Error decoding JSON string: {polygon_string}")
            polygon_list = []

        return cls.clean_polygons(polygon_list)

    @classmethod
    def clean_polygons(cls, polygon_list: list[dict]) -> list[dict]:
        if polygon_list is None:
            logger.error(f"Invalid polygon list: {polygon_list}")
            return []

        if type(polygon_list) is not list:
            logger.error(f"Invalid polygon list: {polygon_list}")
            return []

        clean_list = []

        for polygon in polygon_list:
            x = polygon.get("x", None)
            y = polygon.get("y", None)

            if x is None and "left" in polygon:
                x = polygon["left"]

            if y is None and "top" in polygon:
                y = polygon["top"]

            clean_polygon = {
                "x": x,
                "y": y,
            }

            clean_list.append(clean_polygon)

        return clean_list

    def as_dict(self, session):
        return {
            "id": self.id,
            "name": self.name,
            "s3_object_name": self.s3_object_name,
            "content_type": self.content_type,
            "upload_date": self.upload_date,
            "modified_date": self.modified_date,
            "file_hash_sha1": self.file_hash_sha1,
            "tags": sorted(
                [
                    {
                        "tag_guid": t[0].id,
                        "tag": t[0].tag,
                    }
                    for t in self.tags(session)
                ],
                key=lambda x: x["tag"],
            ),
            "labels": sorted(
                [
                    {
                        "label_guid": l[0].id,
                        "label": l[0].label,
                        "polygon": DatasetObject.polygon_string_to_json(
                            l[0].polygon or "[]"
                        ),
                    }
                    for l in self.labels(session)
                ],
                key=lambda x: x["label"],
            ),
        }

    def tags(self, session):
        stmt = select(DatasetObjectTag).where(
            DatasetObjectTag.dataset_object_id == self.id
        )

        result = session.execute(stmt)

        return result.all()

    def labels(self, session):
        stmt = select(DatasetObjectLabel).where(
            DatasetObjectLabel.dataset_object_id == self.id
        )

        result = session.execute(stmt)

        return result.all()


class DatasetObjectTag(Base):
    __tablename__ = "dataset_object_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True
    )
    dataset_object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    tag: Mapped[str] = mapped_column(String(64), index=True)

    def __repr__(self):
        return f"<DatasetObjectTag(dataset_object_id={self.dataset_object_id}, tag={self.tag}>"

    def __str__(self):
        return f"<DatasetObjectTag(dataset_object_id={self.dataset_object_id}, tag={self.tag}>"


class DatasetObjectLabel(Base):
    __tablename__ = "dataset_object_labels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True
    )
    dataset_object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    label: Mapped[str] = mapped_column(String(128), index=True)
    polygon: Mapped[str] = mapped_column(Text)

    def __repr__(self):
        return f"<DatasetObjectLabel(dataset_object_id={self.dataset_object_id}, label={self.label}>"

    def __str__(self):
        return f"<DatasetObjectLabel(dataset_object_id={self.dataset_object_id}, label={self.label}>"


class MLModelObject(Base):
    __tablename__ = "mlmodel_objects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True
    )
    name: Mapped[str] = mapped_column(String(512))
    s3_object_name: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    content_type = mapped_column(String(128))

    def __repr__(self):
        return f"<MLModel(name={self.name}, s3_object_name={self.s3_object_name}>"

    def __str__(self):
        return f"<MLModel(name={self.name}, s3_object_name={self.s3_object_name}>"

    def as_dict(self, session):
        return {
            "id": self.id,
            "name": self.name,
            "s3_object_name": self.s3_object_name,
            "content_type": self.content_type,
            "tags": set([t[0].tag for t in self.tags()]),
        }

    def tags(self, session):
        stmt = select(MLModelObjectTag).where(
            MLModelObjectTag.mlmodel_object_id == self.id
        )

        result = session.execute(stmt)

        return result.all()


class MLModelObjectTag(Base):
    __tablename__ = "mlmodel_object_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True
    )
    mlmodel_object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    tag: Mapped[str] = mapped_column(String(64), index=True)

    def __repr__(self):
        return f"<MLModelObjectTag(model_object_id={self.mlmodel_object_id}, tag={self.tag}>"

    def __str__(self):
        return f"<MLModelObjectTag(model_object_id={self.mlmodel_object_id}, tag={self.tag}>"
