import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../api';
import loginImage from '../assets/login-image.png';

export function LoginPage() {
  const navigate = useNavigate();

  const [email, setEmail] = useState('aoanuchina@hse.edu.ru');
  const [password, setPassword] = useState('password123');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const response = await login({ email, password });
      localStorage.setItem('mentorai_token', response.access_token);
      localStorage.setItem('mentorai_user', JSON.stringify(response.user));
      navigate('/app');
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Не удалось войти');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="login-layout">
      <section className="login-hero">
        <img src={loginImage} alt="MentorAI" className="login-hero-image" />
      </section>

      <section className="login-panel">
        <div className="login-card">
          <div className="brand">
            <span className="brand__mentor">Mentor</span>
            <span className="brand__ai">AI</span>
          </div>

          <form className="login-form" onSubmit={handleSubmit}>
            <label className="login-form__label" htmlFor="email">
              Войти
            </label>

            <input
              id="email"
              className="login-input"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="Введите e-mail"
              required
            />

            <div className="password-field">
              <input
                className="login-input"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Введите пароль"
                required
              />
              <button
                className="password-toggle"
                type="button"
                onClick={() => setShowPassword((current) => !current)}
                aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
              >
                {showPassword ? '🙈' : '👁️'}
              </button>
            </div>

            <button className="submit-button" type="submit" disabled={isLoading}>
              {isLoading ? 'Входим...' : 'Войти'}
            </button>

            <button className="forgot-link" type="button">
              Забыли пароль?
            </button>

            {error ? <p className="login-error">{error}</p> : null}
          </form>
        </div>
      </section>
    </main>
  );
}