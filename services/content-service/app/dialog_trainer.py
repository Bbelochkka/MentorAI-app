from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .chatbot import _call_llm, _cleanup_answer_text
from .config import settings
from .infrastructure import get_postgres_connection
from .security import get_current_user

router = APIRouter(prefix="/api/trainer", tags=["dialog-trainer"])
logger = logging.getLogger(__name__)


class TrainerScenarioResponse(BaseModel):
    id: int
    title: str
    scenario_type: str
    funnel_stage: str
    is_full_funnel: bool
    description: str | None = None
    stage_hint: str | None = None
    final_goal: str | None = None


class TrainerClientResponse(BaseModel):
    id: int
    name: str
    position: str | None = None
    age: int | None = None
    temperament: str | None = None
    attitude: str | None = None
    communication_style: str | None = None
    buying_history: str | None = None
    decision_role: str | None = None
    tech_level: str | None = None
    persona: str | None = None
    pain_points: str | None = None
    typical_objections: str | None = None


class TrainerProductResponse(BaseModel):
    id: int
    title: str
    source_type: str
    description: str | None = None
    price: str | None = None
    target_audience: str | None = None
    key_benefits: str | None = None
    limitations: str | None = None
    typical_objections: str | None = None


class TrainerDifficultyResponse(BaseModel):
    code: str
    title: str
    description: str


class TrainerOptionsResponse(BaseModel):
    scenarios: list[TrainerScenarioResponse]
    clients: list[TrainerClientResponse]
    products: list[TrainerProductResponse]
    difficulties: list[TrainerDifficultyResponse]


class TrainerSelectedProductRequest(BaseModel):
    product_id: int | None = None
    manual_title: str | None = None
    manual_description: str | None = None


class TrainerSessionCreateRequest(BaseModel):
    scenario_id: int
    client_id: int
    difficulty: str = Field(default="medium")
    mode: str = Field(default="practice")
    products: list[TrainerSelectedProductRequest] = Field(default_factory=list)


class TrainerMessageCreateRequest(BaseModel):
    message: str


class TrainerMessageResponse(BaseModel):
    id: int
    sender_type: str
    message_text: str
    created_at: datetime


class TrainerSessionProductResponse(BaseModel):
    id: int
    product_id: int | None = None
    product_title: str
    product_context: str | None = None


class TrainerResultResponse(BaseModel):
    total_score: float
    strong_sides: str | None = None
    weak_sides: str | None = None
    recommendations: str | None = None
    created_at: datetime | None = None


class TrainerSessionSummaryResponse(BaseModel):
    id: int
    scenario_id: int
    scenario_title: str
    scenario_description: str | None = None
    funnel_stage: str
    current_stage: str
    stage_hint: str | None = None
    final_goal: str | None = None
    is_full_funnel: bool
    client_id: int
    client_name: str
    client_position: str | None = None
    client_age: int | None = None
    client_temperament: str | None = None
    client_attitude: str | None = None
    client_communication_style: str | None = None
    client_buying_history: str | None = None
    client_decision_role: str | None = None
    client_tech_level: str | None = None
    client_persona: str | None = None
    client_pain_points: str | None = None
    client_typical_objections: str | None = None
    difficulty: str
    mode: str
    status: str
    goal_reached: bool
    auto_completed: bool
    brief_start_tip: str
    started_at: datetime
    completed_at: datetime | None = None
    total_score: float | None = None
    last_message: str | None = None
    selected_products: list[TrainerSessionProductResponse] = Field(default_factory=list)


class TrainerSessionResponse(TrainerSessionSummaryResponse):
    messages: list[TrainerMessageResponse]
    result: TrainerResultResponse | None = None


_DIFFICULTIES = [
    TrainerDifficultyResponse(
        code="easy",
        title="Лёгкая",
        description="Клиент открыт к разговору, отвечает спокойно и быстрее соглашается на следующий шаг.",
    ),
    TrainerDifficultyResponse(
        code="medium",
        title="Средняя",
        description="Клиент отвечает нейтрально, задаёт уточнения, сомневается и ждёт понятной пользы.",
    ),
    TrainerDifficultyResponse(
        code="hard",
        title="Сложная",
        description="Клиент занят, сопротивляется, может отвечать резко и требует конкретные аргументы.",
    ),
]

_ALLOWED_DIFFICULTIES = {item.code for item in _DIFFICULTIES}
_ALLOWED_MODES = {"practice", "exam"}
_STAGE_ORDER = ["intro", "need_discovery", "presentation", "objection", "closing"]
_STAGE_TITLES = {
    "intro": "холодный звонок",
    "need_discovery": "выявление потребности",
    "presentation": "презентация продукта",
    "objection": "обработка возражений",
    "closing": "закрытие сделки",
    "custom": "индивидуальный этап",
}
_STAGE_START_TIPS = {
    "intro": "Начните с короткого приветствия: представьтесь, назовите компанию, объясните повод обращения и спросите, удобно ли клиенту говорить.",
    "need_discovery": "Первые этапы воронки уже прошли: контакт установлен, клиент готов продолжить разговор. Начните с открытого вопроса о текущей ситуации, потребностях и критериях выбора.",
    "presentation": "Первые этапы воронки уже прошли: контакт установлен и базовая потребность клиента известна. Начните с короткой связки: какую задачу клиента вы услышали и как выбранный продукт помогает её решить.",
    "objection": "Первые этапы воронки уже прошли: клиент знает предложение, но сомневается. Начните с признания сомнения, уточните причину возражения и только потом давайте аргумент.",
    "closing": "Первые этапы воронки уже прошли: клиент заинтересован и основные сомнения сняты. Начните с короткого итога пользы и предложите конкретный следующий шаг: заявку, КП, демо, встречу или подключение.",
    "custom": "Начните с уточнения ситуации клиента и аккуратно ведите разговор к цели, указанной в карточке сценария.",
}

_BAD_REPLY_MARKERS = (
    "как ии",
    "как ai",
    "я искусственный",
    "я не могу",
    "в рамках тренажера",
    "в рамках тренажёра",
    "оценка",
    "правильный ответ",
    "менеджеру следует",
    "виртуальный клиент",
    "сценарий",
    "stage",
    "score",
)

_PRODUCT_STOP_TITLES = {
    "описание", "цена", "стоимость", "преимущества", "ограничения", "возражения", "целевая аудитория",
    "вывод", "итог", "модуль", "тема", "введение", "заключение", "курс", "тариф", "продукт", "услуга",
}


def _decimal_to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _compact(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _normalize_key(value: str) -> str:
    return _compact(value).lower().replace("ё", "е")


def _safe_product_id(course_id: int, index: int, title: str) -> int:
    digest = int(hashlib.sha1(f"{course_id}:{index}:{title}".encode("utf-8")).hexdigest()[:6], 16)
    return -int(course_id * 1_000_000 + index * 10_000 + digest % 10_000)


def _ensure_trainer_schema() -> None:
    ddl_statements = [
        """
        CREATE TABLE IF NOT EXISTS dialog_trainer_scenarios (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT,
            title VARCHAR(255) NOT NULL,
            scenario_type VARCHAR(50) NOT NULL DEFAULT 'custom',
            funnel_stage VARCHAR(50) NOT NULL DEFAULT 'intro',
            is_full_funnel BOOLEAN NOT NULL DEFAULT FALSE,
            description TEXT,
            stage_hint TEXT,
            final_goal TEXT,
            success_markers TEXT,
            failure_markers TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'published',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_dialog_trainer_scenarios_type CHECK (scenario_type IN ('cold_call', 'objection_handling', 'closing', 'custom')),
            CONSTRAINT chk_dialog_trainer_scenarios_status CHECK (status IN ('draft', 'published', 'archived'))
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS dialog_trainer_clients (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT,
            name VARCHAR(255) NOT NULL,
            position VARCHAR(255),
            age INTEGER,
            temperament VARCHAR(150),
            attitude VARCHAR(150),
            communication_style TEXT,
            buying_history TEXT,
            decision_role TEXT,
            tech_level VARCHAR(100),
            persona TEXT,
            pain_points TEXT,
            typical_objections TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS dialog_trainer_sessions (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            scenario_id BIGINT NOT NULL REFERENCES dialog_trainer_scenarios(id),
            client_id BIGINT NOT NULL REFERENCES dialog_trainer_clients(id),
            difficulty VARCHAR(20) NOT NULL DEFAULT 'medium',
            mode VARCHAR(20) NOT NULL DEFAULT 'practice',
            current_stage VARCHAR(50) NOT NULL DEFAULT 'intro',
            final_goal TEXT,
            goal_reached BOOLEAN NOT NULL DEFAULT FALSE,
            auto_completed BOOLEAN NOT NULL DEFAULT FALSE,
            status VARCHAR(20) NOT NULL DEFAULT 'started',
            total_score NUMERIC(5,2),
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            completed_at TIMESTAMPTZ,
            CONSTRAINT chk_dialog_trainer_sessions_status CHECK (status IN ('started', 'completed', 'abandoned')),
            CONSTRAINT chk_dialog_trainer_sessions_mode CHECK (mode IN ('practice', 'exam')),
            CONSTRAINT chk_dialog_trainer_sessions_difficulty CHECK (difficulty IN ('easy', 'medium', 'hard'))
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS dialog_trainer_messages (
            id BIGSERIAL PRIMARY KEY,
            session_id BIGINT NOT NULL REFERENCES dialog_trainer_sessions(id) ON DELETE CASCADE,
            sender_type VARCHAR(20) NOT NULL,
            message_text TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_dialog_trainer_messages_sender CHECK (sender_type IN ('user', 'virtual_client', 'system'))
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS dialog_trainer_session_products (
            id BIGSERIAL PRIMARY KEY,
            session_id BIGINT NOT NULL REFERENCES dialog_trainer_sessions(id) ON DELETE CASCADE,
            product_id BIGINT,
            product_title VARCHAR(255) NOT NULL,
            product_context TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS dialog_trainer_results (
            id BIGSERIAL PRIMARY KEY,
            session_id BIGINT NOT NULL UNIQUE REFERENCES dialog_trainer_sessions(id) ON DELETE CASCADE,
            total_score NUMERIC(5,2) NOT NULL DEFAULT 0,
            strong_sides TEXT,
            weak_sides TEXT,
            recommendations TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
    ]

    alter_statements = [
        "ALTER TABLE dialog_trainer_scenarios ADD COLUMN IF NOT EXISTS funnel_stage VARCHAR(50) NOT NULL DEFAULT 'intro'",
        "ALTER TABLE dialog_trainer_scenarios ADD COLUMN IF NOT EXISTS is_full_funnel BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE dialog_trainer_scenarios ADD COLUMN IF NOT EXISTS stage_hint TEXT",
        "ALTER TABLE dialog_trainer_scenarios ADD COLUMN IF NOT EXISTS final_goal TEXT",
        "ALTER TABLE dialog_trainer_scenarios ADD COLUMN IF NOT EXISTS success_markers TEXT",
        "ALTER TABLE dialog_trainer_scenarios ADD COLUMN IF NOT EXISTS failure_markers TEXT",
        "ALTER TABLE dialog_trainer_clients ADD COLUMN IF NOT EXISTS age INTEGER",
        "ALTER TABLE dialog_trainer_clients ADD COLUMN IF NOT EXISTS temperament VARCHAR(150)",
        "ALTER TABLE dialog_trainer_clients ADD COLUMN IF NOT EXISTS attitude VARCHAR(150)",
        "ALTER TABLE dialog_trainer_clients ADD COLUMN IF NOT EXISTS communication_style TEXT",
        "ALTER TABLE dialog_trainer_clients ADD COLUMN IF NOT EXISTS buying_history TEXT",
        "ALTER TABLE dialog_trainer_clients ADD COLUMN IF NOT EXISTS decision_role TEXT",
        "ALTER TABLE dialog_trainer_clients ADD COLUMN IF NOT EXISTS tech_level VARCHAR(100)",
        "ALTER TABLE dialog_trainer_clients ADD COLUMN IF NOT EXISTS typical_objections TEXT",
        "ALTER TABLE dialog_trainer_sessions ADD COLUMN IF NOT EXISTS final_goal TEXT",
        "ALTER TABLE dialog_trainer_sessions ADD COLUMN IF NOT EXISTS goal_reached BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE dialog_trainer_sessions ADD COLUMN IF NOT EXISTS auto_completed BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE dialog_trainer_sessions ADD COLUMN IF NOT EXISTS current_stage VARCHAR(50) NOT NULL DEFAULT 'intro'",
        "ALTER TABLE dialog_trainer_sessions ADD COLUMN IF NOT EXISTS total_score NUMERIC(5,2)",
    ]

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            for statement in ddl_statements:
                cur.execute(statement)
            for statement in alter_statements:
                cur.execute(statement)
            _seed_base_data(cur)
        conn.commit()


def _seed_base_data(cur: Any) -> None:
    cur.execute(
        """
        INSERT INTO dialog_trainer_scenarios (
            id, company_id, title, scenario_type, funnel_stage, is_full_funnel,
            description, stage_hint, final_goal, success_markers, failure_markers, status
        )
        VALUES
        (1, NULL, 'Полная воронка продаж', 'custom', 'intro', TRUE,
         'Полная тренировка от первого контакта до договорённости о следующем шаге.',
         'Тренировка проходит через все этапы: холодный звонок, выявление потребности, презентация, обработка возражений и закрытие.',
         'Клиент согласился на конкретный следующий шаг: заявку, подключение, КП, демо, встречу или повторный контакт.',
         'задавайте; мне важно; звучит интересно; логично; пришлите КП; давайте подключим; согласен на демо; давайте заявку',
         'мне неинтересно; не звоните; до свидания; я подумаю', 'published'),
        (2, NULL, 'Холодный звонок', 'cold_call', 'intro', FALSE,
         'Первый контакт с потенциальным клиентом.',
         'Менеджер должен представиться, назвать компанию, объяснить повод обращения и получить разрешение продолжить разговор.',
         'Клиент согласился продолжить разговор или ответить на 1–2 уточняющих вопроса.',
         'можно, слушаю; задавайте вопрос; давайте коротко; спрашивайте; готов выслушать; один-два вопроса',
         'мне неинтересно; не звоните; до свидания; нет времени; уберите мой номер', 'published'),
        (3, NULL, 'Выявление потребности', 'custom', 'need_discovery', FALSE,
         'Этап уточнения задачи клиента.',
         'Менеджер задаёт открытые вопросы, чтобы понять боль клиента, текущую ситуацию и критерии выбора.',
         'Клиент сформулировал проблему, потребность или критерии выбора.',
         'мне важно; проблема в том что; хочу чтобы; нужно решить; неудобно что; не хватает; меня волнует',
         'вы ничего не спросили; вы не поняли; мне это не подходит', 'published'),
        (4, NULL, 'Презентация продукта', 'custom', 'presentation', FALSE,
         'Этап объяснения ценности продукта.',
         'Менеджер связывает продукт с потребностью клиента и объясняет пользу без перегруза деталями.',
         'Клиент понял ценность предложения и готов обсуждать условия или следующий шаг.',
         'звучит интересно; понимаю пользу; подходит; можно обсудить; расскажите условия; это решает',
         'слишком общо; звучит как реклама; не понял пользу; мне это не нужно', 'published'),
        (5, NULL, 'Обработка возражений', 'objection_handling', 'objection', FALSE,
         'Этап обработки сомнений клиента.',
         'Менеджер признаёт сомнение, уточняет причину и даёт аргумент без спора и давления.',
         'Клиент принял аргумент или согласился продолжить обсуждение.',
         'логично; можно сравнить; давайте посмотрим; звучит разумно; готов обсудить; тогда понятно',
         'вы меня не убедили; вы спорите; это всё равно дорого; я не доверяю', 'published'),
        (6, NULL, 'Закрытие сделки', 'closing', 'closing', FALSE,
         'Финальный этап перевода клиента к конкретному действию.',
         'Менеджер подводит итог, предлагает конкретный следующий шаг и согласует время или действие.',
         'Клиент согласился на заявку, подключение, демо, КП, встречу или повторный контакт.',
         'оформляйте; давайте подключим; пришлите КП; согласен на демо; завтра удобно; давайте заявку; назначим встречу; готов попробовать',
         'я подумаю; потом решим; когда-нибудь; если что обращусь', 'published')
        ON CONFLICT (id) DO UPDATE
        SET title = EXCLUDED.title,
            scenario_type = EXCLUDED.scenario_type,
            funnel_stage = EXCLUDED.funnel_stage,
            is_full_funnel = EXCLUDED.is_full_funnel,
            description = EXCLUDED.description,
            stage_hint = EXCLUDED.stage_hint,
            final_goal = EXCLUDED.final_goal,
            success_markers = EXCLUDED.success_markers,
            failure_markers = EXCLUDED.failure_markers,
            status = EXCLUDED.status
        """
    )

    cur.execute(
        """
        INSERT INTO dialog_trainer_clients (
            id, company_id, name, position, age, temperament, attitude, communication_style,
            buying_history, decision_role, tech_level, persona, pain_points, typical_objections
        )
        VALUES
        (1, NULL, 'Евгений', 'Руководитель отдела продаж', 38,
         'рациональный, быстрый, требовательный',
         'занят, готов слушать только конкретику',
         'отвечает коротко, перебивает длинные презентации, просит цифры и сроки',
         'Нет',
         'лицо, влияющее на решение', 'высокий',
         'Евгений — деловой и занятый клиент. Если менеджер говорит общо, он быстро теряет интерес. Если слышит конкретику и выгоду, соглашается на следующий шаг.',
         'Хочет контролировать расходы команды, быстро подключать сотрудников и видеть прозрачную детализацию.',
         'нет времени; у нас уже есть оператор; покажите выгоду в цифрах; не хочу менять процессы'),
        (2, NULL, 'Ольга', 'Частный клиент, мама двоих детей', 42,
         'доброжелательная, осторожная',
         'открыта к разговору, но боится сложных условий',
         'задаёт бытовые вопросы, просит объяснять простыми словами',
         'Да',
         'самостоятельно принимает решение', 'средний',
         'Ольга вежлива и готова слушать, если менеджер не давит и объясняет человеческим языком.',
         'Хочет контролировать расходы детей и не получать неожиданные списания.',
         'сложно переносить номера; дети не разберутся; боюсь скрытых платежей'),
        (3, NULL, 'Игорь', 'Коммерческий директор', 45,
         'скептичный, жёсткий, аналитичный',
         'сомневается и проверяет каждое обещание',
         'может грубить, если слышит рекламные фразы; уважает точные аргументы',
         'Нет',
         'ключевое лицо, принимающее решение', 'высокий',
         'Игорь не любит мягкие обещания. Ему нужны риски, экономика, пилот и понятный контроль результата.',
         'Нужны экономия бюджета, контроль корпоративных номеров и отсутствие хаоса при подключении сотрудников.',
         'дорого; уже есть оператор; не верю обещаниям; нужен пилот, а не полный переход'),
        (4, NULL, 'Николай Петрович', 'Пенсионер', 68,
         'спокойный, осторожный, медленный в принятии решения',
         'вежливый, но плохо воспринимает технические термины',
         'часто просит повторить, не любит англицизмы и сложные тарифные формулировки',
         'Да',
         'самостоятельно принимает решение, но может советоваться с семьёй', 'низкий',
         'Николай Петрович не грубит, но легко теряется, если менеджер говорит быстро или технически сложно.',
         'Хочет простой тариф без скрытых списаний и непонятных услуг.',
         'я не понимаю гигабайты; мне бы без лишнего; не хочу, чтобы списывали деньги')
        ON CONFLICT (id) DO UPDATE
        SET name = EXCLUDED.name,
            position = EXCLUDED.position,
            age = EXCLUDED.age,
            temperament = EXCLUDED.temperament,
            attitude = EXCLUDED.attitude,
            communication_style = EXCLUDED.communication_style,
            buying_history = EXCLUDED.buying_history,
            decision_role = EXCLUDED.decision_role,
            tech_level = EXCLUDED.tech_level,
            persona = EXCLUDED.persona,
            pain_points = EXCLUDED.pain_points,
            typical_objections = EXCLUDED.typical_objections
        """
    )


def _scenario_from_row(row: tuple[Any, ...]) -> TrainerScenarioResponse:
    return TrainerScenarioResponse(
        id=row[0],
        title=row[1],
        scenario_type=row[2],
        funnel_stage=row[3],
        is_full_funnel=bool(row[4]),
        description=row[5],
        stage_hint=row[6],
        final_goal=row[7],
    )


def _client_from_row(row: tuple[Any, ...]) -> TrainerClientResponse:
    return TrainerClientResponse(
        id=row[0],
        name=row[1],
        position=row[2],
        age=row[3],
        temperament=row[4],
        attitude=row[5],
        communication_style=row[6],
        buying_history=row[7],
        decision_role=row[8],
        tech_level=row[9],
        persona=row[10],
        pain_points=row[11],
        typical_objections=row[12],
    )


def _stage_start_tip(stage: str, is_full_funnel: bool) -> str:
    if is_full_funnel and stage == "intro":
        return "Вы выбрали полную воронку. Начните с установления контакта: представьтесь, назовите компанию, объясните повод обращения и получите разрешение продолжить разговор. После достижения цели каждого этапа тренажёр сам переведёт вас дальше."
    return _STAGE_START_TIPS.get(stage, _STAGE_START_TIPS["custom"])


def _stage_goal_text(stage: str) -> str:
    goals = {
        "intro": "Клиент согласился продолжить разговор или ответить на 1–2 уточняющих вопроса.",
        "need_discovery": "Клиент сформулировал проблему, потребность или критерии выбора.",
        "presentation": "Клиент понял ценность предложения и готов обсуждать условия или следующий шаг.",
        "objection": "Клиент принял аргумент или согласился продолжить обсуждение.",
        "closing": "Клиент согласился на заявку, подключение, демо, КП, встречу или повторный контакт.",
    }
    return goals.get(stage, "Клиент согласился на целевое действие по выбранному этапу.")


def _next_stage(stage: str) -> str | None:
    try:
        index = _STAGE_ORDER.index(stage)
    except ValueError:
        return None
    if index >= len(_STAGE_ORDER) - 1:
        return None
    return _STAGE_ORDER[index + 1]


def _load_course_texts(company_id: int) -> list[dict[str, Any]]:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, c.title, COALESCE(c.description, '')
                FROM courses c
                JOIN course_versions cv
                  ON cv.course_id = c.id
                 AND cv.version_number = c.current_version_no
                WHERE c.company_id = %s
                  AND cv.status = 'published'
                ORDER BY c.id DESC
                LIMIT 50
                """,
                (company_id,),
            )
            course_rows = cur.fetchall()

            result: list[dict[str, Any]] = []
            for course_id, course_title, course_description in course_rows:
                cur.execute(
                    """
                    SELECT cm.title, ct.title, COALESCE(ct.content, '')
                    FROM course_versions cv
                    JOIN course_modules cm ON cm.course_version_id = cv.id
                    JOIN course_topics ct ON ct.module_id = cm.id
                    WHERE cv.course_id = %s
                      AND cv.version_number = (
                          SELECT current_version_no FROM courses WHERE id = %s
                      )
                    ORDER BY cm.sort_order, ct.sort_order
                    """,
                    (course_id, course_id),
                )
                topic_rows = cur.fetchall()
                blocks = [f"Курс: {course_title}", course_description or ""]
                for module_title, topic_title, content in topic_rows:
                    blocks.append(f"Модуль: {module_title}\nТема: {topic_title}\n{content}")
                result.append({"id": course_id, "title": course_title, "text": "\n\n".join(blocks)})
    return result




def _load_processed_document_texts(company_id: int) -> list[dict[str, Any]]:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, raw_text
                FROM documents
                WHERE company_id = %s
                  AND status = 'processed'
                  AND COALESCE(raw_text, '') <> ''
                ORDER BY created_at DESC
                LIMIT 30
                """,
                (company_id,),
            )
            rows = cur.fetchall()
    return [{"id": row[0], "title": row[1], "text": row[2] or ""} for row in rows]


def _context_tokens(text: str) -> set[str]:
    tokens = re.findall(r"[A-Za-zА-Яа-яЁё0-9]{3,}", (text or "").lower().replace("ё", "е"))
    stop_words = {
        "это", "как", "что", "для", "или", "при", "без", "над", "под", "про", "вам", "нас", "они",
        "если", "есть", "уже", "будет", "можно", "нужно", "клиент", "менеджер", "продукт", "услуга",
    }
    return {token for token in tokens if token not in stop_words}


def _score_context_block(query: str, text: str) -> float:
    query_tokens = _context_tokens(query)
    text_tokens = _context_tokens(text)
    if not query_tokens or not text_tokens:
        return 0.0
    score = len(query_tokens & text_tokens) * 4.0
    query_clean = _normalize_key(query)
    text_clean = _normalize_key(text)
    if query_clean and query_clean in text_clean:
        score += 20.0
    return score


def _load_company_knowledge_context(company_id: int, query: str, *, max_chars: int = 6500) -> str:
    blocks: list[dict[str, Any]] = []
    for course in _load_course_texts(company_id):
        text = _compact(course.get("text") or "")
        if text:
            blocks.append({"title": f"Курс: {course.get('title')}", "text": text[:5000], "score": _score_context_block(query, text)})
    for document in _load_processed_document_texts(company_id):
        text = _compact(document.get("text") or "")
        if text:
            blocks.append({"title": f"Документ: {document.get('title')}", "text": text[:5000], "score": _score_context_block(query, text)})

    if not blocks:
        return "Корпоративные материалы пока не найдены. Клиент может попросить менеджера уточнить продукт, цену и условия."

    blocks.sort(key=lambda item: item["score"], reverse=True)
    rendered: list[str] = []
    used = 0
    for block in blocks[:5]:
        piece = f"[{block['title']}]\n{block['text']}"
        if used + len(piece) > max_chars:
            piece = piece[: max(0, max_chars - used)]
        if piece.strip():
            rendered.append(piece.strip())
            used += len(piece)
        if used >= max_chars:
            break
    return "\n\n".join(rendered)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    cleaned = text.strip()
    fence = chr(96) * 3
    cleaned = cleaned.replace(fence + "json", "").replace(fence, "").strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _looks_like_product_title(title: str) -> bool:
    value = _compact(title).strip(" .,:;—-–|#*")
    if len(value) < 3 or len(value) > 70:
        return False
    low = _normalize_key(value)
    if low in _PRODUCT_STOP_TITLES:
        return False
    if low.startswith(("модуль", "тема", "глава", "раздел", "курс")):
        return False
    if len(value.split()) > 7:
        return False
    return bool(re.search(r"[A-Za-zА-Яа-яЁё]", value))


def _extract_price(context: str) -> str | None:
    patterns = [
        r"(?:от\s+)?\d[\d\s]{1,8}\s*(?:₽|руб\.?|рублей)\s*(?:/\s*(?:мес|месяц|номер|sim))?",
        r"\d+[,.]?\d*\s*(?:тыс\.?\s*)?руб",
    ]
    for pattern in patterns:
        match = re.search(pattern, context, flags=re.IGNORECASE)
        if match:
            return _compact(match.group(0))
    return None


def _context_around(text: str, start: int, end: int, radius: int = 900) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return _compact(text[left:right])[:1800]


def _description_from_context(title: str, context: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", _compact(context))
    for sentence in sentences:
        if title.lower() in sentence.lower() and len(sentence) <= 260:
            return sentence
    for sentence in sentences:
        if 30 <= len(sentence) <= 220:
            return sentence
    return _compact(context)[:220]


def _extract_products_from_course(course: dict[str, Any]) -> list[TrainerProductResponse]:
    text = course["text"] or ""
    candidates: dict[str, dict[str, Any]] = {}

    patterns = [
        r"(?:тариф|услуга|продукт|решение|опция|пакет)\s+[«\"“]([^»\"”]{2,70})[»\"”]",
        r"[«\"“]([^»\"”]{2,70})[»\"”]\s*(?:—|-|–|:)\s*(?:тариф|услуга|продукт|решение|опция|пакет)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            title = _compact(match.group(1))
            if not _looks_like_product_title(title):
                continue
            key = _normalize_key(title)
            candidates.setdefault(key, {"title": title, "start": match.start(), "end": match.end()})

    for raw_line in text.splitlines():
        line = raw_line.strip().strip("* ")
        if not line or len(line) > 240:
            continue
        if line.count("|") >= 2:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if cells and _looks_like_product_title(cells[0]) and _normalize_key(cells[0]) not in {"название", "тариф", "продукт"}:
                title = cells[0]
                pos = text.find(raw_line)
                candidates.setdefault(_normalize_key(title), {"title": title, "start": max(pos, 0), "end": max(pos, 0) + len(raw_line)})
            continue
        match = re.match(r"^(?:[-•]\s*)?([A-ZА-ЯЁ][A-Za-zА-Яа-яЁё0-9 +\-]{2,60})\s*(?:—|–|-|:)\s*(.{10,})$", line)
        if match:
            title = _compact(match.group(1))
            tail = _compact(match.group(2))
            if _looks_like_product_title(title) and any(word in tail.lower() for word in ("тариф", "услуг", "руб", "₽", "клиент", "пакет", "связ", "интернет", "подключ")):
                pos = text.find(raw_line)
                candidates.setdefault(_normalize_key(title), {"title": title, "start": max(pos, 0), "end": max(pos, 0) + len(raw_line)})

    products: list[TrainerProductResponse] = []
    for index, item in enumerate(candidates.values(), start=1):
        title = item["title"]
        context = _context_around(text, item["start"], item["end"])
        description = _description_from_context(title, context)
        price = _extract_price(context)
        products.append(
            TrainerProductResponse(
                id=_safe_product_id(course["id"], index, title),
                title=title,
                source_type="course",
                description=description,
                price=price,
                target_audience=None,
                key_benefits=context,
                limitations=None,
                typical_objections=None,
            )
        )
        if len(products) >= 12:
            break
    return products


def _load_course_products(company_id: int) -> list[TrainerProductResponse]:
    products: list[TrainerProductResponse] = []
    seen: set[str] = set()
    for course in _load_course_texts(company_id):
        for product in _extract_products_from_course(course):
            key = _normalize_key(product.title)
            if key in seen:
                continue
            seen.add(key)
            products.append(product)
    return products[:30]


def _build_manual_product_context(title: str, description: str | None) -> str:
    text = _compact(description)
    return f"Название: {title}" + (f"\nОписание: {text}" if text else "")


def _build_product_context(product: TrainerProductResponse) -> str:
    parts = [f"Название: {product.title}"]
    if product.description:
        parts.append(f"Описание: {product.description}")
    if product.price:
        parts.append(f"Цена: {product.price}")
    if product.target_audience:
        parts.append(f"ЦА: {product.target_audience}")
    if product.key_benefits:
        parts.append(f"Материал из курса: {product.key_benefits}")
    if product.limitations:
        parts.append(f"Ограничения: {product.limitations}")
    if product.typical_objections:
        parts.append(f"Типовые возражения: {product.typical_objections}")
    return "\n".join(parts)


def _render_history(messages: list[TrainerMessageResponse]) -> str:
    rendered = []
    for message in messages[-12:]:
        if message.sender_type == "user":
            role = "Менеджер"
        elif message.sender_type == "virtual_client":
            role = "Клиент"
        else:
            continue
        rendered.append(f"{role}: {message.message_text}")
    return "\n".join(rendered) or "Диалог только начался."


def _clean_multiline_feedback(value: Any) -> str:
    """Очищает текст оценки, но сохраняет переносы строк для карточек результата."""
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Если модель вернула пункты через точку с запятой, аккуратно превращаем их в строки.
    if "\n" not in text and ";" in text:
        text = re.sub(r"\s*;\s*", "\n", text)

    lines: list[str] = []
    for raw_line in text.split("\n"):
        line = re.sub(r"\s+", " ", raw_line).strip()
        line = re.sub(r"^[-•*\d.)\s]+", "", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def _looks_not_russian(value: str) -> bool:
    """Отсекает ответы оценки на английском: пользователю нужны русские рекомендации."""
    cyrillic = len(re.findall(r"[А-Яа-яЁё]", value or ""))
    latin = len(re.findall(r"[A-Za-z]", value or ""))
    return latin > 24 and latin > cyrillic


def _clean_client_reply(text: str) -> str:
    cleaned = _cleanup_answer_text(text or "")
    cleaned = re.sub(r"^(Клиент|Виртуальный клиент|Ответ клиента)\s*[:—-]\s*", "", cleaned, flags=re.IGNORECASE).strip()
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    cleaned = " ".join(lines[:2]).strip()
    if not cleaned:
        return ""
    if len(cleaned) > 420:
        cleaned = cleaned[:420].rsplit(" ", 1)[0].strip() + "..."
    lowered = cleaned.lower()
    if any(marker in lowered for marker in _BAD_REPLY_MARKERS):
        return ""
    return cleaned


def _generate_client_reply(session: dict[str, Any], messages: list[TrainerMessageResponse], user_message: str, company_id: int) -> str:
    """Генерирует реплику виртуального клиента только через текущий LLM-провайдер.

    Здесь специально нет заранее прописанных fallback-реплик. Если LLM
    недоступен или вернул некорректный ответ, backend отдаёт понятную ошибку 502.
    Так проще отлаживать интеграцию и не получать «фальшивый» диалог из шаблонов.
    """
    knowledge_context = _load_company_knowledge_context(
        company_id,
        f"{session.get('scenario_title')} {session.get('current_stage')} {session.get('client_pain_points')} {user_message}",
        max_chars=2600,
    )
    previous_client_replies = [m.message_text for m in messages if m.sender_type == "virtual_client"][-8:]

    difficulty_rules = {
        "easy": "Клиент доброжелательный: он открыт к разговору, задаёт уточняющие вопросы и соглашается, если менеджер говорит понятно.",
        "medium": "Клиент нейтральный: он сомневается, уточняет условия и ждёт конкретной пользы перед согласием.",
        "hard": "Клиент сложный: он занят, может отвечать резко, не любит общие фразы и требует конкретику, цифры и понятный следующий шаг.",
    }

    system_prompt = """
Ты играешь роль клиента в учебном диалоговом тренажёре продаж MentorAI.

Правила роли:
- ты НЕ ассистент, НЕ преподаватель и НЕ оценщик;
- ты НЕ объясняешь правила тренажёра;
- ты НЕ даёшь советов менеджеру;
- ты отвечаешь только как реальный клиент в разговоре с менеджером;
- пиши от первого лица, живым русским языком;
- ответ должен быть коротким: 1–2 предложения;
- не используй списки, заголовки, markdown и фразу «Клиент:»;
- всегда реагируй на последнюю реплику менеджера и историю диалога;
- не повторяй дословно прошлые реплики клиента.

Логика поведения:
- если менеджер говорит слишком общо, давит, ошибается в условиях или не задаёт нужные вопросы — выражай сомнение, задавай уточнение или сопротивляйся;
- если менеджер хорошо ведёт этап воронки, уточняет потребность, связывает пользу с проблемой клиента и предлагает конкретный следующий шаг — становись более открытым;
- если финальная цель этапа действительно достигнута, можешь согласиться на следующий шаг;
- не соглашайся на цель слишком рано, если менеджер не подвёл к ней разговор.
""".strip()

    prompt = f"""
Контекст тренировки:
Сценарий: {session.get('scenario_title')}
Текущий этап воронки: {_STAGE_TITLES.get(session.get('current_stage'), session.get('current_stage'))}
Цель текущего этапа: {session.get('stage_final_goal') or session.get('final_goal')}
Полная воронка: {'да' if session.get('is_full_funnel') else 'нет'}
Сложность: {session.get('difficulty')} — {difficulty_rules.get(session.get('difficulty'), '')}

Профиль клиента:
Имя: {session.get('client_name')}
Возраст: {session.get('client_age') or 'не указан'}
Роль/должность: {session.get('client_position') or 'не указана'}
Темперамент: {session.get('client_temperament') or 'нейтральный'}
Настрой: {session.get('client_attitude') or 'нейтральный'}
Стиль общения: {session.get('client_communication_style') or session.get('client_persona') or 'обычный'}
Пользуется услугами компании: {session.get('client_buying_history') or 'Нет'}
Роль в принятии решения: {session.get('client_decision_role') or 'не указана'}
Уровень технической грамотности: {session.get('client_tech_level') or 'средний'}
Боли клиента: {session.get('client_pain_points') or 'нет данных'}
Типичные возражения: {session.get('client_typical_objections') or 'нет данных'}

Корпоративные материалы о компании, товарах, услугах, тарифах, условиях и аргументации:
{knowledge_context}

История диалога:
{_render_history(messages)}

Прошлые реплики клиента, которые нельзя повторять дословно:
{'; '.join(previous_client_replies) or 'нет'}

Последняя реплика менеджера:
{user_message}

Сгенерируй следующую реплику клиента. Ответь только репликой клиента без кавычек и без пояснений.
""".strip()

    try:
        raw_reply = _call_llm(prompt, system_prompt=system_prompt, max_tokens=180)
        reply = _clean_client_reply(raw_reply)

        if not reply:
            raise ValueError(f"LLM-провайдер {settings.llm_provider} вернул пустую или служебную реплику: {raw_reply!r}")

        normalized_reply = _normalize_key(reply)
        previous_normalized = {_normalize_key(item) for item in previous_client_replies}

        if normalized_reply in previous_normalized:
            retry_prompt = prompt + """

Ты повторил прошлую реплику клиента. Переформулируй ответ полностью иначе, но сохрани тот же характер клиента и реакцию на последнюю реплику менеджера.
Ответь только новой репликой клиента.
""".strip()
            raw_retry = _call_llm(retry_prompt, system_prompt=system_prompt, max_tokens=180)
            retry_reply = _clean_client_reply(raw_retry)
            if not retry_reply or _normalize_key(retry_reply) in previous_normalized:
                raise ValueError(f"LLM-провайдер {settings.llm_provider} повторяет прошлые реплики: {raw_retry!r}")
            return retry_reply

        return reply

    except HTTPException:
        logger.exception("LLM не смогла сгенерировать реплику виртуального клиента; provider=%s", settings.llm_provider)
        raise
    except Exception as exc:
        logger.exception("Ошибка генерации реплики виртуального клиента через LLM; provider=%s", settings.llm_provider)
        raise HTTPException(
            status_code=502,
            detail=(
                f"LLM-провайдер {settings.llm_provider} не смог сгенерировать реплику виртуального клиента. "
                "Проверь LLM_PROVIDER, LLM_BASE_URL, LLM_MODEL и доступность модели."
            ),
        ) from exc

def _has_any_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _manager_action_matches_stage(stage: str, user_message: str, user_turns: int) -> bool:
    lower = re.sub(r"\s+", " ", (user_message or "").lower().replace("ё", "е")).strip()
    if not lower:
        return False

    if stage == "intro":
        has_greeting = _has_any_phrase(
            lower,
            ("здрав", "добрый", "меня зовут", "я из", "компан", "обращаюсь"),
        )
        has_permission_or_reason = _has_any_phrase(
            lower,
            ("удобно", "минут", "пару слов", "коротко", "рассказать", "звоню", "хотел бы", "могу"),
        )
        return has_greeting and has_permission_or_reason and len(lower) >= 20

    if stage == "need_discovery":
        return user_turns >= 1 and (
            "?" in user_message
            or _has_any_phrase(
                lower,
                (
                    "что важно",
                    "что для вас важно",
                    "какие задачи",
                    "какие сложности",
                    "с чем работаете",
                    "как сейчас",
                    "чем пользуетесь",
                    "что не устраивает",
                    "какая цель",
                ),
            )
        )

    if stage == "presentation":
        return user_turns >= 1 and _has_any_phrase(
            lower,
            (
                "поможет",
                "решит",
                "позволит",
                "сможете",
                "вы получите",
                "подойдет",
                "польз",
                "эконом",
                "контрол",
                "сниз",
                "ускор",
                "прозрач",
            ),
        )

    if stage == "objection":
        return user_turns >= 1 and _has_any_phrase(
            lower,
            (
                "понимаю",
                "соглас",
                "это нормально",
                "давайте",
                "сравним",
                "пилот",
                "без риска",
                "покажу",
                "объясню",
                "уточню",
            ),
        )

    if stage == "closing":
        return user_turns >= 1 and _has_any_phrase(
            lower,
            (
                "оформ",
                "подключ",
                "демо",
                "кп",
                "коммерческ",
                "встреч",
                "созвон",
                "заяв",
                "договор",
                "запланир",
                "назнач",
                "следующий шаг",
                "когда удобно",
            ),
        )

    return user_turns >= 2


def _stage_success_markers(stage: str) -> list[str]:
    markers = {
        "intro": [
            "задавайте",
            "спрашивайте",
            "слушаю",
            "говорите",
            "давайте коротко",
            "один-два вопроса",
            "есть пара минут",
            "могу говорить",
            "готов выслушать",
            "можете задать",
            "можно пару вопросов",
        ],
        "need_discovery": [
            "мне важно",
            "проблема",
            "хочу чтобы",
            "нужно",
            "не хватает",
            "неудобно",
            "меня волнует",
            "для меня важно",
            "сейчас у нас",
            "нам нужно",
        ],
        "presentation": [
            "звучит интересно",
            "подходит",
            "понимаю пользу",
            "можно обсудить",
            "это решит",
            "полезно",
            "интересно",
            "понятно",
            "вижу смысл",
        ],
        "objection": [
            "логично",
            "давайте посмотрим",
            "можно сравнить",
            "звучит разумно",
            "готов обсудить",
            "тогда понятно",
            "хорошо",
            "ладно",
            "убедили",
        ],
        "closing": [
            "оформляйте",
            "давайте подключим",
            "пришлите кп",
            "пришлите предложение",
            "согласен на демо",
            "давайте демо",
            "завтра удобно",
            "давайте заявку",
            "готов попробовать",
            "назначим встречу",
            "можно созвон",
            "давайте созвонимся",
        ],
    }
    return markers.get(stage, [])


def _goal_is_reached(session: dict[str, Any], client_reply: str, user_message: str, user_turns: int) -> bool:
    stage = session.get("current_stage") or "custom"
    if not _manager_action_matches_stage(stage, user_message, user_turns):
        return False
    combined = f"{client_reply} {user_message}".lower().replace("ё", "е")
    markers = _stage_success_markers(stage)
    raw_markers = session.get("success_markers") or ""
    markers.extend([m.strip().lower().replace("ё", "е") for m in re.split(r"[;\n]+", raw_markers) if m.strip()])
    return any(marker in combined for marker in markers)


def _score_dialog(
    session: dict[str, Any],
    messages: list[TrainerMessageResponse],
    goal_reached: bool,
    manual_finish: bool,
    company_id: int,
) -> tuple[float, str, str, str]:
    """Формирует итоговую аналитику только через текущий LLM-провайдер."""
    rendered_dialog = _render_history(messages)
    knowledge_context = _load_company_knowledge_context(
        company_id,
        f"{session.get('scenario_title')} {session.get('current_stage')} {session.get('client_pain_points')} {rendered_dialog}",
        max_chars=3200,
    )

    system_prompt = """
Ты эксперт по обучению менеджеров по продажам и наставник для стажёров.
Оцени только предоставленный тренировочный диалог.
Учитывай этап воронки, финальную цель, характер клиента, знание продукта, вопросы менеджера, аргументацию и следующий шаг.
Все значения внутри JSON пиши только на русском языке.
Ответ верни строго в формате JSON без markdown, без ``` и без пояснений вокруг JSON.
""".strip()

    prompt = f"""
Сценарий: {session.get('scenario_title')}
Текущий/финальный этап: {_STAGE_TITLES.get(session.get('current_stage'), session.get('current_stage'))}
Финальная цель: {session.get('stage_final_goal') or session.get('final_goal')}
Цель достигнута автоматически: {'да' if goal_reached else 'нет'}
Завершено вручную: {'да' if manual_finish else 'нет'}
Сложность: {session.get('difficulty')}
Клиент: {session.get('client_name')}, {session.get('client_position') or 'роль не указана'}
Характер клиента: {session.get('client_persona') or ''} {session.get('client_attitude') or ''} {session.get('client_communication_style') or ''}
Пользуется услугами компании: {session.get('client_buying_history') or 'Нет'}
Боли клиента: {session.get('client_pain_points') or 'нет данных'}

Корпоративные материалы:
{knowledge_context}

Диалог:
{rendered_dialog}

Верни JSON строго такого вида:
{{
  "total_score": 0,
  "strong_sides": "2-3 конкретных пункта на русском через \\n: что менеджер сделал хорошо именно в этом диалоге",
  "weak_sides": "2-3 конкретных пункта на русском через \\n: что было неверно или слабо именно в этом диалоге",
  "recommendations": "4-5 практических рекомендаций на русском через \\n: что конкретно улучшить в следующей попытке"
}}

Требования к оценке:
- total_score должен быть числом от 0 до 100;
- если диалог завершён вручную и цель не достигнута, не ставь высокий балл;
- не пиши общие фразы, привязывай выводы к конкретным репликам менеджера;
- сильные стороны, зоны роста и рекомендации пиши только на русском языке;
- рекомендации должны быть содержательными, но компактными: в каждом пункте укажи, что именно сказать/спросить, зачем это нужно и как это поможет довести клиента до цели;
- в рекомендациях учитывай профиль оппонента: темперамент, стиль общения, пользуется ли он услугами компании, роль в принятии решения, боли и типичные возражения;
- если менеджер ошибся в цене, условиях или слишком быстро давил на клиента, обязательно отметь это в weak_sides;
- если менеджер задавал хорошие вопросы или корректно обработал сомнение, отметь это в strong_sides.
""".strip()

    def _parse_score_payload(raw_text: str) -> tuple[float, str, str, str] | None:
        data = _extract_json_object(raw_text)
        if not data:
            return None
        try:
            score = float(data.get("total_score", 0))
        except Exception:
            return None
        score = max(0.0, min(100.0, round(score, 2)))
        strong = _clean_multiline_feedback(data.get("strong_sides"))
        weak = _clean_multiline_feedback(data.get("weak_sides"))
        recommendations = _clean_multiline_feedback(data.get("recommendations"))
        if not strong or not weak or not recommendations:
            return None
        if _looks_not_russian(f"{strong}\n{weak}\n{recommendations}"):
            return None
        return score, strong, weak, recommendations

    try:
        raw = _call_llm(prompt, system_prompt=system_prompt, max_tokens=1100)
        parsed = _parse_score_payload(raw)
        if parsed:
            return parsed

        retry_prompt = prompt + f"""

Предыдущий ответ был в неправильном формате:
{raw}

Исправь ответ. Верни только валидный JSON указанной структуры. Все текстовые значения должны быть на русском языке.
""".strip()
        raw_retry = _call_llm(retry_prompt, system_prompt=system_prompt, max_tokens=1100)
        parsed_retry = _parse_score_payload(raw_retry)
        if parsed_retry:
            return parsed_retry

        raise ValueError(f"LLM-провайдер {settings.llm_provider} вернул аналитику в неправильном формате: {raw_retry!r}")

    except HTTPException:
        logger.exception("LLM не смогла сформировать аналитику диалога; provider=%s", settings.llm_provider)
        raise
    except Exception as exc:
        logger.exception("Ошибка генерации итоговой аналитики через LLM; provider=%s", settings.llm_provider)
        raise HTTPException(
            status_code=502,
            detail=(
                f"LLM-провайдер {settings.llm_provider} не смог сформировать итоговую аналитику диалога. "
                "Проверь LLM_PROVIDER, LLM_BASE_URL, LLM_MODEL и доступность модели."
            ),
        ) from exc

def _load_messages(session_id: int) -> list[TrainerMessageResponse]:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, sender_type, message_text, created_at
                FROM dialog_trainer_messages
                WHERE session_id = %s
                ORDER BY created_at ASC, id ASC
                """,
                (session_id,),
            )
            rows = cur.fetchall()
    return [TrainerMessageResponse(id=row[0], sender_type=row[1], message_text=row[2], created_at=row[3]) for row in rows]


def _load_products_for_session(session_id: int) -> list[TrainerSessionProductResponse]:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, product_id, product_title, product_context
                FROM dialog_trainer_session_products
                WHERE session_id = %s
                ORDER BY id
                """,
                (session_id,),
            )
            rows = cur.fetchall()
    return [TrainerSessionProductResponse(id=row[0], product_id=row[1], product_title=row[2], product_context=row[3]) for row in rows]


def _load_result(session_id: int) -> TrainerResultResponse | None:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT total_score, strong_sides, weak_sides, recommendations, created_at
                FROM dialog_trainer_results
                WHERE session_id = %s
                """,
                (session_id,),
            )
            row = cur.fetchone()
    if not row:
        return None
    return TrainerResultResponse(
        total_score=float(row[0]),
        strong_sides=row[1],
        weak_sides=row[2],
        recommendations=row[3],
        created_at=row[4],
    )


def _session_row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "scenario_id": row[1],
        "scenario_title": row[2],
        "scenario_type": row[3],
        "scenario_description": row[4],
        "funnel_stage": row[5],
        "is_full_funnel": bool(row[6]),
        "stage_hint": row[7],
        "scenario_final_goal": row[8],
        "success_markers": row[9],
        "failure_markers": row[10],
        "client_id": row[11],
        "client_name": row[12],
        "client_position": row[13],
        "client_age": row[14],
        "client_temperament": row[15],
        "client_attitude": row[16],
        "client_communication_style": row[17],
        "client_buying_history": row[18],
        "client_decision_role": row[19],
        "client_tech_level": row[20],
        "client_persona": row[21],
        "client_pain_points": row[22],
        "client_typical_objections": row[23],
        "difficulty": row[24],
        "mode": row[25],
        "status": row[26],
        "current_stage": row[27],
        "final_goal": row[28],
        "goal_reached": bool(row[29]),
        "auto_completed": bool(row[30]),
        "started_at": row[31],
        "completed_at": row[32],
        "total_score": _decimal_to_float(row[33]),
        "last_message": row[34],
    }


def _fetch_session_dict(session_id: int, user_id: int) -> dict[str, Any]:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    s.id, sc.id, sc.title, sc.scenario_type, sc.description, sc.funnel_stage,
                    sc.is_full_funnel, sc.stage_hint, sc.final_goal, sc.success_markers, sc.failure_markers,
                    c.id, c.name, c.position, c.age, c.temperament, c.attitude, c.communication_style,
                    c.buying_history, c.decision_role, c.tech_level, c.persona, c.pain_points, c.typical_objections,
                    s.difficulty, s.mode, s.status, s.current_stage, s.final_goal, s.goal_reached,
                    s.auto_completed, s.started_at, s.completed_at, s.total_score,
                    (
                        SELECT dm.message_text
                        FROM dialog_trainer_messages dm
                        WHERE dm.session_id = s.id
                        ORDER BY dm.created_at DESC, dm.id DESC
                        LIMIT 1
                    ) AS last_message
                FROM dialog_trainer_sessions s
                JOIN dialog_trainer_scenarios sc ON sc.id = s.scenario_id
                JOIN dialog_trainer_clients c ON c.id = s.client_id
                WHERE s.id = %s AND s.user_id = %s
                """,
                (session_id, user_id),
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Диалог не найден")
    session = _session_row_to_dict(row)
    session["selected_products"] = _load_products_for_session(session_id)
    session["stage_final_goal"] = _stage_goal_text(session["current_stage"]) if session["is_full_funnel"] else session["final_goal"]
    return session


def _session_to_summary(session: dict[str, Any]) -> TrainerSessionSummaryResponse:
    return TrainerSessionSummaryResponse(
        id=session["id"],
        scenario_id=session["scenario_id"],
        scenario_title=session["scenario_title"],
        scenario_description=session.get("scenario_description"),
        funnel_stage=session["funnel_stage"],
        current_stage=session["current_stage"],
        stage_hint=session.get("stage_hint"),
        final_goal=session.get("stage_final_goal") or session.get("final_goal"),
        is_full_funnel=session["is_full_funnel"],
        client_id=session["client_id"],
        client_name=session["client_name"],
        client_position=session.get("client_position"),
        client_age=session.get("client_age"),
        client_temperament=session.get("client_temperament"),
        client_attitude=session.get("client_attitude"),
        client_communication_style=session.get("client_communication_style"),
        client_buying_history=session.get("client_buying_history"),
        client_decision_role=session.get("client_decision_role"),
        client_tech_level=session.get("client_tech_level"),
        client_persona=session.get("client_persona"),
        client_pain_points=session.get("client_pain_points"),
        client_typical_objections=session.get("client_typical_objections"),
        difficulty=session["difficulty"],
        mode=session["mode"],
        status=session["status"],
        goal_reached=session["goal_reached"],
        auto_completed=session["auto_completed"],
        brief_start_tip=_stage_start_tip(session["current_stage"], session["is_full_funnel"]),
        started_at=session["started_at"],
        completed_at=session.get("completed_at"),
        total_score=session.get("total_score"),
        last_message=session.get("last_message"),
        selected_products=session.get("selected_products", []),
    )


def _build_session_response(session_id: int, user_id: int) -> TrainerSessionResponse:
    session = _fetch_session_dict(session_id, user_id)
    summary = _session_to_summary(session)
    return TrainerSessionResponse(
        **summary.model_dump(),
        messages=_load_messages(session_id),
        result=_load_result(session_id),
    )


@router.get("/options", response_model=TrainerOptionsResponse)
def get_trainer_options(current_user: dict = Depends(get_current_user)) -> TrainerOptionsResponse:
    _ensure_trainer_schema()
    company_id = current_user["company_id"]

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, scenario_type, funnel_stage, is_full_funnel, description, stage_hint, final_goal
                FROM dialog_trainer_scenarios
                WHERE status = 'published'
                  AND (company_id = %s OR company_id IS NULL)
                ORDER BY is_full_funnel DESC, id ASC
                """,
                (company_id,),
            )
            scenario_rows = cur.fetchall()

            cur.execute(
                """
                SELECT id, name, position, age, temperament, attitude, communication_style,
                       buying_history, decision_role, tech_level, persona, pain_points, typical_objections
                FROM dialog_trainer_clients
                WHERE company_id = %s OR company_id IS NULL
                ORDER BY id ASC
                """,
                (company_id,),
            )
            client_rows = cur.fetchall()

    return TrainerOptionsResponse(
        scenarios=[_scenario_from_row(row) for row in scenario_rows],
        clients=[_client_from_row(row) for row in client_rows],
        products=[],
        difficulties=_DIFFICULTIES,
    )


@router.get("/sessions", response_model=list[TrainerSessionSummaryResponse])
def list_trainer_sessions(current_user: dict = Depends(get_current_user)) -> list[TrainerSessionSummaryResponse]:
    _ensure_trainer_schema()
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    s.id, sc.id, sc.title, sc.scenario_type, sc.description, sc.funnel_stage,
                    sc.is_full_funnel, sc.stage_hint, sc.final_goal, sc.success_markers, sc.failure_markers,
                    c.id, c.name, c.position, c.age, c.temperament, c.attitude, c.communication_style,
                    c.buying_history, c.decision_role, c.tech_level, c.persona, c.pain_points, c.typical_objections,
                    s.difficulty, s.mode, s.status, s.current_stage, s.final_goal, s.goal_reached,
                    s.auto_completed, s.started_at, s.completed_at, s.total_score,
                    (
                        SELECT dm.message_text
                        FROM dialog_trainer_messages dm
                        WHERE dm.session_id = s.id
                        ORDER BY dm.created_at DESC, dm.id DESC
                        LIMIT 1
                    ) AS last_message
                FROM dialog_trainer_sessions s
                JOIN dialog_trainer_scenarios sc ON sc.id = s.scenario_id
                JOIN dialog_trainer_clients c ON c.id = s.client_id
                WHERE s.user_id = %s
                ORDER BY s.started_at DESC
                LIMIT 50
                """,
                (current_user["id"],),
            )
            rows = cur.fetchall()

    result = []
    for row in rows:
        session = _session_row_to_dict(row)
        session["selected_products"] = _load_products_for_session(session["id"])
        session["stage_final_goal"] = _stage_goal_text(session["current_stage"]) if session["is_full_funnel"] else session["final_goal"]
        result.append(_session_to_summary(session))
    return result


@router.post("/sessions", response_model=TrainerSessionResponse, status_code=status.HTTP_201_CREATED)
def create_trainer_session(
    payload: TrainerSessionCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> TrainerSessionResponse:
    _ensure_trainer_schema()

    if payload.difficulty not in _ALLOWED_DIFFICULTIES:
        raise HTTPException(status_code=400, detail="Некорректная сложность")
    if payload.mode not in _ALLOWED_MODES:
        raise HTTPException(status_code=400, detail="Некорректный режим тренировки")

    company_id = current_user["company_id"]

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, scenario_type, funnel_stage, is_full_funnel, description, stage_hint, final_goal
                FROM dialog_trainer_scenarios
                WHERE id = %s
                  AND status = 'published'
                  AND (company_id = %s OR company_id IS NULL)
                """,
                (payload.scenario_id, company_id),
            )
            scenario_row = cur.fetchone()
            if not scenario_row:
                raise HTTPException(status_code=404, detail="Этап воронки не найден")
            scenario = _scenario_from_row(scenario_row)

            cur.execute(
                """
                SELECT id
                FROM dialog_trainer_clients
                WHERE id = %s
                  AND (company_id = %s OR company_id IS NULL)
                """,
                (payload.client_id, company_id),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Клиент не найден")

            start_stage = "intro" if scenario.is_full_funnel else scenario.funnel_stage
            final_goal = _stage_goal_text(start_stage) if scenario.is_full_funnel else (scenario.final_goal or _stage_goal_text(start_stage))

            cur.execute(
                """
                INSERT INTO dialog_trainer_sessions (
                    company_id, user_id, scenario_id, client_id, difficulty, mode,
                    current_stage, final_goal, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'started')
                RETURNING id
                """,
                (company_id, current_user["id"], scenario.id, payload.client_id, payload.difficulty, payload.mode, start_stage, final_goal),
            )
            session_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO dialog_trainer_messages (session_id, sender_type, message_text)
                VALUES (%s, 'system', %s)
                """,
                (session_id, f"Цель тренировки: {final_goal}\nС чего начать: {_stage_start_tip(start_stage, scenario.is_full_funnel)}"),
            )
        conn.commit()

    return _build_session_response(session_id, current_user["id"])


@router.get("/sessions/{session_id}", response_model=TrainerSessionResponse)
def get_trainer_session(session_id: int, current_user: dict = Depends(get_current_user)) -> TrainerSessionResponse:
    _ensure_trainer_schema()
    return _build_session_response(session_id, current_user["id"])


@router.post("/sessions/{session_id}/messages", response_model=TrainerSessionResponse)
def send_trainer_message(
    session_id: int,
    payload: TrainerMessageCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> TrainerSessionResponse:
    _ensure_trainer_schema()
    message = _compact(payload.message)
    if not message:
        raise HTTPException(status_code=400, detail="Реплика не должна быть пустой")

    session = _fetch_session_dict(session_id, current_user["id"])
    if session["status"] != "started":
        raise HTTPException(status_code=400, detail="Диалог уже завершён")

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO dialog_trainer_messages (session_id, sender_type, message_text)
                VALUES (%s, 'user', %s)
                """,
                (session_id, message),
            )
        conn.commit()

    messages_with_user = _load_messages(session_id)
    user_turns = len([m for m in messages_with_user if m.sender_type == "user"])
    session["selected_products"] = _load_products_for_session(session_id)
    client_reply = _generate_client_reply(session, messages_with_user, message, current_user["company_id"])

    goal_reached_for_stage = _goal_is_reached(session, client_reply, message, user_turns)
    new_stage = session["current_stage"]
    completed = False
    system_transition_message: str | None = None

    if goal_reached_for_stage:
        next_stage = _next_stage(session["current_stage"]) if session["is_full_funnel"] else None
        if next_stage:
            new_stage = next_stage
            system_transition_message = (
                f"Этап «{_STAGE_TITLES.get(session['current_stage'], session['current_stage'])}» пройден. "
                f"Переходим к этапу «{_STAGE_TITLES.get(next_stage, next_stage)}». "
                f"Новая цель: {_stage_goal_text(next_stage)}"
            )
        else:
            completed = True

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO dialog_trainer_messages (session_id, sender_type, message_text)
                VALUES (%s, 'virtual_client', %s)
                """,
                (session_id, client_reply),
            )
            if system_transition_message:
                cur.execute(
                    """
                    INSERT INTO dialog_trainer_messages (session_id, sender_type, message_text)
                    VALUES (%s, 'system', %s)
                    """,
                    (session_id, system_transition_message),
                )
                cur.execute(
                    """
                    UPDATE dialog_trainer_sessions
                    SET current_stage = %s,
                        final_goal = %s
                    WHERE id = %s
                    """,
                    (new_stage, _stage_goal_text(new_stage), session_id),
                )
            if completed:
                messages_for_score = _load_messages(session_id)
                messages_for_score.append(
                    TrainerMessageResponse(id=0, sender_type="virtual_client", message_text=client_reply, created_at=datetime.utcnow())
                )
                total_score, strong_sides, weak_sides, recommendations = _score_dialog(session, messages_for_score, True, False, current_user["company_id"])
                cur.execute(
                    """
                    UPDATE dialog_trainer_sessions
                    SET status = 'completed',
                        completed_at = NOW(),
                        total_score = %s,
                        goal_reached = TRUE,
                        auto_completed = TRUE
                    WHERE id = %s
                    """,
                    (total_score, session_id),
                )
                cur.execute(
                    """
                    INSERT INTO dialog_trainer_results (session_id, total_score, strong_sides, weak_sides, recommendations)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (session_id) DO UPDATE
                    SET total_score = EXCLUDED.total_score,
                        strong_sides = EXCLUDED.strong_sides,
                        weak_sides = EXCLUDED.weak_sides,
                        recommendations = EXCLUDED.recommendations,
                        created_at = NOW()
                    """,
                    (session_id, total_score, strong_sides, weak_sides, recommendations),
                )
        conn.commit()

    return _build_session_response(session_id, current_user["id"])


@router.post("/sessions/{session_id}/finish", response_model=TrainerSessionResponse)
def finish_trainer_session(session_id: int, current_user: dict = Depends(get_current_user)) -> TrainerSessionResponse:
    _ensure_trainer_schema()
    session = _fetch_session_dict(session_id, current_user["id"])
    messages = _load_messages(session_id)
    goal_reached = bool(session.get("goal_reached"))
    total_score, strong_sides, weak_sides, recommendations = _score_dialog(session, messages, goal_reached, True, current_user["company_id"])

    if not goal_reached:
        recommendations = "Диалог завершён вручную. Финальная цель не была достигнута автоматически.\n" + recommendations

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE dialog_trainer_sessions
                SET status = 'completed',
                    completed_at = COALESCE(completed_at, NOW()),
                    total_score = %s,
                    auto_completed = FALSE
                WHERE id = %s AND user_id = %s
                """,
                (total_score, session_id, current_user["id"]),
            )
            cur.execute(
                """
                INSERT INTO dialog_trainer_results (session_id, total_score, strong_sides, weak_sides, recommendations)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE
                SET total_score = EXCLUDED.total_score,
                    strong_sides = EXCLUDED.strong_sides,
                    weak_sides = EXCLUDED.weak_sides,
                    recommendations = EXCLUDED.recommendations,
                    created_at = NOW()
                """,
                (session_id, total_score, strong_sides, weak_sides, recommendations),
            )
        conn.commit()

    return _build_session_response(session_id, current_user["id"])
