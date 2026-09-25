export const WORKSPACE_SECTION_ROUTES = {
  studentCourses: { name: "student-courses", path: "/student/courses" },
  studentSkills: { name: "student-skills", path: "/student/skills" },
  studentHistory: { name: "student-history", path: "/student/history" },
  studentProgress: { name: "student-progress", path: "/student/progress" },
  curatorLearners: { name: "curator-learners", path: "/curator/learners" },
  curatorReviews: { name: "curator-reviews", path: "/curator/reviews" },
  curatorQuestions: { name: "curator-questions", path: "/curator/questions" },
  adminCourses: { name: "admin-courses", path: "/admin/courses" },
  adminBuilder: { name: "admin-builder", path: "/admin/builder" },
  adminGroups: { name: "admin-groups", path: "/admin/groups" },
  adminUsers: { name: "admin-users", path: "/admin/users" },
} as const;
