<template>
  <div class="page-shell dashboard-page">
    <section class="page-hero dashboard-hero">
      <div class="hero-copy">
        <p class="eyebrow">Control Plane</p>
        <h1>Welcome, {{ authState.user?.display_name || authState.user?.username || "Explorer" }}</h1>
        <p>HyperAgents brings projects, reusable resources, workflow runs, knowledge, and generated files into a single operator workspace.</p>
        <div class="hero-actions">
          <Button type="primary" @click="goRoute('workbench')">
            <Icon type="ios-chatbubbles" />
            Open Workbench
          </Button>
          <Button @click="goRoute('resources-agents-create')">
            <Icon type="md-add" />
            Create Agent
          </Button>
          <Button @click="refreshDashboard" :loading="loading">
            <Icon type="md-refresh" />
            Refresh
          </Button>
        </div>
      </div>
      <div class="hero-status">
        <div class="status-card">
          <span>Signed in as</span>
          <strong>{{ authState.user?.username || "-" }}</strong>
        </div>
        <div class="status-card">
          <span>Auth</span>
          <strong>{{ authState.token ? "Active" : "Missing" }}</strong>
        </div>
        <div class="hero-tags">
          <Tag color="green">Project-first</Tag>
          <Tag color="blue">Provider-agnostic</Tag>
          <Tag color="cyan">Memory-ready</Tag>
        </div>
      </div>
    </section>

    <Row :gutter="16" class="dashboard-row">
      <i-col :xs="24" :sm="12" :lg="6" v-for="item in metrics" :key="item.label">
        <Card dis-hover class="metric-card">
          <div class="metric-icon" :class="item.tone">
            <Icon :type="item.icon" />
          </div>
          <div>
            <p class="metric-label">{{ item.label }}</p>
            <p class="metric-value">{{ item.value }}</p>
            <p class="metric-note">{{ item.note }}</p>
          </div>
        </Card>
      </i-col>
    </Row>

    <Row :gutter="16" class="dashboard-row">
      <i-col :xs="24" :lg="16">
        <Card dis-hover class="section-card starter-template-card">
          <template #title>
            <div class="card-title-row">
              <div>
                <span>Starter Templates</span>
                <p>Use system presets to create your first resource faster.</p>
              </div>
              <Tag color="geekblue">System Presets</Tag>
            </div>
          </template>
          <div class="template-summary">
            <div>
              <span>Templates</span>
              <strong>{{ defaultResources.length }}</strong>
            </div>
            <div>
              <span>Agent presets</span>
              <strong>{{ defaultAgentTemplateCount }}</strong>
            </div>
            <div>
              <span>Providers</span>
              <strong>{{ providerTemplateCount }}</strong>
            </div>
          </div>
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

      <i-col :xs="24" :lg="8">
        <Card dis-hover class="section-card quick-action-card">
          <template #title>Quick Actions</template>
          <div class="quick-actions">
            <Button v-for="item in quickActions" :key="item.label" long @click="goRoute(item.route)">
              <Icon :type="item.icon" />
              {{ item.label }}
            </Button>
          </div>
        </Card>
      </i-col>
    </Row>

    <Row :gutter="16" class="dashboard-row">
      <i-col :xs="24">
        <Card dis-hover class="section-card">
          <template #title>
            <div class="card-title-row">
              <span>Capability Map</span>
              <Tag color="cyan">{{ ownedResources.length }} resources</Tag>
            </div>
          </template>
          <div class="capability-grid compact">
            <button v-for="item in capabilityCards" :key="item.kind" class="capability-card" @click="goRoute(item.route)">
              <span class="capability-icon" :class="item.tone"><Icon :type="item.icon" /></span>
              <span class="capability-copy">
                <strong>{{ item.label }}</strong>
                <small>{{ item.description }}</small>
              </span>
              <span class="capability-count">{{ item.count }}</span>
            </button>
          </div>
        </Card>
      </i-col>
    </Row>

    <Row :gutter="16" class="dashboard-row">
      <i-col :xs="24" :lg="10">
        <Card dis-hover class="section-card">
          <template #title>Architecture Pulse</template>
          <Timeline>
            <TimelineItem color="green">Projects define visibility and ownership boundaries.</TimelineItem>
            <TimelineItem color="blue">Resources are loaded by project and executed through runtime.</TimelineItem>
            <TimelineItem color="cyan">Workbench keeps agent tests, messages, runs, and events inspectable.</TimelineItem>
            <TimelineItem color="purple">Workflows orchestrate project agents and preserve run history.</TimelineItem>
            <TimelineItem color="orange">My Files keeps uploads and generated artifacts downloadable.</TimelineItem>
          </Timeline>
        </Card>
      </i-col>

      <i-col :xs="24" :lg="14">
        <Card dis-hover class="section-card">
          <template #title>
            <div class="card-title-row">
              <span>Recent Projects</span>
              <Button size="small" @click="goRoute('projects')">View All</Button>
            </div>
          </template>
          <Table :columns="projectColumns" :data="recentProjects" stripe size="small" />
          <div v-if="recentProjects.length === 0" class="empty-state">No projects yet.</div>
        </Card>
      </i-col>
    </Row>

    <Row :gutter="16" class="dashboard-row">
      <i-col :xs="24" :lg="10">
        <Card dis-hover class="section-card">
          <template #title>My Files Snapshot</template>
          <div class="file-summary">
            <div>
              <span>Total files</span>
              <strong>{{ files.length }}</strong>
            </div>
            <div>
              <span>Generated</span>
              <strong>{{ generatedFileCount }}</strong>
            </div>
            <div>
              <span>Uploads</span>
              <strong>{{ uploadedFileCount }}</strong>
            </div>
          </div>
          <div class="recent-files">
            <div v-for="file in recentFiles" :key="file.path" class="recent-file-row">
              <Icon type="md-document" />
              <span>{{ file.path }}</span>
            </div>
            <div v-if="recentFiles.length === 0" class="empty-state compact">No files yet.</div>
          </div>
        </Card>
      </i-col>
    </Row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { Message } from "view-ui-plus";
import { authState } from "../stores/auth";
import { api } from "../services/api";

const router = useRouter();

const projects = ref([]);
const ownedResources = ref([]);
const defaultResources = ref([]);
const files = ref([]);
const loading = ref(false);
const templatePage = ref(1);
const pageSize = 10;

const resourceKindLabels = {
  agent: "Agents",
  tool: "Tools",
  skill: "Skills",
  mcp: "MCPs",
  knowledge_base: "Knowledge",
  workflow: "Workflows"
};

const capabilityMeta = [
  { kind: "agent", label: "Agents", route: "resources-agents", icon: "ios-planet", tone: "tone-teal", description: "Conversation and runtime actors" },
  { kind: "tool", label: "Tools", route: "resources-tools", icon: "md-construct", tone: "tone-blue", description: "Deterministic code helpers" },
  { kind: "skill", label: "Skills", route: "resources-skills", icon: "md-school", tone: "tone-violet", description: "Reusable how-to packages" },
  { kind: "mcp", label: "MCPs", route: "resources-mcps", icon: "md-git-network", tone: "tone-cyan", description: "External tool integrations" },
  { kind: "knowledge_base", label: "Knowledge", route: "resources-knowledge-bases", icon: "ios-book", tone: "tone-amber", description: "Documents and retrieval" },
  { kind: "workflow", label: "Workflows", route: "workflows", icon: "md-share", tone: "tone-rose", description: "Multi-agent orchestration" }
];

const quickActions = [
  { label: "Open Workbench", route: "workbench", icon: "ios-chatbubbles" },
  { label: "Create Agent", route: "resources-agents-create", icon: "ios-planet" },
  { label: "Upload Knowledge", route: "resources-knowledge-bases", icon: "ios-book" },
  { label: "Create Workflow", route: "workflows-create", icon: "md-share" },
  { label: "Open My Files", route: "my-files", icon: "ios-folder" }
];

const ownedByKind = computed(() => {
  const counts = Object.fromEntries(Object.keys(resourceKindLabels).map((kind) => [kind, 0]));
  ownedResources.value.forEach((item) => {
    if (counts[item.kind] !== undefined) {
      counts[item.kind] += 1;
    }
  });
  return counts;
});

const metrics = computed(() => [
  { label: "Projects", value: projects.value.length, note: "visible to current user", icon: "ios-folder", tone: "tone-blue" },
  { label: "Agents", value: ownedByKind.value.agent || 0, note: "ready for Workbench", icon: "ios-planet", tone: "tone-teal" },
  { label: "Resources", value: ownedResources.value.length, note: "tools, skills, MCPs, knowledge, workflows", icon: "md-cube", tone: "tone-violet" },
  { label: "Files", value: files.value.length, note: "uploads and generated artifacts", icon: "md-document", tone: "tone-amber" }
]);

const capabilityCards = computed(() => capabilityMeta.map((item) => ({
  ...item,
  count: ownedByKind.value[item.kind] || 0
})));

const recentProjects = computed(() => {
  return [...projects.value]
    .sort((a, b) => new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0))
    .slice(0, 5);
});

const defaultAgentTemplateCount = computed(() => defaultResources.value.filter((item) => item.kind === "agent").length);
const providerTemplateCount = computed(() => new Set(defaultResources.value.map((item) => item.model_provider).filter(Boolean)).size);
const generatedFileCount = computed(() => files.value.filter((item) => item.path?.startsWith("generated/")).length);
const uploadedFileCount = computed(() => files.value.filter((item) => item.path?.startsWith("uploads/")).length);
const recentFiles = computed(() => files.value.slice(0, 5));

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

const projectColumns = [
  { title: "Name", key: "name", minWidth: 160, ellipsis: true },
  { title: "Owner", key: "owner_name", minWidth: 130, ellipsis: true },
  { title: "Members", render: (_, { row }) => row.members?.length || 0, width: 100 },
  { title: "Updated", render: (_, { row }) => formatDate(row.updated_at || row.created_at), minWidth: 150 }
];

function formatDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return date.toLocaleString();
}

function goRoute(name) {
  router.push({ name });
}

async function refreshDashboard() {
  loading.value = true;
  try {
    const [projectList, resourceList, templateList, fileList] = await Promise.all([
      api.listProjects(),
      api.listOwnedResources(),
      api.listDefaultResources(),
      api.listMyFiles()
    ]);
    projects.value = projectList || [];
    ownedResources.value = resourceList || [];
    defaultResources.value = templateList || [];
    files.value = fileList.files || [];
    templatePage.value = 1;
  } catch (error) {
    Message.error(error.message || "Load dashboard failed");
  } finally {
    loading.value = false;
  }
}

onMounted(refreshDashboard);
</script>

<style scoped>
.dashboard-page {
  display: grid;
  gap: 18px;
}

.dashboard-hero {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 22px;
}

.hero-copy {
  max-width: 820px;
}

.dashboard-hero h1 {
  margin: 0;
  font-size: clamp(30px, 4vw, 48px);
  line-height: 1.04;
}

.dashboard-hero p:not(.eyebrow) {
  max-width: 760px;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 22px;
}

.hero-status {
  display: grid;
  gap: 10px;
  min-width: 240px;
  align-content: end;
}

.status-card {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid rgba(15, 118, 110, 0.18);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.78);
}

.status-card span,
.metric-label,
.metric-note,
.capability-copy small,
.file-summary span,
.recent-file-row,
.template-summary span {
  color: #64748b;
}

.status-card strong {
  color: #142033;
}

.hero-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.dashboard-row {
  row-gap: 16px;
}

.metric-card {
  min-height: 132px;
  display: flex;
  gap: 14px;
  align-items: center;
}

.metric-icon,
.capability-icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  color: #ffffff;
  box-shadow: 0 12px 24px rgba(21, 36, 61, 0.16);
}

.metric-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  font-size: 24px;
}

.metric-label {
  margin: 0 0 6px;
  font-weight: 700;
}

.metric-value {
  margin: 0;
  color: #121b2f;
  font-size: 30px;
  font-weight: 900;
  line-height: 1;
}

.metric-note {
  margin: 8px 0 0;
  line-height: 1.35;
}

.section-card {
  height: 100%;
}

.starter-template-card :deep(.ivu-card-head) {
  border-bottom-color: #cfe1f4;
  background: linear-gradient(135deg, #f6fbff 0%, #eef6ff 100%);
}

.starter-template-card .card-title-row p {
  margin: 5px 0 0;
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
}

.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.template-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.template-summary div {
  display: grid;
  gap: 5px;
  padding: 13px 14px;
  border: 1px solid #d8e7f5;
  border-radius: 8px;
  background: #ffffff;
}

.template-summary strong {
  color: #0f172a;
  font-size: 26px;
  line-height: 1;
}

.quick-action-card {
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.capability-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.capability-grid.compact {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.capability-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  min-height: 82px;
  padding: 13px;
  border: 1px solid #dbe7f3;
  border-radius: 8px;
  background: #ffffff;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
}

.capability-card:hover {
  border-color: #0f766e;
  box-shadow: 0 14px 34px rgba(15, 118, 110, 0.12);
  transform: translateY(-1px);
}

.capability-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  font-size: 22px;
}

.capability-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.capability-copy strong,
.capability-copy small,
.recent-file-row span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.capability-copy strong {
  color: #172033;
}

.capability-count {
  min-width: 34px;
  padding: 5px 9px;
  border-radius: 999px;
  background: #eef4fb;
  color: #24324a;
  font-weight: 900;
  text-align: center;
}

.quick-actions {
  display: grid;
  gap: 10px;
}

.file-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.file-summary div {
  display: grid;
  gap: 5px;
  padding: 12px;
  border-radius: 8px;
  background: #f6f9fd;
  border: 1px solid #dfe8f2;
}

.file-summary strong {
  color: #121b2f;
  font-size: 24px;
}

.recent-files {
  display: grid;
  gap: 8px;
}

.recent-file-row {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  min-width: 0;
}

.empty-state.compact {
  padding: 12px;
}

.tone-blue { background: linear-gradient(135deg, #2563eb, #0891b2); }
.tone-teal { background: linear-gradient(135deg, #0f766e, #14b8a6); }
.tone-violet { background: linear-gradient(135deg, #6d28d9, #7c3aed); }
.tone-cyan { background: linear-gradient(135deg, #0284c7, #06b6d4); }
.tone-amber { background: linear-gradient(135deg, #b45309, #f59e0b); }
.tone-rose { background: linear-gradient(135deg, #be123c, #f43f5e); }

@media (max-width: 980px) {
  .dashboard-hero {
    display: grid;
  }

  .hero-status {
    min-width: 0;
  }

  .hero-tags {
    justify-content: flex-start;
  }

  .capability-grid,
  .capability-grid.compact,
  .file-summary,
  .template-summary {
    grid-template-columns: 1fr;
  }
}
</style>