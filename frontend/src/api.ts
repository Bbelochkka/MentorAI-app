const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export interface LoginPayload {
  email: string;
  password: string;
}

export interface UserDto {
  id: number;
  email: string;
  name: string;
  role: string;
  company_id?: number;
}

export interface LoginResponse {
  access_token: string;
  token_type: 'bearer';
  user: UserDto;
}

export interface DocumentDto {
  id: number;
  company_id: number;
  uploaded_by: number | null;
  title: string;
  file_name: string;
  file_type: string;
  file_path: string;
  status: string;
  raw_text: string | null;
  created_at: string;
}

export interface DocumentListResponse {
  items: DocumentDto[];
}

function getToken(): string | null {
  return localStorage.getItem('mentorai_token');
}

export function getStoredUser(): UserDto | null {
  const raw = localStorage.getItem('mentorai_user');
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UserDto;
  } catch {
    return null;
  }
}

export function isLearnerUser(user: UserDto | null): boolean {
  return user?.role === 'employer';
}

async function parseError(response: Response): Promise<Error> {
  const error = await response
    .json()
    .catch(() => ({ detail: 'Ошибка запроса' }));

  if (Array.isArray(error.detail)) {
    const message = error.detail
      .map((item: { msg?: string }) => item?.msg)
      .filter(Boolean)
      .join('; ');
    return new Error(message || 'Ошибка запроса');
  }

  return new Error(error.detail ?? 'Ошибка запроса');
}

async function authorizedFetch(input: RequestInfo | URL, init?: RequestInit) {
  const token = getToken();

  const headers = new Headers(init?.headers ?? {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  return fetch(input, {
    ...init,
    headers
  });
}

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  const response = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export async function getMe(): Promise<UserDto> {
  const response = await authorizedFetch(`${API_URL}/api/me`);

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export async function getDocuments(): Promise<DocumentDto[]> {
  const response = await authorizedFetch(`${API_URL}/api/documents`);

  if (!response.ok) {
    throw await parseError(response);
  }

  const data: DocumentListResponse = await response.json();
  return data.items;
}

export async function getDocument(documentId: number): Promise<DocumentDto> {
  const response = await authorizedFetch(`${API_URL}/api/documents/${documentId}`);

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export async function uploadDocument(file: File): Promise<DocumentDto> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await authorizedFetch(`${API_URL}/api/documents/upload`, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export async function deleteDocument(documentId: number): Promise<{ message: string }> {
  const response = await authorizedFetch(`${API_URL}/api/documents/${documentId}`, {
    method: 'DELETE'
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export async function processDocument(documentId: number): Promise<DocumentDto> {
  const response = await authorizedFetch(`${API_URL}/api/documents/${documentId}/process`, {
    method: 'POST'
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export interface CourseGeneratePayload {
  title: string;
  document_ids: number[];
  additional_requirements?: string;
  desired_structure?: string;
}

export interface CourseTopicDto {
  id: number;
  title: string;
  content: string;
  order_index: number;
}

export interface CourseModuleDto {
  id: number;
  title: string;
  order_index: number;
  topics: CourseTopicDto[];
}

export interface CourseDraftDto {
  course_id: number;
  version_id: number;
  title: string;
  description: string;
  status: string;
  modules: CourseModuleDto[];
}

export interface CourseTopicUpdatePayload {
  id?: number;
  title: string;
  content: string;
  order_index?: number;
}

export interface CourseModuleUpdatePayload {
  id?: number;
  title: string;
  order_index?: number;
  topics: CourseTopicUpdatePayload[];
}

export interface CourseDraftUpdatePayload {
  title: string;
  description: string;
  modules: CourseModuleUpdatePayload[];
}

export interface CourseStatusUpdatePayload {
  status: 'draft' | 'published';
}

export async function generateCourseDraft(payload: CourseGeneratePayload): Promise<CourseDraftDto> {
  const response = await authorizedFetch(`${API_URL}/api/courses/generate-draft`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export async function updateCourseDraft(courseId: number, payload: CourseDraftUpdatePayload): Promise<CourseDraftDto> {
  const response = await authorizedFetch(`${API_URL}/api/courses/${courseId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export interface CourseSummaryDto {
  course_id: number;
  title: string;
  description: string;
  status: string;
  source_documents: string[];
}

export interface CourseListResponse {
  items: CourseSummaryDto[];
}

export async function getCourses(): Promise<CourseSummaryDto[]> {
  const response = await authorizedFetch(`${API_URL}/api/courses`);

  if (!response.ok) {
    throw await parseError(response);
  }

  const data: CourseListResponse = await response.json();
  return data.items;
}

export async function updateCourseStatus(courseId: number, payload: CourseStatusUpdatePayload): Promise<CourseDraftDto> {
  const response = await authorizedFetch(`${API_URL}/api/courses/${courseId}/status`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export async function getCourse(courseId: number): Promise<CourseDraftDto> {
  const response = await authorizedFetch(`${API_URL}/api/courses/${courseId}`);

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export async function deleteCourse(courseId: number): Promise<{ message: string }> {
  const response = await authorizedFetch(`${API_URL}/api/courses/${courseId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}


export interface TestGeneratePayload {
  title: string;
  course_id: number;
  desired_question_count?: string;
}

export interface TestOptionDto {
  id: number;
  text: string;
  is_correct: boolean;
  order_index: number;
}

export interface TestQuestionDto {
  id: number;
  question_text: string;
  order_index: number;
  options: TestOptionDto[];
}

export interface TestOptionUpdatePayload {
  id?: number;
  text: string;
  is_correct: boolean;
  order_index?: number;
}

export interface TestQuestionUpdatePayload {
  id?: number;
  question_text: string;
  order_index?: number;
  options: TestOptionUpdatePayload[];
}

export interface TestDraftUpdatePayload {
  title: string;
  questions: TestQuestionUpdatePayload[];
}

export interface TestDraftDto {
  test_id: number;
  version_id: number;
  title: string;
  status: string;
  course_id: number;
  course_title: string;
  question_count: number;
  questions: TestQuestionDto[];
}

export interface TestSummaryDto {
  test_id: number;
  title: string;
  status: string;
  course_id: number;
  course_title: string;
  question_count: number;
  best_attempt_percent?: number | null;
}

export interface TestListResponse {
  items: TestSummaryDto[];
}

export interface TestStatusUpdatePayload {
  status: 'draft' | 'published';
}

export async function getTests(): Promise<TestSummaryDto[]> {
  const response = await authorizedFetch(`${API_URL}/api/tests`);

  if (!response.ok) {
    throw await parseError(response);
  }

  const data: TestListResponse = await response.json();
  return data.items;
}

export async function generateTestDraft(payload: TestGeneratePayload): Promise<TestDraftDto> {
  const response = await authorizedFetch(`${API_URL}/api/tests/generate-draft`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export async function getTest(testId: number): Promise<TestDraftDto> {
  const response = await authorizedFetch(`${API_URL}/api/tests/${testId}`);

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export async function updateTestStatus(testId: number, payload: TestStatusUpdatePayload): Promise<TestDraftDto> {
  const response = await authorizedFetch(`${API_URL}/api/tests/${testId}/status`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export async function deleteTest(testId: number): Promise<{ message: string }> {
  const response = await authorizedFetch(`${API_URL}/api/tests/${testId}`, {
    method: 'DELETE'
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}


export async function updateTestDraft(testId: number, payload: TestDraftUpdatePayload): Promise<TestDraftDto> {
  const response = await authorizedFetch(`${API_URL}/api/tests/${testId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}


export interface LearnerTestOptionDto {
  id: number;
  text: string;
  order_index: number;
}

export interface LearnerTestQuestionDto {
  id: number;
  question_text: string;
  order_index: number;
  options: LearnerTestOptionDto[];
}

export interface TestAttemptStartDto {
  attempt_id: number;
  attempt_no: number;
  test_id: number;
  title: string;
  course_id: number;
  course_title: string;
  question_count: number;
  started_at: string;
  questions: LearnerTestQuestionDto[];
}

export interface TestAttemptAnswerPayload {
  question_id: number;
  selected_option_id?: number | null;
}

export interface TestAttemptFinishPayload {
  answers: TestAttemptAnswerPayload[];
}

export interface AttemptResultOptionDto {
  id: number;
  text: string;
  order_index: number;
  is_selected: boolean;
  is_correct: boolean;
}

export interface AttemptResultQuestionDto {
  id: number;
  question_text: string;
  order_index: number;
  selected_option_id?: number | null;
  is_correct: boolean;
  options: AttemptResultOptionDto[];
}

export interface TestAttemptResultDto {
  attempt_id: number;
  attempt_no: number;
  test_id: number;
  title: string;
  course_id: number;
  course_title: string;
  question_count: number;
  correct_answers: number;
  score: number;
  percent: number;
  status: string;
  started_at: string;
  completed_at?: string | null;
  questions: AttemptResultQuestionDto[];
}

export async function startTestAttempt(testId: number): Promise<TestAttemptStartDto> {
  const response = await authorizedFetch(`${API_URL}/api/tests/${testId}/attempts`, {
    method: 'POST'
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export async function finishTestAttempt(
  attemptId: number,
  payload: TestAttemptFinishPayload
): Promise<TestAttemptResultDto> {
  const response = await authorizedFetch(`${API_URL}/api/attempts/${attemptId}/finish`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export async function getAttemptResult(attemptId: number): Promise<TestAttemptResultDto> {
  const response = await authorizedFetch(`${API_URL}/api/attempts/${attemptId}/result`);

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}
export interface ChatbotAskPayload {
  query: string;
}

export interface ChatbotSourceDto {
  document_id: number;
  document_title: string;
  chunk_id?: number | null;
  relevance_score?: number | null;
}

export interface ChatbotTurnDto {
  id: number;
  query_text: string;
  answer_text: string;
  created_at: string;
  sources: ChatbotSourceDto[];
}

export interface ChatbotSessionSummaryDto {
  id: number;
  created_at: string;
  last_question?: string | null;
}

export interface ChatbotSessionDto {
  id: number;
  created_at: string;
  last_question?: string | null;
  interactions: ChatbotTurnDto[];
}

export async function getChatbotSessions(): Promise<ChatbotSessionSummaryDto[]> {
  const response = await authorizedFetch(`${API_URL}/api/chatbot/sessions`);

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export async function createChatbotSession(): Promise<ChatbotSessionSummaryDto> {
  const response = await authorizedFetch(`${API_URL}/api/chatbot/sessions`, {
    method: 'POST'
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export async function getChatbotSession(sessionId: number): Promise<ChatbotSessionDto> {
  const response = await authorizedFetch(`${API_URL}/api/chatbot/sessions/${sessionId}`);

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export async function sendChatbotMessage(
  sessionId: number,
  payload: ChatbotAskPayload
): Promise<ChatbotTurnDto> {
  const response = await authorizedFetch(`${API_URL}/api/chatbot/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

