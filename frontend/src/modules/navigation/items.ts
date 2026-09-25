import type { UserRole } from "@/api/http";
import { DASHBOARD_ROUTE } from "@/pages/dashboard/constants";
import { WORKSPACE_SECTION_ROUTES } from "@/pages/workspace-section/constants";

export type NavigationIconName =
  | "home"
  | "courses"
  | "skills"
  | "history"
  | "progress"
  | "learners"
  | "reviews"
  | "questions"
  | "builder"
  | "groups"
  | "users";

export interface NavigationItem {
  name: string;
  path: string;
  label: string;
  description: string;
  icon: NavigationIconName;
}

export const navigationByRole: Record<UserRole, NavigationItem[]> = {
  student: [
    {
      ...DASHBOARD_ROUTE,
      label: "Главная",
      description: "Ваше пространство обучения",
      icon: "home",
    },
    {
      ...WORKSPACE_SECTION_ROUTES.studentCourses,
      label: "Курсы",
      description: "Доступные курсы и шаги",
      icon: "courses",
    },
    {
      ...WORKSPACE_SECTION_ROUTES.studentSkills,
      label: "Навыки",
      description: "Ваш путь в программировании",
      icon: "skills",
    },
    {
      ...WORKSPACE_SECTION_ROUTES.studentHistory,
      label: "История",
      description: "Попытки и отзывы",
      icon: "history",
    },
    {
      ...WORKSPACE_SECTION_ROUTES.studentProgress,
      label: "Прогресс",
      description: "Результаты по курсам",
      icon: "progress",
    },
  ],
  curator: [
    {
      ...DASHBOARD_ROUTE,
      label: "Обзор",
      description: "Рабочее пространство куратора",
      icon: "home",
    },
    {
      ...WORKSPACE_SECTION_ROUTES.curatorLearners,
      label: "Ученики",
      description: "Ученики ваших групп",
      icon: "learners",
    },
    {
      ...WORKSPACE_SECTION_ROUTES.curatorReviews,
      label: "Проверки",
      description: "Работы на ручную проверку",
      icon: "reviews",
    },
    {
      ...WORKSPACE_SECTION_ROUTES.curatorQuestions,
      label: "Вопросы",
      description: "Вопросы по шагам",
      icon: "questions",
    },
  ],
  admin: [
    {
      ...DASHBOARD_ROUTE,
      label: "Обзор",
      description: "Рабочее пространство администратора",
      icon: "home",
    },
    {
      ...WORKSPACE_SECTION_ROUTES.adminCourses,
      label: "Курсы",
      description: "Черновики и опубликованные курсы",
      icon: "courses",
    },
    {
      ...WORKSPACE_SECTION_ROUTES.adminBuilder,
      label: "Конструктор",
      description: "Модули и шаги курсов",
      icon: "builder",
    },
    {
      ...WORKSPACE_SECTION_ROUTES.adminGroups,
      label: "Группы",
      description: "Группы и кураторы",
      icon: "groups",
    },
    {
      ...WORKSPACE_SECTION_ROUTES.adminUsers,
      label: "Пользователи",
      description: "Роли и участники",
      icon: "users",
    },
  ],
};

export function navigationForRole(role: UserRole | null): NavigationItem[] {
  return role ? navigationByRole[role] : [];
}
