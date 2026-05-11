import { Link, NavLink, useNavigate } from 'react-router-dom';
import { getStoredUser, isAdminUser, isLearnerUser } from '../api';

type SidebarSection =
  | 'documents'
  | 'courses'
  | 'tests'
  | 'analytics'
  | 'myAnalytics'
  | 'trainer'
  | 'guide'
  | 'employees';

type SidebarItem = {
  key: SidebarSection;
  label: string;
  path: string;
  icon: string;
};

const allMenuItems: SidebarItem[] = [
   {
    key: 'documents',
    label: 'Документы',
    path: '/app/documents',
    icon: '/sidebar-icons/documents.svg',
  },
  {
    key: 'courses',
    label: 'Курсы',
    path: '/app/courses',
    icon: '/sidebar-icons/courses.svg',
  },
  {
    key: 'tests',
    label: 'Тесты',
    path: '/app/tests',
    icon: '/sidebar-icons/tests.svg',
  },
  {
    key: 'trainer',
    label: 'Диалоговый тренажёр',
    path: '/app/trainer',
    icon: '/sidebar-icons/dialog-trainer.svg',
  },
  {
    key: 'analytics',
    label: 'Аналитика',
    path: '/app/analytics',
    icon: '/sidebar-icons/analytics.svg',
  },
  {
    key: 'myAnalytics',
    label: 'Моя аналитика',
    path: '/app/my-analytics',
    icon: '/sidebar-icons/my-analytics.svg',
  },
  {
    key: 'guide',
    label: 'Руководство пользователя',
    path: '/app/guide',
    icon: '/sidebar-icons/guide.svg',
  },
  
  {
    key: 'employees',
    label: 'Сотрудники',
    path: '/app/employees',
    icon: '/sidebar-icons/employees.svg',
  },
];

export function Sidebar() {
  const navigate = useNavigate();

  const currentUser = getStoredUser();
  const learner = isLearnerUser(currentUser);
  const admin = isAdminUser(currentUser);

  const menuItems = allMenuItems.filter((item) => {
    if (admin) {
      return item.key === 'employees';
    }

    if (learner) {
      return (
        item.key === 'courses' ||
        item.key === 'tests' ||
        item.key === 'myAnalytics' ||
        item.key === 'trainer' ||
        item.key === 'guide'
      );
    }

    return item.key !== 'employees' && item.key !== 'myAnalytics';
  });

  function handleLogout() {
    const confirmed = window.confirm('Вы точно хотите выйти?');

    if (!confirmed) {
      return;
    }

    localStorage.removeItem('mentorai_token');
    localStorage.removeItem('mentorai_user');

    navigate('/', { replace: true });
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <Link to="/app" className="sidebar-brand" aria-label="На главную">
        <span className="brand__mentor">Mentor</span>
        <span className="brand__ai">AI</span></Link>

        <nav className="sidebar-nav" aria-label="Основное меню">
          {menuItems.map((item) => (
            <NavLink
              key={item.key}
              to={item.path}
              className={({ isActive }) =>
                `sidebar-link ${isActive ? 'active' : ''}`
              }
            >
              <img
                className="sidebar-link__icon"
                src={item.icon}
                alt=""
                aria-hidden="true"
              />
              <span className="sidebar-link__label">{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="sidebar-bottom">
        {!admin ? (
          <NavLink
            to="/app/chatbot"
            className={({ isActive }) =>
              `chatbot-shortcut ${isActive ? 'active' : ''}`
            }
          >
            <img
              className="sidebar-link__icon"
              src="/sidebar-icons/chatbot.svg"
              alt=""
              aria-hidden="true"
            />
            <span className="sidebar-link__label">Чат-бот</span>
          </NavLink>
        ) : null}

        <button type="button" className="sidebar-logout" onClick={handleLogout}>
          <img
            className="sidebar-link__icon"
            src="/sidebar-icons/logout.svg"
            alt=""
            aria-hidden="true"
          />
          <span className="sidebar-link__label">Выйти</span>
        </button>
      </div>
    </aside>
  );
}