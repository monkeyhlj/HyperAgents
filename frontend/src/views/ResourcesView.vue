<template>
  <div>
    <Card dis-hover>
      <template #title>Resources</template>
      <Tabs :value="activeTab" @on-click="switchTab">
        <TabPane label="Overview" name="overview" />
        <TabPane label="Agents" name="agents" />
        <TabPane label="Tools" name="tools" />
        <TabPane label="Skills" name="skills" />
        <TabPane label="MCPs" name="mcps" />
        <TabPane label="Knowledge" name="knowledge-bases" />
      </Tabs>
    </Card>

    <div class="mt16">
      <RouterView />
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute, useRouter, RouterView } from "vue-router";

const route = useRoute();
const router = useRouter();

const activeTab = computed(() => {
  const path = route.path;
  if (path.includes("/resources/agents")) return "agents";
  if (path.includes("/resources/tools")) return "tools";
  if (path.includes("/resources/skills")) return "skills";
  if (path.includes("/resources/mcps")) return "mcps";
  if (path.includes("/resources/knowledge-bases")) return "knowledge-bases";
  return "overview";
});

function switchTab(name) {
  const routeMap = {
    overview: "resources-overview",
    agents: "resources-agents",
    tools: "resources-tools",
    skills: "resources-skills",
    mcps: "resources-mcps",
    "knowledge-bases": "resources-knowledge-bases"
  };
  const target = routeMap[name];
  if (target) {
    router.push({ name: target });
  }
}
</script>
