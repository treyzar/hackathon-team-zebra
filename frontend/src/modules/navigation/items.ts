import type { UserRole } from "@/api/http";
import { DASHBOARD_ROUTE } from "@/pages/dashboard/constants";
import { ADMIN_BUILDER_ROUTE } from "@/pages/admin/builder/constants";
import { ADMIN_COURSES_ROUTE } from "@/pages/admin/courses/constants";
import { ADMIN_GROUPS_ROUTE } from "@/pages/admin/groups/constants";
import { ADMIN_USERS_ROUTE } from "@/pages/admin/users/constants";
import { CURATOR_REVIEWS_ROUTE } from "@/pages/curator/reviews/constants";
import { STUDENT_COURSES_ROUTE } from "@/pages/student/courses/constants";
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
      ...STUDENT_COURSES_ROUTE,
      label: "Мои курсы",
      description: "Курсы, на которые вы записаны",
      icon: "courses",
    },
    {
      ...WORKSPACE_SECTION_ROUTES.studentSkills,
      label: "Карта навыков",
      description: "Ваш путь в программировании",
      icon: "skills",
    },
    {
      ...WORKSPACE_SECTION_ROUTES.studentHistory,
      label: "Мои работы",
      description: "Отправленные решения и отзывы",
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
      ...CURATOR_REVIEWS_ROUTE,
      label: "Работы на проверку",
      description: "Работы учеников для проверки",
      icon: "reviews",
    },
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
      ...ADMIN_COURSES_ROUTE,
      label: "Курсы",
      description: "Черновики и опубликованные курсы",
      icon: "courses",
    },
    {
      ...ADMIN_BUILDER_ROUTE,
      label: "Конструктор",
      description: "Модули и шаги курсов",
      icon: "builder",
    },
    {
      ...ADMIN_GROUPS_ROUTE,
      label: "Группы",
      description: "Группы и кураторы",
      icon: "groups",
    },
    {
      ...ADMIN_USERS_ROUTE,
      label: "Пользователи",
      description: "Роли и участники",
      icon: "users",
    },
  ],
};

export function navigationForRole(role: UserRole | null): NavigationItem[] {
  return role ? navigationByRole[role] : [];
}

/** A section stays highlighted on its nested pages, e.g. a course inside "Курсы". */
export function isNavigationItemActive(item: NavigationItem, path: string): boolean {
  return path === item.path || path.startsWith(`${item.path}/`);
}

export function roleLabel(role: UserRole | null): string {
  if (role === "student") return "Ученик";
  if (role === "curator") return "Куратор";
  return "Администратор";
}
