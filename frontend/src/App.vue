<template>
  <RouterView v-if="isLoginPage" />
  <div v-else class="app-root">
    <Layout class="app-layout">
      <Header class="app-header">
        <div class="brand-block">
          <h1>HyperAgents Control Panel</h1>
          <span>Project-first AgentOS workspace for runtime, registry and memory</span>
        </div>
        <div v-if="authState.user" class="user-block">
          <span class="hello">{{ authState.user.display_name }}</span>
          <Button size="small" ghost @click="logout">Logout</Button>
        </div>
      </Header>

      <Layout>
        <Sider hide-trigger collapsible :collapsed-width="78" v-model="collapsed" class="app-sider">
          <Menu :active-name="activeMenu" theme="dark" width="auto">
            <MenuItem name="dashboard" @click="goTo('/')">
              <Icon type="ios-planet" />
              <span>Dashboard</span>
            </MenuItem>
            <MenuItem name="projects" @click="goTo('/projects')">
              <Icon type="ios-folder-open" />
              <span>Projects</span>
            </MenuItem>
            <Submenu name="resources-group">
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
              <Icon type="ios-flask" />
              <span>Workbench</span>
            </MenuItem>
          </Menu>
        </Sider>

        <Content class="app-content">
          <RouterView />
        </Content>
      </Layout>
    </Layout>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter, RouterView } from "vue-router";
import { Message } from "view-ui-plus";
import { authState, clearAuth } from "./stores/auth";

const route = useRoute();
const router = useRouter();

const collapsed = ref(false);
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
  return "dashboard";
});

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
