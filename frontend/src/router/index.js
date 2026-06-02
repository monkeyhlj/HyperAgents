import { createRouter, createWebHistory } from "vue-router";
import DashboardView from "../views/DashboardView.vue";
import ProjectsView from "../views/ProjectsView.vue";
import ResourcesView from "../views/ResourcesView.vue";
import WorkbenchView from "../views/WorkbenchView.vue";

const routes = [
  { path: "/", name: "dashboard", component: DashboardView },
  { path: "/projects", name: "projects", component: ProjectsView },
  { path: "/resources", name: "resources", component: ResourcesView },
  { path: "/workbench", name: "workbench", component: WorkbenchView }
];

export default createRouter({
  history: createWebHistory(),
  routes
});
