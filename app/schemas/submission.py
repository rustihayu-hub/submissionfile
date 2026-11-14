from pydantic import BaseModel, ConfigDict


class Meta(BaseModel):
    request_id: str


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorBody(BaseModel):
    success: bool = False
    error: ErrorDetail
    meta: Meta


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    assignment_id: str
    user_id: str
    file_id: str
    original_filename: str
    stored_filename: str
    file_type: str
    file_size: int
    status: str
    created_at: str
    updated_at: str
