import { createRouter, createWebHistory } from "vue-router";
import { isAuthenticated } from "../stores/auth";

const routes = [
  { path: "/login", name: "login", component: () => import("../views/LoginView.vue") },
  {
    path: "/",
    name: "dashboard",
    component: () => import("../views/DashboardView.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/projects",
    name: "projects",
    component: () => import("../views/ProjectsView.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/projects/:projectId",
    name: "project-detail",
    component: () => import("../views/ProjectDetailView.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/resources",
    name: "resources",
    component: () => import("../views/ResourcesView.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/workbench",
    name: "workbench",
    component: () => import("../views/WorkbenchView.vue"),
    meta: { requiresAuth: true }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !isAuthenticated()) {
    return { name: "login", query: { redirect: to.fullPath } };
  }
  if (to.name === "login" && isAuthenticated()) {
    return { name: "dashboard" };
  }
  return true;
});

export default router;
