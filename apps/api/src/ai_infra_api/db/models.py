import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ai_infra_api.db.base import Base


class UserRole(StrEnum):
    ADMIN = "admin"
    VIEWER = "viewer"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            values_callable=lambda enum_type: [item.value for item in enum_type],
            native_enum=False,
            length=16,
        ),
        default=UserRole.ADMIN,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Server(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "servers"

    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    hostname: Mapped[str | None] = mapped_column(String(255))
    host: Mapped[str | None] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(32), default="local")
    provider: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    os: Mapped[str | None] = mapped_column(String(128))
    kernel: Mapped[str | None] = mapped_column(String(128))
    cpu_model: Mapped[str | None] = mapped_column(String(255))
    cpu_cores: Mapped[int | None] = mapped_column(Integer)
    memory_total: Mapped[int | None] = mapped_column(BigInteger)
    disk_total: Mapped[int | None] = mapped_column(BigInteger)
    agent_version: Mapped[str | None] = mapped_column(String(64))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class ServerAgent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "server_agents"

    server_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"), unique=True, index=True
    )
    token_hash: Mapped[str | None] = mapped_column(String(255), unique=True)
    version: Mapped[str | None] = mapped_column(String(64))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ServerModelDirectory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "server_model_directories"
    __table_args__ = (UniqueConstraint("server_id", "path"),)

    server_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"), index=True
    )
    path: Mapped[str] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=True)


class GPU(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gpus"
    __table_args__ = (UniqueConstraint("server_id", "gpu_index"),)

    server_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"), index=True
    )
    gpu_index: Mapped[int] = mapped_column(Integer)
    uuid: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    vendor: Mapped[str] = mapped_column(String(64), default="NVIDIA")
    name: Mapped[str] = mapped_column(String(255))
    memory_total: Mapped[int] = mapped_column(BigInteger)
    driver_version: Mapped[str | None] = mapped_column(String(64))
    cuda_version: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="unknown", index=True)


class GPUMetric(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "gpu_metrics"
    __table_args__ = (Index("ix_gpu_metrics_gpu_timestamp", "gpu_id", "timestamp"),)

    gpu_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gpus.id", ondelete="CASCADE"), index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    utilization: Mapped[float | None] = mapped_column(Float)
    memory_used: Mapped[int | None] = mapped_column(BigInteger)
    temperature: Mapped[float | None] = mapped_column(Float)
    power_usage: Mapped[float | None] = mapped_column(Float)
    power_limit: Mapped[float | None] = mapped_column(Float)
    fan_speed: Mapped[float | None] = mapped_column(Float)


class Model(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "models"
    __table_args__ = (UniqueConstraint("source", "source_id"),)

    source: Mapped[str] = mapped_column(String(32), default="local")
    source_id: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255), index=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    architecture: Mapped[str | None] = mapped_column(String(128))
    model_type: Mapped[str | None] = mapped_column(String(64), index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class ModelFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_files"
    __table_args__ = (UniqueConstraint("server_id", "path"),)

    model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("models.id", ondelete="CASCADE"), index=True
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"), index=True
    )
    path: Mapped[str] = mapped_column(Text)
    size: Mapped[int | None] = mapped_column(BigInteger)
    format: Mapped[str | None] = mapped_column(String(32))
    quantization: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str | None] = mapped_column(String(32))
    revision: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="discovered", index=True)


class ModelDownloadTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_download_tasks"

    model_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("models.id", ondelete="SET NULL"), index=True
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str] = mapped_column(String(255))
    target_path: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    downloaded_size: Mapped[int] = mapped_column(BigInteger, default=0)
    total_size: Mapped[int | None] = mapped_column(BigInteger)
    speed_bytes_per_second: Mapped[int | None] = mapped_column(BigInteger)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Deployment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "deployments"
    __table_args__ = (UniqueConstraint("server_id", "port"),)

    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    model_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("model_files.id", ondelete="RESTRICT"), index=True
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"), index=True
    )
    backend: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="stopped", index=True)
    port: Mapped[int] = mapped_column(Integer)
    endpoint: Mapped[str | None] = mapped_column(String(512))
    container_id: Mapped[str | None] = mapped_column(String(128))
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DeploymentGPU(Base):
    __tablename__ = "deployment_gpus"

    deployment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deployments.id", ondelete="CASCADE"), primary_key=True
    )
    gpu_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gpus.id", ondelete="RESTRICT"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ApiEndpoint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "api_endpoints"

    deployment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deployments.id", ondelete="CASCADE"), unique=True, index=True
    )
    model_name: Mapped[str] = mapped_column(String(255), index=True)
    url: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    port: Mapped[int] = mapped_column(Integer)


class Notification(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notifications"

    level: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(128), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(128))
    success: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str | None] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
