from pydantic import BaseModel, Field


class QueueItemCreate(BaseModel):
    language: str
    speakers: int = Field(ge=1, le=5)


class QueueItem(BaseModel):
    id: int
    original_name: str
    size_bytes: int
    language: str
    speakers: int
    status: str
    preview: str | None = None
    error_message: str | None = None


class QueueItemUpdate(BaseModel):
    language: str | None = None
    speakers: int | None = Field(None, ge=1, le=5)


class StartTranscriptionRequest(BaseModel):
    # TODO: Add fields if we need batch options later.
    pass
