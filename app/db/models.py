import uuid
import hashlib
from .engine import Base
from ..config import get_settings
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy import select, String, UUID

settings = get_settings()


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
        salted_password = password + salt + settings.secret_key
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

    def __repr__(self):
        return f"<Dataset(name={self.name}, s3_object_name={self.s3_object_name}>"

    def __str__(self):
        return f"<Dataset(name={self.name}, s3_object_name={self.s3_object_name}>"

    def tags(self, session):
        stmt = select(DatasetObjectTag).where(
            DatasetObjectTag.dataset_object_id == self.id
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
