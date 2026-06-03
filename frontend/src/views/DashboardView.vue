<template>
  <div>
    <Card class="hero-card" dis-hover>
      <h2>Welcome, {{ authState.user?.display_name || "Explorer" }}</h2>
      <p>
        HyperAgents combines project governance, registry, runtime, and memory into one testable workspace.
      </p>
      <Tag color="green">Project-first</Tag>
      <Tag color="blue">Provider-agnostic</Tag>
      <Tag color="cyan">Memory-ready</Tag>
    </Card>

    <Row :gutter="16" class="mt16">
      <i-col span="6" v-for="item in metrics" :key="item.label">
        <Card dis-hover>
          <p class="metric-label">{{ item.label }}</p>
          <p class="metric-value">{{ item.value }}</p>
        </Card>
      </i-col>
    </Row>

    <Card class="mt16" dis-hover>
      <template #title>Architecture Pulse</template>
      <Timeline>
        <TimelineItem color="green">Projects define visibility and ownership boundaries.</TimelineItem>
        <TimelineItem color="blue">Resources are loaded by project and executed via runtime.</TimelineItem>
        <TimelineItem color="cyan">Memory records support semantic retrieval and retry queue.</TimelineItem>
      </Timeline>
    </Card>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { authState } from "../stores/auth";

const metrics = computed(() => [
  { label: "Current User", value: authState.user?.username || "-" },
  { label: "Auth Status", value: authState.token ? "Active" : "Missing" },
  { label: "Frontend", value: "Vue 3 + View UI Plus" },
  { label: "Backend", value: "FastAPI v1 API" }
]);
</script>
