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
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  function isValidEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);}

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();

  setError(null);
  setEmailError(null);
  setPasswordError(null);

  if (!isValidEmail(email)) {
    setEmailError('Неверный электронный адрес');
    return;
  }

  setIsLoading(true);

  try {
    const response = await login({ email, password });
    localStorage.setItem('mentorai_token', response.access_token);
    localStorage.setItem('mentorai_user', JSON.stringify(response.user));
    navigate('/app');
  } catch (submitError) {
    const message = submitError instanceof Error ? submitError.message : '';

    if (
      message.toLowerCase().includes('email') ||
      message.toLowerCase().includes('почт') ||
      message.toLowerCase().includes('пользователь')
    ) {
      setEmailError('Неверный электронный адрес');
    } else {
      setPasswordError('Неверный пароль');
    }
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

          <form className="login-form" onSubmit={handleSubmit} noValidate>
            <label className="login-form__label" htmlFor="email">
              Войти
            </label>

<div className="login-field">
  <input
    id="email"
    className={`login-input ${emailError ? 'login-input--error' : ''}`}
    type="email"
    value={email}
    onChange={(event) => {
      setEmail(event.target.value);
      setEmailError(null);
    }}
    placeholder="Введите e-mail"
    required
  />

  {emailError ? <p className="login-field-error">{emailError}</p> : null}
  <div className="password-field">
    <input
      className={`login-input ${passwordError ? 'login-input--error' : ''}`}
      type={showPassword ? 'text' : 'password'}
      value={password}
      onChange={(event) => {
        setPassword(event.target.value);
        setPasswordError(null);
      }}
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

  {passwordError ? <p className="login-field-error">{passwordError}</p> : null}
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