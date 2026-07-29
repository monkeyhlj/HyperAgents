<template>
  <RouterView v-if="isLoginPage" />
  <div v-else class="app-shell">
    <Layout class="app-layout">
      <Sider hide-trigger collapsible :collapsed-width="76" v-model="collapsed" class="app-sider">
        <div class="sider-brand" :class="{ collapsed }">
          <div class="brand-mark">HA</div>
          <div class="brand-copy">
            <strong>HyperAgents</strong>
            <span>AgentOS Workspace</span>
          </div>
        </div>

        <Menu :active-name="menuActiveName" theme="dark" width="auto" class="app-menu">
          <MenuItem name="dashboard" @click="goTo('/')">
            <Icon type="ios-planet" />
            <span>Dashboard</span>
          </MenuItem>
          <MenuItem name="projects" @click="goTo('/projects')">
            <Icon type="ios-folder-open" />
            <span>Projects</span>
          </MenuItem>
          <Dropdown
            v-if="collapsed"
            class="collapsed-resource-dropdown"
            transfer
            trigger="hover"
            placement="right-start"
            @on-click="goTo"
          >
            <MenuItem name="resources-overview" @click="goTo('/resources/overview')">
              <Icon type="ios-cube" />
              <span>Resources</span>
            </MenuItem>
            <template #list>
              <DropdownMenu class="resource-flyout-menu">
                <DropdownItem name="/resources/overview" :class="{ active: activeMenu === 'resources-overview' }">Overview</DropdownItem>
                <DropdownItem name="/resources/agents" :class="{ active: activeMenu === 'resources-agents' }">Agents</DropdownItem>
                <DropdownItem name="/resources/tools" :class="{ active: activeMenu === 'resources-tools' }">Tools</DropdownItem>
                <DropdownItem name="/resources/skills" :class="{ active: activeMenu === 'resources-skills' }">Skills</DropdownItem>
                <DropdownItem name="/resources/mcps" :class="{ active: activeMenu === 'resources-mcps' }">MCPs</DropdownItem>
                <DropdownItem name="/resources/knowledge-bases" :class="{ active: activeMenu === 'resources-knowledge-bases' }">Knowledge</DropdownItem>
              </DropdownMenu>
            </template>
          </Dropdown>
          <Submenu v-else name="resources-group">
            <template #title>
              <Icon type="ios-cube" />
              <span>Resources</span>
            </template>
            <MenuItem name="resources-overview" @click="goTo('/resources/overview')">Overview</MenuItem>
            <MenuItem name="resources-agents" @click="goTo('/resources/agents')">Agents</MenuItem>
            <MenuItem name="resources-tools" @click="goTo('/resources/tools')">Tools</MenuItem>
            <MenuItem name="resources-skills" @click="goTo('/resources/skills')">Skills</MenuItem>
            <MenuItem name="resources-mcps" @click="goTo('/resources/mcps')">MCPs</MenuItem>
            <MenuItem name="resources-knowledge-bases" @click="goTo('/resources/knowledge-bases')">Knowledge</MenuItem>
          </Submenu>
          <MenuItem name="workflows" @click="goTo('/workflows')">
            <Icon type="ios-git-network" />
            <span>Workflows</span>
          </MenuItem>
          <MenuItem name="workbench" @click="goTo('/workbench')">
            <Icon type="ios-chatbubbles" />
            <span>Workbench</span>
          </MenuItem>
          <MenuItem name="my-files" @click="goTo('/my-files')">
            <Icon type="ios-folder" />
            <span>My Files</span>
          </MenuItem>
        </Menu>
      </Sider>

      <Layout class="main-layout">
        <Header class="app-header">
          <div class="header-left">
            <Button class="sider-toggle" size="small" shape="circle" @click="collapsed = !collapsed">
              <Icon :type="collapsed ? 'ios-arrow-forward' : 'ios-arrow-back'" />
            </Button>
            <div>
              <h1>{{ pageTitle }}</h1>
              <p>{{ pageSubtitle }}</p>
            </div>
          </div>
          <div v-if="authState.user" class="user-block">
            <div class="user-avatar">{{ userInitial }}</div>
            <div class="user-meta">
              <span>{{ authState.user.display_name }}</span>
              <small>{{ authState.user.username }}</small>
            </div>
            <Button size="small" @click="logout">Logout</Button>
          </div>
        </Header>

        <div v-if="openTabs.length" class="page-tabs-bar">
          <div class="page-tabs-scroll">
            <button
              v-for="tab in openTabs"
              :key="tab.path"
              type="button"
              class="page-tab"
              :class="{ active: tab.path === route.fullPath }"
              @click="activateTab(tab)"
            >
              <span>{{ tab.title }}</span>
              <Icon type="md-close" class="tab-close" @click.stop="closeTab(tab.path)" />
            </button>
          </div>
          <Dropdown trigger="click" placement="bottom-end" @on-click="handleTabCommand">
            <Button size="small">Tabs <Icon type="ios-arrow-down" /></Button>
            <template #list>
              <DropdownMenu>
                <DropdownItem name="close-current">Close Current</DropdownItem>
                <DropdownItem name="close-others">Close Others</DropdownItem>
                <DropdownItem name="close-all">Close All</DropdownItem>
              </DropdownMenu>
            </template>
          </Dropdown>
        </div>

        <Content class="app-content">
          <RouterView v-slot="{ Component, route: viewRoute }">
            <KeepAlive include="WorkbenchView,WorkflowDetailView">
              <component :is="Component" :key="viewRoute.meta.keepAlive ? (viewRoute.meta.keepAliveKey === 'fullPath' ? viewRoute.fullPath : viewRoute.name) : viewRoute.fullPath" />
            </KeepAlive>
          </RouterView>
        </Content>
      </Layout>
    </Layout>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter, RouterView } from "vue-router";
import { Message } from "view-ui-plus";
import { authState, clearAuth } from "./stores/auth";

const route = useRoute();
const router = useRouter();

const collapsed = ref(false);
const openTabs = ref([]);
const isLoginPage = computed(() => route.path.startsWith("/login"));

const activeMenu = computed(() => {
  if (route.path.startsWith("/projects")) return "projects";
  if (route.path.startsWith("/resources/agents")) return "resources-agents";
  if (route.path.startsWith("/resources/tools")) return "resources-tools";
  if (route.path.startsWith("/resources/skills")) return "resources-skills";
  if (route.path.startsWith("/resources/mcps")) return "resources-mcps";
  if (route.path.startsWith("/resources/knowledge-bases")) return "resources-knowledge-bases";
  if (route.path.startsWith("/resources")) return "resources-overview";
  if (route.path.startsWith("/workflows")) return "workflows";
  if (route.path.startsWith("/workbench")) return "workbench";
  if (route.path.startsWith("/my-files")) return "my-files";
  return "dashboard";
});
const menuActiveName = computed(() => {
  if (collapsed.value && activeMenu.value.startsWith("resources")) return "resources-overview";
  return activeMenu.value;
});

const pageTitle = computed(() => {
  const map = {
    dashboard: "Dashboard",
    projects: "Projects",
    "resources-overview": "Resources",
    "resources-agents": "Agents",
    "resources-tools": "Tools",
    "resources-skills": "Skills",
    "resources-mcps": "MCPs",
    "resources-knowledge-bases": "Knowledge",
    workflows: "Workflows",
    workbench: "Workbench",
    "my-files": "My Files"
  };
  return map[activeMenu.value] || "HyperAgents";
});

const pageSubtitle = computed(() => {
  if (activeMenu.value === "workbench") return "Test agents, skills, tools, MCPs, and runtime traces in one focused chat surface.";
  if (activeMenu.value.startsWith("resources")) return "Manage reusable capabilities and bind them to project agents.";
  if (activeMenu.value === "projects") return "Organize ownership, members, and runtime boundaries.";
  if (activeMenu.value === "my-files") return "Download generated artifacts and upload working files.";
  return "Project-first runtime control for agent resources and memory.";
});

const userInitial = computed(() => {
  const name = authState.user?.display_name || authState.user?.username || "U";
  return name.slice(0, 1).toUpperCase();
});

function routeTitle(targetRoute = route) {
  if (targetRoute.meta?.title) return String(targetRoute.meta.title);
  const map = {
    dashboard: "Dashboard",
    projects: "Projects",
    "project-detail": "Project Detail",
    "resources-overview": "Resources",
    "resources-agents": "Agents",
    "resources-tools": "Tools",
    "resources-skills": "Skills",
    "resources-mcps": "MCPs",
    "resources-knowledge-bases": "Knowledge",
    workflows: "Workflows",
    workbench: "Workbench",
    "my-files": "My Files"
  };
  return map[targetRoute.name] || pageTitle.value || "Page";
}

function upsertCurrentTab(targetRoute = route) {
  if (targetRoute.path.startsWith("/login")) return;
  const nextTab = {
    path: targetRoute.fullPath,
    name: targetRoute.name,
    title: routeTitle(targetRoute)
  };
  const existingIndex = openTabs.value.findIndex((item) => item.path === nextTab.path);
  if (existingIndex >= 0) {
    openTabs.value.splice(existingIndex, 1, nextTab);
  } else {
    openTabs.value.push(nextTab);
  }
}

function activateTab(tab) {
  if (tab.path !== route.fullPath) {
    router.push(tab.path);
  }
}

function closeTab(path) {
  const wasCurrent = path === route.fullPath;
  const currentIndex = openTabs.value.findIndex((item) => item.path === path);
  const remaining = openTabs.value.filter((item) => item.path !== path);
  openTabs.value = remaining;

  if (!wasCurrent) return;

  if (remaining.length > 0) {
    const nextIndex = Math.max(0, Math.min(currentIndex, remaining.length - 1));
    router.push(remaining[nextIndex].path);
    return;
  }

  if (route.path !== "/") {
    router.push("/");
  } else {
    upsertCurrentTab(route);
  }
}

function handleTabCommand(command) {
  if (command === "close-current") {
    closeTab(route.fullPath);
    return;
  }
  if (command === "close-others") {
    openTabs.value = openTabs.value.filter((item) => item.path === route.fullPath);
    if (!openTabs.value.length) upsertCurrentTab(route);
    return;
  }
  if (command === "close-all") {
    openTabs.value = [];
    if (route.path !== "/") {
      router.push("/");
    } else {
      upsertCurrentTab(route);
    }
  }
}

watch(
  () => route.fullPath,
  () => upsertCurrentTab(route),
  { immediate: true }
);
function goTo(path) {
  if (route.path !== path) {
    router.push(path);
  }
}

async function logout() {
  clearAuth();
  Message.info("Logged out");
  await router.replace("/login");
}
</script>