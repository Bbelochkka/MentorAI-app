import { NavLink } from 'react-router-dom';
import { getStoredUser, isAdminUser, isLearnerUser } from '../api';

type SidebarSection = 'documents' | 'courses' | 'tests' | 'analytics' | 'trainer' | 'guide' | 'employees';

const allMenuItems: Array<{ key: SidebarSection; label: string; path: string }> = [
  { key: 'documents', label: 'Документы', path: '/app/documents' },
  { key: 'courses', label: 'Курсы', path: '/app/courses' },
  { key: 'tests', label: 'Тесты', path: '/app/tests' },
  { key: 'trainer', label: 'Диалоговый тренажёр', path: '/app/trainer' },
  { key: 'analytics', label: 'Аналитика', path: '/app/analytics' },
  { key: 'guide', label: 'Руководство пользователя', path: '/app/guide' },
  { key: 'employees', label: 'Сотрудники', path: '/app/employees' },
];

export function Sidebar() {
  const currentUser = getStoredUser();
  const learner = isLearnerUser(currentUser);
  const admin = isAdminUser(currentUser);

const menuItems = allMenuItems.filter((item) => {
  if (learner) {
    return item.key !== 'documents' && item.key !== 'analytics' && item.key !== 'employees';
  }

  if (!admin && item.key === 'employees') {
    return false;
  }

  return true;
});

  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <div className="brand sidebar-brand">
          <span className="brand__mentor">Mentor</span>
          <span className="brand__ai">AI</span>
        </div>

        <nav className="sidebar-nav" aria-label="Основное меню">
          {menuItems.map((item) => (
            <NavLink
              key={item.key}
              to={item.path}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            >
              <span className="sidebar-link__icon" />
              <span className="sidebar-link__label">{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="sidebar-bottom">
        <NavLink to="/app/chatbot" className={({ isActive }) => `chatbot-shortcut ${isActive ? 'active' : ''}`}>
          <span className="chatbot-shortcut__icon" />
          <span>Чат-бот</span>
        </NavLink>
      </div>
    </aside>
  );
}
