from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: str
    company_id: int


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    user: UserResponse


class HealthResponse(BaseModel):
    status: str
    service: str
    checks: dict[str, str]


class DocumentResponse(BaseModel):
    id: int
    company_id: int
    uploaded_by: int | None
    title: str
    file_name: str
    file_type: str
    file_path: str
    status: str
    raw_text: str | None = None
    created_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]


class CourseGenerateRequest(BaseModel):
    title: str
    document_ids: list[int]
    additional_requirements: str | None = None
    desired_structure: str | None = None


class CourseTopicResponse(BaseModel):
    id: int
    title: str
    content: str
    order_index: int


class CourseModuleResponse(BaseModel):
    id: int
    title: str
    order_index: int
    topics: list[CourseTopicResponse]


class CourseDraftResponse(BaseModel):
    course_id: int
    version_id: int
    title: str
    description: str
    status: str
    modules: list[CourseModuleResponse]


class CourseSummaryResponse(BaseModel):
    course_id: int
    title: str
    description: str
    status: str
    source_documents: list[str]


class CourseListResponse(BaseModel):
    items: list[CourseSummaryResponse]


class CourseTopicUpdateRequest(BaseModel):
    id: int | None = None
    title: str
    content: str
    order_index: int | None = None


class CourseModuleUpdateRequest(BaseModel):
    id: int | None = None
    title: str
    order_index: int | None = None
    topics: list[CourseTopicUpdateRequest]


class CourseDraftUpdateRequest(BaseModel):
    title: str
    description: str = ''
    modules: list[CourseModuleUpdateRequest]


class CourseStatusUpdateRequest(BaseModel):
    status: Literal['draft', 'published']


class TestGenerateRequest(BaseModel):
    title: str
    course_id: int
    desired_question_count: str | None = None


class TestOptionResponse(BaseModel):
    id: int
    text: str
    is_correct: bool
    order_index: int


class TestQuestionResponse(BaseModel):
    id: int
    question_text: str
    order_index: int
    options: list[TestOptionResponse]


class TestDraftResponse(BaseModel):
    test_id: int
    version_id: int
    title: str
    status: str
    course_id: int
    course_title: str
    question_count: int
    questions: list[TestQuestionResponse]


class TestSummaryResponse(BaseModel):
    test_id: int
    title: str
    status: str
    course_id: int
    course_title: str
    question_count: int
    best_attempt_percent: float | None = None


class TestListResponse(BaseModel):
    items: list[TestSummaryResponse]


class TestOptionUpdateRequest(BaseModel):
    id: int | None = None
    text: str
    is_correct: bool
    order_index: int | None = None


class TestQuestionUpdateRequest(BaseModel):
    id: int | None = None
    question_text: str
    order_index: int | None = None
    options: list[TestOptionUpdateRequest]


class TestDraftUpdateRequest(BaseModel):
    title: str
    questions: list[TestQuestionUpdateRequest]


class TestStatusUpdateRequest(BaseModel):
    status: Literal['draft', 'published']


class LearnerTestOptionResponse(BaseModel):
    id: int
    text: str
    order_index: int


class LearnerTestQuestionResponse(BaseModel):
    id: int
    question_text: str
    order_index: int
    options: list[LearnerTestOptionResponse]


class TestAttemptStartResponse(BaseModel):
    attempt_id: int
    attempt_no: int
    test_id: int
    title: str
    course_id: int
    course_title: str
    question_count: int
    started_at: datetime
    questions: list[LearnerTestQuestionResponse]


class AttemptAnswerRequest(BaseModel):
    question_id: int
    selected_option_id: int | None = None


class TestAttemptFinishRequest(BaseModel):
    answers: list[AttemptAnswerRequest]


class AttemptResultOptionResponse(BaseModel):
    id: int
    text: str
    order_index: int
    is_selected: bool
    is_correct: bool


class AttemptResultQuestionResponse(BaseModel):
    id: int
    question_text: str
    order_index: int
    selected_option_id: int | None = None
    is_correct: bool
    options: list[AttemptResultOptionResponse]


class TestAttemptResultResponse(BaseModel):
    attempt_id: int
    attempt_no: int
    test_id: int
    title: str
    course_id: int
    course_title: str
    question_count: int
    correct_answers: int
    score: float
    percent: float
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    questions: list[AttemptResultQuestionResponse]
