-- db_auth_migration.sql
-- Безопасная миграция пользователей: русские строки задаются через UTF-8 HEX,
-- поэтому файл корректно выполняется на Windows и на другом устройстве.

ALTER TABLE users ADD COLUMN IF NOT EXISTS hire_date DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS job_title VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS supervisor_id BIGINT;

INSERT INTO roles (id, code)
VALUES
    (1, 'employer'),
    (2, 'manager'),
    (3, 'admin')
ON CONFLICT (id) DO NOTHING;

-- Руководитель

INSERT INTO users (
    id,
    company_id,
    role_id,
    full_name,
    email,
    password_hash,
    is_active,
    hire_date,
    job_title,
    department,
    supervisor_id
)
VALUES (
    1,
    1,
    2,
    convert_from(decode('d090d0bdd183d187d0b8d0bdd0b020d090d0bbd191d0bdd0b020d09ed0bbd0b5d0b3d0bed0b2d0bdd0b0', 'hex'), 'UTF8'),
    'aoanuchina@hse.edu.ru',
    'pbkdf2_sha256$260000$f75600dfc248c47f3cad42f4ff9ceeae$198a838deef3d9ff1e39a759e36bee61587f8cae7aeb0e82fcfc9362aeae6270',
    TRUE,
    CURRENT_DATE,
    convert_from(decode('d0a0d183d0bad0bed0b2d0bed0b4d0b8d182d0b5d0bbd18c20d0bed182d0b4d0b5d0bbd0b020d0bfd180d0bed0b4d0b0d0b6', 'hex'), 'UTF8'),
    convert_from(decode('d09ed182d0b4d0b5d0bb20d0bfd180d0bed0b4d0b0d0b6', 'hex'), 'UTF8'),
    NULL
)
ON CONFLICT (id) DO UPDATE
SET
    company_id = EXCLUDED.company_id,
    role_id = EXCLUDED.role_id,
    full_name = EXCLUDED.full_name,
    email = EXCLUDED.email,
    password_hash = EXCLUDED.password_hash,
    is_active = EXCLUDED.is_active,
    hire_date = EXCLUDED.hire_date,
    job_title = EXCLUDED.job_title,
    department = EXCLUDED.department,
    supervisor_id = EXCLUDED.supervisor_id;

-- Тестовый стажёр

INSERT INTO users (
    id,
    company_id,
    role_id,
    full_name,
    email,
    password_hash,
    is_active,
    hire_date,
    job_title,
    department,
    supervisor_id
)
VALUES (
    2,
    1,
    1,
    convert_from(decode('d09fd0bed0bfd0bed0b220d090d180d181d0b5d0bdd0b8d0b920d090d0bbd0b5d0bad181d0b0d0bdd0b4d180d0bed0b2d0b8d187', 'hex'), 'UTF8'),
    'trainee@mentorai.local',
    'pbkdf2_sha256$260000$14df469ff9465bdc97312bd58a35458f$62797760ec7d4d00af317c445205e50ca813a4f7c9b1034801ca7013a1b3e745',
    TRUE,
    CURRENT_DATE,
    convert_from(decode('d09cd0b5d0bdd0b5d0b4d0b6d0b5d18020d0bfd0be20d0bfd180d0bed0b4d0b0d0b6d0b0d0bc', 'hex'), 'UTF8'),
    convert_from(decode('d09ed182d0b4d0b5d0bb20d0bfd180d0bed0b4d0b0d0b6', 'hex'), 'UTF8'),
    1
)
ON CONFLICT (id) DO UPDATE
SET
    company_id = EXCLUDED.company_id,
    role_id = EXCLUDED.role_id,
    full_name = EXCLUDED.full_name,
    email = EXCLUDED.email,
    password_hash = EXCLUDED.password_hash,
    is_active = EXCLUDED.is_active,
    hire_date = EXCLUDED.hire_date,
    job_title = EXCLUDED.job_title,
    department = EXCLUDED.department,
    supervisor_id = EXCLUDED.supervisor_id;

-- Тестовый администратор

INSERT INTO users (
    id,
    company_id,
    role_id,
    full_name,
    email,
    password_hash,
    is_active,
    hire_date,
    job_title,
    department,
    supervisor_id
)
VALUES (
    3,
    1,
    3,
    convert_from(decode('d090d0b4d0bcd0b8d0bdd0b8d181d182d180d0b0d182d0bed180', 'hex'), 'UTF8'),
    'admin@mentorai.com',
    'pbkdf2_sha256$260000$f75600dfc248c47f3cad42f4ff9ceeae$198a838deef3d9ff1e39a759e36bee61587f8cae7aeb0e82fcfc9362aeae6270',
    TRUE,
    CURRENT_DATE,
    convert_from(decode('d090d0b4d0bcd0b8d0bdd0b8d181d182d180d0b0d182d0bed18020d181d0b8d181d182d0b5d0bcd18b', 'hex'), 'UTF8'),
    convert_from(decode('d090d0b4d0bcd0b8d0bdd0b8d181d182d180d0b8d180d0bed0b2d0b0d0bdd0b8d0b5', 'hex'), 'UTF8'),
    NULL
)
ON CONFLICT (id) DO UPDATE
SET
    company_id = EXCLUDED.company_id,
    role_id = EXCLUDED.role_id,
    full_name = EXCLUDED.full_name,
    email = EXCLUDED.email,
    password_hash = EXCLUDED.password_hash,
    is_active = EXCLUDED.is_active,
    hire_date = EXCLUDED.hire_date,
    job_title = EXCLUDED.job_title,
    department = EXCLUDED.department,
    supervisor_id = EXCLUDED.supervisor_id;

-- Если раньше был создан стажёр со старым email trainee@mentorai.dev,
-- скрываем его, чтобы он не дублировался в интерфейсе.

UPDATE users
SET is_active = FALSE
WHERE email = 'trainee@mentorai.dev';

-- Если остались строки, где ФИО было испорчено в ????,
-- но это системные тестовые пользователи, обновляем их напрямую по email.

UPDATE users
SET
    full_name = convert_from(decode('d090d0bdd183d187d0b8d0bdd0b020d090d0bbd191d0bdd0b020d09ed0bbd0b5d0b3d0bed0b2d0bdd0b0', 'hex'), 'UTF8'),
    job_title = convert_from(decode('d0a0d183d0bad0bed0b2d0bed0b4d0b8d182d0b5d0bbd18c20d0bed182d0b4d0b5d0bbd0b020d0bfd180d0bed0b4d0b0d0b6', 'hex'), 'UTF8'),
    department = convert_from(decode('d09ed182d0b4d0b5d0bb20d0bfd180d0bed0b4d0b0d0b6', 'hex'), 'UTF8'),
    supervisor_id = NULL,
    is_active = TRUE
WHERE email = 'aoanuchina@hse.edu.ru';

UPDATE users
SET
    full_name = convert_from(decode('d09fd0bed0bfd0bed0b220d090d180d181d0b5d0bdd0b8d0b920d090d0bbd0b5d0bad181d0b0d0bdd0b4d180d0bed0b2d0b8d187', 'hex'), 'UTF8'),
    job_title = convert_from(decode('d09cd0b5d0bdd0b5d0b4d0b6d0b5d18020d0bfd0be20d0bfd180d0bed0b4d0b0d0b6d0b0d0bc', 'hex'), 'UTF8'),
    department = convert_from(decode('d09ed182d0b4d0b5d0bb20d0bfd180d0bed0b4d0b0d0b6', 'hex'), 'UTF8'),
    supervisor_id = 1,
    is_active = TRUE
WHERE email = 'trainee@mentorai.local';

UPDATE users
SET
    full_name = convert_from(decode('d090d0b4d0bcd0b8d0bdd0b8d181d182d180d0b0d182d0bed180', 'hex'), 'UTF8'),
    job_title = convert_from(decode('d090d0b4d0bcd0b8d0bdd0b8d181d182d180d0b0d182d0bed18020d181d0b8d181d182d0b5d0bcd18b', 'hex'), 'UTF8'),
    department = convert_from(decode('d090d0b4d0bcd0b8d0bdd0b8d181d182d180d0b8d180d0bed0b2d0b0d0bdd0b8d0b5', 'hex'), 'UTF8'),
    supervisor_id = NULL,
    is_active = TRUE
WHERE email = 'admin@mentorai.com';

SELECT setval(
    pg_get_serial_sequence('users', 'id'),
    GREATEST((SELECT MAX(id) FROM users), 3),
    TRUE
);