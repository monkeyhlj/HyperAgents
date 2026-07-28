<template>
  <div class="page-shell dashboard-page">
    <section class="page-hero dashboard-hero">
      <div>
        <p class="eyebrow">Control Plane</p>
        <h1>Welcome, {{ authState.user?.display_name || "Explorer" }}</h1>
        <p>HyperAgents brings projects, resources, runtime traces, memory, and generated files into a single operator workspace.</p>
      </div>
      <div class="hero-tags">
        <Tag color="green">Project-first</Tag>
        <Tag color="blue">Provider-agnostic</Tag>
        <Tag color="cyan">Memory-ready</Tag>
      </div>
    </section>

    <Row :gutter="16">
      <i-col :xs="24" :sm="12" :lg="6" v-for="item in metrics" :key="item.label">
        <Card dis-hover class="metric-card">
          <p class="metric-label">{{ item.label }}</p>
          <p class="metric-value">{{ item.value }}</p>
        </Card>
      </i-col>
    </Row>

    <Row :gutter="16">
      <i-col :xs="24" :lg="10">
        <Card dis-hover>
          <template #title>Architecture Pulse</template>
          <Timeline>
            <TimelineItem color="green">Projects define visibility and ownership boundaries.</TimelineItem>
            <TimelineItem color="blue">Resources are loaded by project and executed through runtime.</TimelineItem>
            <TimelineItem color="cyan">Memory and files make agent work inspectable and repeatable.</TimelineItem>
          </Timeline>
        </Card>
      </i-col>
      <i-col :xs="24" :lg="14">
        <Card dis-hover>
          <template #title>System Default Resource Templates</template>
          <Table :columns="templateColumns" :data="pagedDefaultResources" stripe size="small" />
          <Page
            v-if="defaultResources.length > pageSize"
            class="table-pagination"
            :total="defaultResources.length"
            :current="templatePage"
            :page-size="pageSize"
            show-total
            @on-change="templatePage = $event"
          />
          <div v-if="defaultResources.length === 0" class="empty-state">No default templates loaded.</div>
        </Card>
      </i-col>
    </Row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { authState } from "../stores/auth";
import { api } from "../services/api";

const defaultResources = ref([]);
const templatePage = ref(1);
const pageSize = 10;

const metrics = computed(() => [
  { label: "Current User", value: authState.user?.username || "-" },
  { label: "Auth Status", value: authState.token ? "Active" : "Missing" },
  { label: "Frontend", value: "Vue 3" },
  { label: "Backend", value: "FastAPI" }
]);

const pagedDefaultResources = computed(() => {
  const start = (templatePage.value - 1) * pageSize;
  return defaultResources.value.slice(start, start + pageSize);
});

const templateColumns = [
  { title: "Kind", key: "kind", width: 130 },
  { title: "Name", key: "name", minWidth: 180 },
  { title: "Provider", key: "model_provider", minWidth: 140 },
  { title: "Model", key: "model_name", minWidth: 160 }
];

onMounted(async () => {
  try {
    defaultResources.value = await api.listDefaultResources();
    templatePage.value = 1;
  } catch {
    defaultResources.value = [];
  }
});
</script>

<style scoped>
.dashboard-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
}

.dashboard-hero h1 {
  margin: 0;
  font-size: clamp(28px, 4vw, 44px);
  line-height: 1.05;
}

.hero-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.metric-card {
  min-height: 112px;
}

@media (max-width: 760px) {
  .dashboard-hero {
    display: grid;
  }
  .hero-tags {
    justify-content: flex-start;
  }
}
</style>