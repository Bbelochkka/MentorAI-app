CREATE TABLE IF NOT EXISTS dialog_trainer_scenarios (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT,
    title VARCHAR(255) NOT NULL,
    scenario_type VARCHAR(50) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'published',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_dialog_trainer_scenarios_type CHECK (scenario_type IN ('cold_call', 'objection_handling', 'closing', 'custom')),
    CONSTRAINT chk_dialog_trainer_scenarios_status CHECK (status IN ('draft', 'published', 'archived'))
);

ALTER TABLE dialog_trainer_scenarios
ADD COLUMN IF NOT EXISTS funnel_stage VARCHAR(30) DEFAULT 'intro',
ADD COLUMN IF NOT EXISTS is_full_funnel BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS stage_hint TEXT,
ADD COLUMN IF NOT EXISTS final_goal TEXT,
ADD COLUMN IF NOT EXISTS success_markers TEXT;

CREATE TABLE IF NOT EXISTS dialog_trainer_clients (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT,
    name VARCHAR(255) NOT NULL,
    position VARCHAR(255),
    persona TEXT,
    pain_points TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE dialog_trainer_clients
ADD COLUMN IF NOT EXISTS age INTEGER,
ADD COLUMN IF NOT EXISTS temperament VARCHAR(255),
ADD COLUMN IF NOT EXISTS attitude VARCHAR(255),
ADD COLUMN IF NOT EXISTS communication_style TEXT,
ADD COLUMN IF NOT EXISTS buying_history TEXT,
ADD COLUMN IF NOT EXISTS decision_role TEXT,
ADD COLUMN IF NOT EXISTS tech_level VARCHAR(100),
ADD COLUMN IF NOT EXISTS typical_objections TEXT;

CREATE TABLE IF NOT EXISTS dialog_trainer_sessions (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scenario_id BIGINT NOT NULL REFERENCES dialog_trainer_scenarios(id) ON DELETE RESTRICT,
    client_id BIGINT NOT NULL REFERENCES dialog_trainer_clients(id) ON DELETE RESTRICT,
    difficulty VARCHAR(10) NOT NULL DEFAULT 'medium',
    mode VARCHAR(20) NOT NULL DEFAULT 'practice',
    status VARCHAR(20) NOT NULL DEFAULT 'started',
    current_stage VARCHAR(30) NOT NULL DEFAULT 'intro',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_score NUMERIC(5,2),
    CONSTRAINT chk_dialog_trainer_sessions_difficulty CHECK (difficulty IN ('easy', 'medium', 'hard')),
    CONSTRAINT chk_dialog_trainer_sessions_mode CHECK (mode IN ('practice', 'exam')),
    CONSTRAINT chk_dialog_trainer_sessions_status CHECK (status IN ('started', 'completed', 'abandoned')),
    CONSTRAINT chk_dialog_trainer_sessions_stage CHECK (current_stage IN ('intro', 'need_discovery', 'presentation', 'objection', 'closing', 'custom'))
);

ALTER TABLE dialog_trainer_sessions
ADD COLUMN IF NOT EXISTS goal_reached BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS auto_completed BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS dialog_trainer_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES dialog_trainer_sessions(id) ON DELETE CASCADE,
    sender_type VARCHAR(20) NOT NULL,
    message_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_dialog_trainer_messages_sender CHECK (sender_type IN ('user', 'virtual_client', 'system'))
);

CREATE TABLE IF NOT EXISTS dialog_trainer_results (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL UNIQUE REFERENCES dialog_trainer_sessions(id) ON DELETE CASCADE,
    total_score NUMERIC(5,2) NOT NULL DEFAULT 0,
    strong_sides TEXT,
    weak_sides TEXT,
    recommendations TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dialog_trainer_sessions_user_started
    ON dialog_trainer_sessions (user_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_dialog_trainer_messages_session_created
    ON dialog_trainer_messages (session_id, created_at ASC, id ASC);

INSERT INTO dialog_trainer_scenarios (
    id, company_id, title, scenario_type, funnel_stage, is_full_funnel,
    description, stage_hint, final_goal, success_markers, status
)
VALUES
    (
        1,
        1,
        'Холодный звонок',
        'cold_call',
        'intro',
        FALSE,
        'Первый контакт с потенциальным клиентом.',
        'На этом этапе менеджер должен представиться, назвать компанию, объяснить повод обращения и получить разрешение продолжить разговор.',
        'Клиент согласился продолжить разговор или ответить на 1–2 уточняющих вопроса.',
        'слушаю; задавайте вопрос; давайте коротко; готов выслушать; расскажите; можете спросить; спрашивайте',
        'published'
    ),
    (
        2,
        1,
        'Обработка возражений',
        'objection_handling',
        'objection',
        FALSE,
        'Клиент сомневается в цене, пользе или необходимости решения.',
        'Менеджер должен признать сомнение, уточнить причину и дать аргумент без спора и давления.',
        'Клиент принял аргумент или согласился продолжить обсуждение.',
        'логично; звучит разумно; можно сравнить; давайте посмотрим; готов обсудить; убедительно',
        'published'
    ),
    (
        3,
        1,
        'Закрытие сделки',
        'closing',
        'closing',
        FALSE,
        'Финальный этап общения с клиентом.',
        'Менеджер должен подвести итог, предложить конкретный следующий шаг и согласовать время или действие.',
        'Клиент согласился на заявку, подключение, демо, КП, встречу или повторный контакт.',
        'оформляйте; давайте подключим; пришлите КП; согласен на демо; завтра удобно; давайте заявку; назначим встречу; отправьте предложение',
        'published'
    ),
    (
        4,
        1,
        'Выявление потребности',
        'custom',
        'need_discovery',
        FALSE,
        'Этап уточнения задачи клиента.',
        'Менеджер задаёт открытые вопросы, чтобы понять боль клиента, текущую ситуацию и критерии выбора.',
        'Клиент сформулировал проблему, потребность или критерии выбора.',
        'мне важно; проблема в том что; хочу чтобы; нужно решить; не хватает; неудобно; хотелось бы',
        'published'
    ),
    (
        5,
        1,
        'Презентация продукта',
        'custom',
        'presentation',
        FALSE,
        'Этап объяснения ценности продукта.',
        'Менеджер связывает продукт с потребностью клиента и объясняет пользу без перегруза деталями.',
        'Клиент понял ценность предложения и готов обсуждать условия или следующий шаг.',
        'звучит интересно; подходит; понимаю пользу; можно обсудить; расскажите условия; выглядит полезно',
        'published'
    ),
    (
        6,
        1,
        'Полная воронка продаж',
        'custom',
        'intro',
        TRUE,
        'Полная тренировка от первого контакта до договорённости о следующем шаге.',
        'Тренировка проходит через все этапы: холодный звонок, выявление потребности, презентация, обработка возражений и закрытие сделки.',
        'Клиент согласился на конкретный следующий шаг: заявку, подключение, КП, демо, встречу или повторный контакт.',
        'оформляйте; давайте подключим; пришлите КП; согласен на демо; завтра удобно; давайте заявку; назначим встречу; отправьте предложение',
        'published'
    )
ON CONFLICT (id) DO UPDATE
SET title = EXCLUDED.title,
    scenario_type = EXCLUDED.scenario_type,
    funnel_stage = EXCLUDED.funnel_stage,
    is_full_funnel = EXCLUDED.is_full_funnel,
    description = EXCLUDED.description,
    stage_hint = EXCLUDED.stage_hint,
    final_goal = EXCLUDED.final_goal,
    success_markers = EXCLUDED.success_markers,
    status = EXCLUDED.status;

INSERT INTO dialog_trainer_clients (
    id, company_id, name, position, age, temperament, attitude, communication_style,
    buying_history, decision_role, tech_level, persona, pain_points, typical_objections
)
VALUES
    (
        1,
        1,
        'Евгений',
        'Руководитель отдела продаж',
        38,
        'рациональный, быстрый, требовательный',
        'занят, готов слушать только конкретику',
        'отвечает коротко, перебивает длинные презентации, просит цифры и сроки',
        'раньше услугами компании не пользовался',
        'лицо, влияющее на решение',
        'высокий',
        'Деловой и занятый клиент. Если менеджер говорит общо, быстро теряет интерес.',
        'Хочет контролировать расходы команды, быстро подключать сотрудников и видеть прозрачную детализацию.',
        'нет времени; у нас уже есть оператор; покажите выгоду в цифрах; не хочу менять процессы'
    ),
    (
        2,
        1,
        'Ольга',
        'Частный клиент, мама двоих детей',
        42,
        'доброжелательная, осторожная',
        'открыта к разговору, но боится сложных условий',
        'задаёт бытовые вопросы, просит объяснять простыми словами',
        'покупала SIM-карту компании для себя',
        'самостоятельно принимает решение',
        'средний',
        'Вежлива и готова слушать, если менеджер не давит и объясняет человеческим языком.',
        'Хочет контролировать расходы детей и не получать неожиданные списания.',
        'сложно переносить номера; дети не разберутся; боюсь скрытых платежей'
    ),
    (
        3,
        1,
        'Игорь',
        'Коммерческий директор',
        45,
        'скептичный, жёсткий, аналитичный',
        'сомневается и проверяет каждое обещание',
        'может грубить, если слышит рекламные фразы; уважает точные аргументы',
        'с компанией не работал, есть негативный опыт с другим поставщиком',
        'ключевое лицо, принимающее решение',
        'высокий',
        'Не любит мягкие обещания. Ему нужны риски, экономика, пилот и понятный контроль результата.',
        'Нужны экономия бюджета, контроль расходов и отсутствие хаоса при подключении сотрудников.',
        'дорого; уже есть поставщик; не верю обещаниям; нужен пилот'
    ),
    (
        4,
        1,
        'Николай Петрович',
        'Пенсионер',
        68,
        'спокойный, осторожный, медленный в принятии решения',
        'вежливый, но плохо воспринимает технические термины',
        'часто просит повторить, не любит англицизмы и сложные формулировки',
        'пользовался услугами компании несколько лет назад',
        'самостоятельно принимает решение, но может советоваться с семьёй',
        'низкий',
        'Не грубит, но легко теряется, если менеджер говорит быстро или технически сложно.',
        'Хочет простой продукт без скрытых платежей и непонятных условий.',
        'я не понимаю технические условия; мне бы без лишнего; не хочу, чтобы списывали деньги'
    )
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
    typical_objections = EXCLUDED.typical_objections;
