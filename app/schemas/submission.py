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


class HealthData(BaseModel):
    service: str
    status: str


class HealthResponse(BaseModel):
    success: bool = True
    data: HealthData
    meta: Meta


class SubmissionListData(BaseModel):
    items: list[SubmissionOut]
    count: int


class SubmissionListResponse(BaseModel):
    success: bool = True
    data: SubmissionListData
    meta: Meta


class SubmissionCreateData(BaseModel):
    submission: SubmissionOut


class SubmissionCreateResponse(BaseModel):
    success: bool = True
    data: SubmissionCreateData
    meta: Meta


class SubmissionDeleteData(BaseModel):
    id: str
    deleted: bool


class SubmissionDeleteResponse(BaseModel):
    success: bool = True
    data: SubmissionDeleteData
    meta: Meta
