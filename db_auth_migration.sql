-- Обновление существующего bootstrap-пользователя на хэшированный пароль
UPDATE users
SET password_hash = 'pbkdf2_sha256$260000$f75600dfc248c47f3cad42f4ff9ceeae$198a838deef3d9ff1e39a759e36bee61587f8cae7aeb0e82fcfc9362aeae6270'
WHERE email = 'aoanuchina@hse.edu.ru';

-- Создание тестового стажёра, если его ещё нет
INSERT INTO users (id, company_id, role_id, full_name, email, password_hash)
VALUES (2, 1, 1, 'Стажёр', 'trainee@mentorai.dev', 'pbkdf2_sha256$260000$14df469ff9465bdc97312bd58a35458f$62797760ec7d4d00af317c445205e50ca813a4f7c9b1034801ca7013a1b3e745')
ON CONFLICT (id) DO NOTHING;
