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
    redirect: { name: "resources-overview" },
    meta: { requiresAuth: true }
  },
  {
    path: "/resources/overview",
    name: "resources-overview",
    component: () => import("../views/resources/ResourceOwnedListView.vue"),
    meta: { requiresAuth: true, section: "resources", title: "My Resources" }
  },
  {
    path: "/resources/agents",
    name: "resources-agents",
    component: () => import("../views/resources/ResourceOwnedListView.vue"),
    meta: { requiresAuth: true, section: "resources", kind: "agent", title: "Agents", createRoute: "resources-agents-create" }
  },
  {
    path: "/resources/tools",
    name: "resources-tools",
    component: () => import("../views/resources/ResourceOwnedListView.vue"),
    meta: { requiresAuth: true, section: "resources", kind: "tool", title: "Tools", createRoute: "resources-tools-create" }
  },
  {
    path: "/resources/skills",
    name: "resources-skills",
    component: () => import("../views/resources/ResourceOwnedListView.vue"),
    meta: { requiresAuth: true, section: "resources", kind: "skill", title: "Skills", createRoute: "resources-skills-create" }
  },
  {
    path: "/resources/mcps",
    name: "resources-mcps",
    component: () => import("../views/resources/ResourceOwnedListView.vue"),
    meta: { requiresAuth: true, section: "resources", kind: "mcp", title: "MCPs", createRoute: "resources-mcps-create" }
  },
  {
    path: "/resources/knowledge-bases",
    name: "resources-knowledge-bases",
    component: () => import("../views/resources/ResourceOwnedListView.vue"),
    meta: {
      requiresAuth: true,
      section: "resources",
      kind: "knowledge_base",
      title: "Knowledge Bases",
      createRoute: "resources-knowledge-bases-create"
    }
  },
  {
    path: "/resources/agents/create",
    name: "resources-agents-create",
    component: () => import("../views/resources/ResourceCreateView.vue"),
    meta: { requiresAuth: true, kind: "agent", backRoute: "resources-agents", title: "Create Agent" }
  },
  {
    path: "/resources/agents/:resourceId/edit",
    name: "resources-agents-edit",
    component: () => import("../views/resources/ResourceCreateView.vue"),
    meta: { requiresAuth: true, kind: "agent", backRoute: "resources-agents", title: "Edit Agent", mode: "edit" }
  },
  {
    path: "/resources/tools/create",
    name: "resources-tools-create",
    component: () => import("../views/resources/ResourceCreateView.vue"),
    meta: { requiresAuth: true, kind: "tool", backRoute: "resources-tools", title: "Create Tool" }
  },
  {
    path: "/resources/tools/:resourceId/edit",
    name: "resources-tools-edit",
    component: () => import("../views/resources/ResourceCreateView.vue"),
    meta: { requiresAuth: true, kind: "tool", backRoute: "resources-tools", title: "Edit Tool", mode: "edit" }
  },
  {
    path: "/resources/skills/create",
    name: "resources-skills-create",
    component: () => import("../views/resources/ResourceCreateView.vue"),
    meta: { requiresAuth: true, kind: "skill", backRoute: "resources-skills", title: "Create Skill" }
  },
  {
    path: "/resources/skills/:resourceId/edit",
    name: "resources-skills-edit",
    component: () => import("../views/resources/ResourceCreateView.vue"),
    meta: { requiresAuth: true, kind: "skill", backRoute: "resources-skills", title: "Edit Skill", mode: "edit" }
  },
  {
    path: "/resources/mcps/create",
    name: "resources-mcps-create",
    component: () => import("../views/resources/ResourceCreateView.vue"),
    meta: { requiresAuth: true, kind: "mcp", backRoute: "resources-mcps", title: "Create MCP" }
  },
  {
    path: "/resources/mcps/:resourceId/edit",
    name: "resources-mcps-edit",
    component: () => import("../views/resources/ResourceCreateView.vue"),
    meta: { requiresAuth: true, kind: "mcp", backRoute: "resources-mcps", title: "Edit MCP", mode: "edit" }
  },
  {
    path: "/resources/knowledge-bases/create",
    name: "resources-knowledge-bases-create",
    component: () => import("../views/resources/ResourceCreateView.vue"),
    meta: {
      requiresAuth: true,
      kind: "knowledge_base",
      backRoute: "resources-knowledge-bases",
      title: "Create Knowledge Base"
    }
  },
  {
    path: "/resources/knowledge-bases/:resourceId/edit",
    name: "resources-knowledge-bases-edit",
    component: () => import("../views/resources/ResourceCreateView.vue"),
    meta: {
      requiresAuth: true,
      kind: "knowledge_base",
      backRoute: "resources-knowledge-bases",
      title: "Edit Knowledge Base",
      mode: "edit"
    }
  },
  {
    path: "/workflows",
    name: "workflows",
    component: () => import("../views/resources/ResourceOwnedListView.vue"),
    meta: {
      requiresAuth: true,
      section: "workflows",
      kind: "workflow",
      title: "Workflows",
      createRoute: "workflows-create"
    }
  },
  {
    path: "/workflows/create",
    name: "workflows-create",
    component: () => import("../views/resources/ResourceCreateView.vue"),
    meta: {
      requiresAuth: true,
      kind: "workflow",
      backRoute: "workflows",
      title: "Create Workflow"
    }
  },
  {
    path: "/workflows/:resourceId/edit",
    name: "workflows-edit",
    component: () => import("../views/resources/ResourceCreateView.vue"),
    meta: {
      requiresAuth: true,
      kind: "workflow",
      backRoute: "workflows",
      title: "Edit Workflow",
      mode: "edit"
    }
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
