<template>
  <div class="page-shell">
    <Card dis-hover>
      <template #title>
        <Space>
          <span>{{ pageTitle }}</span>
          <Button v-if="createRoute" type="primary" size="small" @click="goCreate">Add {{ kindLabel }}</Button>
          <Button size="small" :loading="loading" @click="loadData">Refresh</Button>
        </Space>
      </template>

      <Form inline>
        <FormItem>
          <Input v-model="queryText" clearable placeholder="Search resource name/id/project" style="width: 280px" />
        </FormItem>
        <FormItem>
          <Input v-model="projectQuery" clearable placeholder="Search project name" style="width: 220px" />
        </FormItem>
        <FormItem>
          <Button @click="loadData" :loading="loading">Search</Button>
        </FormItem>
        <FormItem>
          <Tag color="cyan">Total: {{ resources.length }}</Tag>
        </FormItem>
      </Form>

      <Table :columns="columns" :data="pagedResources" stripe>
        <template #project="{ row }">
          <div class="project-cell">
            <Tag color="gold">{{ row.project_name || '-' }}</Tag>
            <span>{{ row.project_id }}</span>
          </div>
        </template>
        <template #toolRuntime="{ row }">
          {{ toolConfig(row).runtime || '-' }}
        </template>
        <template #toolFunction="{ row }">
          {{ toolConfig(row).entrypoint || '-' }}
        </template>
        <template #toolShared="{ row }">
          <Tag :color="toolConfig(row).shared_in_project === false ? 'default' : 'green'">
            {{ toolConfig(row).shared_in_project === false ? 'false' : 'true' }}
          </Tag>
        </template>
        <template #mcpTransport="{ row }">
          {{ mcpConfig(row).transport || "streamable_http" }}
        </template>
        <template #mcpEndpoint="{ row }">
          <span v-if="mcpConfig(row).transport === 'stdio'">{{ mcpConfig(row).command || '-' }}</span>
          <span v-else>{{ mcpConfig(row).endpoint_url || '-' }}</span>
        </template>
        <template #mcpLastProbe="{ row }">
          <Tag v-if="row._mcp_probe?.ok" color="green">ok</Tag>
          <Tag v-else-if="row._mcp_probe" color="red">failed</Tag>
          <Tag v-else color="default">untested</Tag>
        </template>
        <template #action="{ row }">
          <Space>
            <Button size="small" @click="openDetail(row)">{{ detailActionLabel }}</Button>
            <Button
              v-if="resourceKind === 'knowledge_base'"
              size="small"
              type="primary"
              ghost
              @click="openDocuments(row)"
            >
              Documents
            </Button>
            <Button
              v-if="resourceKind === 'mcp'"
              size="small"
              :loading="probingById[row.id] === true"
              @click="probeMcp(row)"
            >
              Test
            </Button>
            <Button size="small" type="primary" ghost @click="openEditPage(row)">Edit</Button>
            <Button size="small" type="error" ghost @click="openDelete(row)">Delete</Button>
          </Space>
        </template>
      </Table>
      <Page
        v-if="resources.length > pageSize"
        class="table-pagination"
        :total="resources.length"
        :current="resourcePage"
        :page-size="pageSize"
        show-total
        @on-change="resourcePage = $event"
      />
    </Card>

    <Drawer v-model="showDetail" :title="`Resource Detail - ${current?.name || ''}`" width="560">
      <div v-if="current" class="resource-detail-shell">
        <section class="resource-detail-hero">
          <div class="resource-kind-icon" :class="kindTone(current.kind)">
            <Icon :type="kindIcon(current.kind)" />
          </div>
          <div class="resource-detail-heading">
            <div class="resource-detail-title-row">
              <h2>{{ current.name || "Untitled resource" }}</h2>
              <Tag :color="visibilityColor(current.visibility)">{{ current.visibility || "private" }}</Tag>
            </div>
            <p>{{ current.description || resourceKindHint(current.kind) }}</p>
            <div class="resource-detail-tags">
              <Tag color="blue">{{ kindDisplay(current.kind) }}</Tag>
              <Tag color="gold">{{ current.project_name || "No project name" }}</Tag>
              <Tag color="default">ID {{ shortId(current.id) }}</Tag>
            </div>
          </div>
        </section>

        <div class="detail-action-row">
          <Button size="small" type="primary" ghost @click="openEditPage(current)">Edit Resource</Button>
          <Button
            v-if="current.kind === 'knowledge_base'"
            size="small"
            type="primary"
            ghost
            @click="openDocuments(current)"
          >
            Documents
          </Button>
          <Button
            v-if="current.kind === 'skill'"
            size="small"
            type="primary"
            ghost
            @click="openSkillDetail(current)"
          >
            Manage Skill
          </Button>
          <Button
            v-if="current.kind === 'workflow'"
            size="small"
            type="primary"
            ghost
            @click="openWorkflowDetail(current)"
          >
            Test Workflow
          </Button>
          <Button
            v-if="current.kind === 'mcp'"
            size="small"
            :loading="probingById[current.id] === true"
            @click="probeMcp(current)"
          >
            Test MCP
          </Button>
        </div>

        <section class="detail-section">
          <h3>Overview</h3>
          <div class="detail-grid">
            <div class="detail-tile">
              <span>Resource ID</span>
              <strong class="mono-value">{{ current.id }}</strong>
            </div>
            <div class="detail-tile">
              <span>Project</span>
              <strong>{{ current.project_name || "-" }}</strong>
              <small class="mono-value">{{ current.project_id || "-" }}</small>
            </div>
            <div class="detail-tile">
              <span>Kind</span>
              <strong>{{ kindDisplay(current.kind) }}</strong>
            </div>
            <div class="detail-tile">
              <span>Visibility</span>
              <strong>{{ current.visibility || "private" }}</strong>
            </div>
          </div>
        </section>

        <section class="detail-section">
          <h3>{{ kindDisplay(current.kind) }} Settings</h3>
          <div class="detail-field-list">
            <div v-for="field in detailFields(current)" :key="field.label" class="detail-field-row">
              <span>{{ field.label }}</span>
              <strong>{{ field.value }}</strong>
            </div>
          </div>
        </section>

        <section v-if="current.kind === 'agent'" class="detail-section">
          <h3>Bound & Related Resources</h3>
          <div class="binding-groups">
            <div v-for="group in bindingGroups(current)" :key="group.key" class="binding-group">
              <div class="binding-group-title">
                <span>{{ group.label }}</span>
                <Tag :color="group.color">{{ group.items.length }}</Tag>
              </div>
              <div v-if="group.items.length" class="binding-resource-list">
                <div v-for="item in group.items" :key="item.id" class="binding-resource-item">
                  <div>
                    <strong>{{ item.name || item.id }}</strong>
                    <span>{{ bindingItemMeta(item, group) }}</span>
                  </div>
                  <Tag :color="group.color">{{ shortId(item.id) }}</Tag>
                </div>
              </div>
              <p v-else>{{ group.emptyText }}</p>
            </div>
          </div>
        </section>

        <section class="detail-section">
          <h3>Description</h3>
          <p class="detail-description">{{ current.description || "No description has been provided yet." }}</p>
        </section>

        <section class="detail-section">
          <div class="section-title-row">
            <h3>Config JSON</h3>
            <Tag color="default">read only</Tag>
          </div>
          <pre class="detail-config-json">{{ prettyConfig(current) }}</pre>
        </section>
      </div>
    </Drawer>
    <Modal v-model="showDelete" title="Delete Resource" :mask-closable="false">
      <p v-if="current">Confirm delete resource: <strong>{{ current.name }}</strong> ?</p>
      <p>This action cannot be undone.</p>
      <template #footer>
        <Button @click="showDelete = false">Cancel</Button>
        <Button type="error" :loading="deleting" @click="confirmDelete">Delete</Button>
      </template>
    </Modal>

  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Message } from "view-ui-plus";
import { api } from "../../services/api";

const route = useRoute();
const router = useRouter();

const resources = ref([]);
const resourcePage = ref(1);
const pageSize = 10;
const loading = ref(false);
const deleting = ref(false);
const probingById = ref({});
const queryText = ref("");
const projectQuery = ref("");

const showDetail = ref(false);
const showDelete = ref(false);
const current = ref(null);

const pageTitle = computed(() => route.meta.title || "Resources");
const resourceKind = computed(() => route.meta.kind || null);
const createRoute = computed(() => route.meta.createRoute || null);
const showModelFields = computed(() => resourceKind.value === "agent");
const pagedResources = computed(() => {
  const start = (resourcePage.value - 1) * pageSize;
  return resources.value.slice(start, start + pageSize);
});

const kindLabel = computed(() => {
  const map = {
    agent: "Agent",
    tool: "Tool",
    skill: "Skill",
    mcp: "MCP",
    knowledge_base: "Knowledge Base",
    workflow: "Workflow"
  };
  return map[resourceKind.value] || "Resource";
});

const detailActionLabel = computed(() => {
  if (resourceKind.value === "skill") return "Manage";
  if (resourceKind.value === "workflow") return "Test";
  return "Detail";
});
const columns = computed(() => {
  if (resourceKind.value === "tool") {
    return [
      { title: "Kind", key: "kind", width: 100 },
      { title: "Name", key: "name", minWidth: 180 },
      { title: "Project", slot: "project", minWidth: 220 },
      { title: "Visibility", key: "visibility", width: 120 },
      { title: "Runtime", slot: "toolRuntime", width: 120 },
      { title: "Function", slot: "toolFunction", minWidth: 150 },
      { title: "Shared", slot: "toolShared", width: 100 },
      { title: "ID", key: "id", minWidth: 260 },
      { title: "Action", slot: "action", minWidth: 260 }
    ];
  }

  if (resourceKind.value === "mcp") {
    return [
      { title: "Kind", key: "kind", width: 100 },
      { title: "Name", key: "name", minWidth: 180 },
      { title: "Project", slot: "project", minWidth: 220 },
      { title: "Visibility", key: "visibility", width: 120 },
      { title: "Transport", slot: "mcpTransport", width: 150 },
      { title: "Endpoint/Command", slot: "mcpEndpoint", minWidth: 220 },
      { title: "Last Test", slot: "mcpLastProbe", width: 120 },
      { title: "ID", key: "id", minWidth: 220 },
      { title: "Action", slot: "action", minWidth: 320 }
    ];
  }

  const baseColumns = [
    { title: "Kind", key: "kind", width: 120 },
    { title: "Name", key: "name", minWidth: 180 },
    { title: "Project", slot: "project", minWidth: 220 },
    { title: "Visibility", key: "visibility", width: 120 }
  ];

  if (showModelFields.value) {
    baseColumns.push(
      { title: "Model Provider", key: "model_provider", minWidth: 140 },
      { title: "Model Name", key: "model_name", minWidth: 160 }
    );
  }

  const actionWidth = resourceKind.value === "knowledge_base" ? 380 : 260;

  baseColumns.push(
    { title: "ID", key: "id", minWidth: 280 },
    { title: "Action", slot: "action", minWidth: actionWidth }
  );

  return baseColumns;
});

function toolConfig(resource) {
  return (resource && resource.config) || {};
}

function mcpConfig(resource) {
  return (resource && resource.config) || {};
}

function kindDisplay(kind) {
  const map = {
    agent: "Agent",
    tool: "Tool",
    skill: "Skill",
    mcp: "MCP Server",
    knowledge_base: "Knowledge Base",
    workflow: "Workflow"
  };
  return map[kind] || kind || "Resource";
}

function kindIcon(kind) {
  const map = {
    agent: "ios-planet",
    tool: "md-construct",
    skill: "md-school",
    mcp: "md-git-network",
    knowledge_base: "ios-book",
    workflow: "md-share"
  };
  return map[kind] || "ios-cube";
}

function kindTone(kind) {
  const map = {
    agent: "tone-blue",
    tool: "tone-teal",
    skill: "tone-violet",
    mcp: "tone-cyan",
    knowledge_base: "tone-amber",
    workflow: "tone-rose"
  };
  return map[kind] || "tone-blue";
}

function visibilityColor(visibility) {
  const map = {
    private: "red",
    project: "blue",
    public: "green"
  };
  return map[visibility] || "default";
}

function shortId(value) {
  const text = String(value || "");
  if (!text) return "-";
  if (text.length <= 12) return text;
  return `${text.slice(0, 8)}...${text.slice(-4)}`;
}

function resourceKindHint(kind) {
  const map = {
    agent: "An executable assistant profile with model, prompt, and bound capabilities.",
    tool: "A reusable callable function or API wrapper that can be bound to agents.",
    skill: "A progressive-disclosure instruction package that teaches agents how to do a task.",
    mcp: "A Model Context Protocol server configuration exposed as reusable tools.",
    knowledge_base: "A searchable document collection that can be attached to agents.",
    workflow: "A multi-step orchestration graph that coordinates agents and resources."
  };
  return map[kind] || "A reusable project resource.";
}

function arrayCount(value) {
  return Array.isArray(value) ? value.length : 0;
}

function valueOrDash(value) {
  if (value === undefined || value === null || value === "") return "-";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (Array.isArray(value)) return `${value.length}`;
  return String(value);
}

function boundItems(resource, key) {
  const bindings = resource?.bindings || {};
  const items = bindings[key];
  return Array.isArray(items) ? items : [];
}

function boundCount(resource, key, fallback) {
  const bindings = resource?.bindings || {};
  const countKey = {
    tools: "tool_count",
    skills: "skill_count",
    mcps: "mcp_count",
    knowledge_bases: "knowledge_base_count"
  }[key];
  const explicitCount = countKey ? bindings[countKey] : undefined;
  if (Number.isFinite(explicitCount)) {
    return explicitCount;
  }
  const items = boundItems(resource, key);
  return items.length || arrayCount(fallback);
}

function boundSummary(resource, key, fallback) {
  const count = boundCount(resource, key, fallback);
  const names = boundItems(resource, key)
    .map((item) => item.name || item.id)
    .filter(Boolean);
  if (names.length) {
    return `${count} - ${names.join(", ")}`;
  }
  return String(count);
}

function bindingItemMeta(item, group) {
  const parts = [];
  if (item.visibility) parts.push(item.visibility);
  if (item.source) parts.push(item.source);
  if (Number.isFinite(item.priority)) parts.push(`priority ${item.priority}`);
  if (Number.isFinite(item.top_k)) parts.push(`top_k ${item.top_k}`);
  if (Number.isFinite(item.similarity_threshold)) parts.push(`threshold ${item.similarity_threshold}`);
  if (Number.isFinite(item.step_count)) parts.push(`${item.step_count} step(s)`);
  if (Array.isArray(item.steps) && item.steps.length) parts.push(item.steps.join(", "));
  return parts.length ? parts.join(" / ") : group.label;
}
function bindingGroups(resource) {
  return [
    { key: "tools", label: "Tools", color: "green", emptyText: "No tools are bound to this agent.", items: boundItems(resource, "tools") },
    { key: "skills", label: "Skills", color: "purple", emptyText: "No skills are bound to this agent.", items: boundItems(resource, "skills") },
    { key: "mcps", label: "MCPs", color: "blue", emptyText: "No MCPs are bound to this agent.", items: boundItems(resource, "mcps") },
    {
      key: "knowledge_bases",
      label: "Knowledge Bases",
      color: "cyan",
      emptyText: "No knowledge bases are bound to this agent.",
      items: boundItems(resource, "knowledge_bases")
    },
    {
      key: "workflows",
      label: "Used In Workflows",
      color: "magenta",
      emptyText: "No workflows currently reference this agent.",
      items: boundItems(resource, "workflows")
    }
  ];
}

function detailFields(resource) {
  const config = resource?.config || {};
  const commonProvider = resource?.provider_profile || config.provider_profile;
  const fieldsByKind = {
    agent: [
      ["Model Provider", resource?.model_provider],
      ["Model Name", resource?.model_name],
      ["Provider Profile", commonProvider],
      ["Run Mode", config.run_mode || config.engine_type || config.runtime || "llm"],
      ["Tools", boundCount(resource, "tools", config.tool_ids || config.tools)],
      ["Skills", boundCount(resource, "skills", config.skill_ids || config.skills)],
      ["MCPs", boundCount(resource, "mcps", config.mcp_ids || config.mcps || config.mcp_servers)],
      ["Knowledge Bases", boundCount(resource, "knowledge_bases", config.knowledge_base_ids || config.knowledge_bases || config.knowledge)]
    ],
    tool: [
      ["Runtime", config.runtime],
      ["Entrypoint", config.entrypoint],
      ["Shared In Project", config.shared_in_project === false ? false : true],
      ["Timeout Seconds", config.timeout_seconds]
    ],
    skill: [
      ["Package Name", config.package_name || config.skill_name || resource?.name],
      ["Entrypoint", config.entrypoint || config.main || "instruction-only"],
      ["Version", config.version],
      ["Runtime", config.runtime || config.runner || "progressive disclosure"]
    ],
    mcp: [
      ["Transport", config.transport || "streamable_http"],
      ["Endpoint URL", config.endpoint_url],
      ["Command", config.command],
      ["Timeout Seconds", config.timeout_seconds]
    ],
    knowledge_base: [
      ["Chunk Size", config.chunk_size],
      ["Chunk Overlap", config.chunk_overlap],
      ["Top K", config.top_k],
      ["Similarity Threshold", config.similarity_threshold]
    ],
    workflow: [
      ["Version", config.version],
      ["Status", config.status],
      ["Steps", arrayCount(config.steps || config.nodes)],
      ["Timeout Seconds", config.timeout_seconds],
      ["Max Retries", config.max_retries]
    ]
  };
  return (fieldsByKind[resource?.kind] || [["Provider Profile", commonProvider]])
    .map(([label, value]) => ({ label, value: valueOrDash(value) }));
}

function prettyConfig(resource) {
  const config = resource?.config || {};
  if (Object.keys(config).length === 0) {
    return "{}";
  }
  return JSON.stringify(config, null, 2);
}
async function probeMcp(row) {
  probingById.value = { ...probingById.value, [row.id]: true };
  try {
    const result = await api.probeMcp({
      project_id: row.project_id,
      config: mcpConfig(row)
    });
    const items = resources.value.map((item) => {
      if (item.id !== row.id) {
        return item;
      }
      return { ...item, _mcp_probe: result };
    });
    resources.value = items;
    if (result.ok) {
      Message.success(`MCP probe success: ${result.tools.length} tool(s)`);
    } else {
      Message.error(result.error || "MCP probe failed");
    }
  } catch (error) {
    Message.error(error.message || "MCP probe failed");
  } finally {
    probingById.value = { ...probingById.value, [row.id]: false };
  }
}

async function loadData() {
  loading.value = true;
  try {
    resourcePage.value = 1;
    resources.value = await api.listOwnedResources({
      kind: resourceKind.value || undefined,
      q: queryText.value.trim() || undefined,
      project_q: projectQuery.value.trim() || undefined
    });
  } catch (error) {
    Message.error(error.message || "Load resources failed");
  } finally {
    loading.value = false;
  }
}

function goCreate() {
  if (!createRoute.value) {
    return;
  }
  router.push({ name: createRoute.value });
}

function openDetail(row) {
  // For skills and workflows, navigate to their dedicated management pages.
  if (resourceKind.value === 'skill') {
    router.push({ name: 'resources-skill-detail', params: { resourceId: row.id } });
    return;
  }
  if (resourceKind.value === 'workflow') {
    router.push({ name: 'workflows-detail', params: { resourceId: row.id } });
    return;
  }
  
  // For other resources, show the detail drawer
  current.value = row;
  showDetail.value = true;
}

function openEditPage(row) {
  const routeMap = {
    agent: "resources-agents-edit",
    tool: "resources-tools-edit",
    skill: "resources-skills-edit",
    mcp: "resources-mcps-edit",
    knowledge_base: "resources-knowledge-bases-edit",
    workflow: "workflows-edit"
  };
  const routeName = routeMap[row.kind];
  if (!routeName) {
    Message.warning("Edit route is not configured for this resource type");
    return;
  }
  router.push({ name: routeName, params: { resourceId: row.id } });
}

function openDocuments(row) {
  router.push({ name: "resources-knowledge-bases-detail", params: { resourceId: row.id } });
}

function openSkillDetail(row) {
  router.push({ name: "resources-skill-detail", params: { resourceId: row.id } });
}

function openWorkflowDetail(row) {
  router.push({ name: "workflows-detail", params: { resourceId: row.id } });
}

function openDelete(row) {
  current.value = row;
  showDelete.value = true;
}

async function confirmDelete() {
  if (!current.value) {
    return;
  }
  deleting.value = true;
  try {
    await api.deleteResource(current.value.id);
    Message.success("Resource deleted");
    showDelete.value = false;
    current.value = null;
    await loadData();
  } catch (error) {
    Message.error(error.message || "Delete resource failed");
  } finally {
    deleting.value = false;
  }
}

watch(
  () => route.fullPath,
  () => {
    queryText.value = "";
    projectQuery.value = "";
    loadData();
  }
);

onMounted(loadData);
</script>

<style scoped>
.project-cell {
  display: grid;
  gap: 5px;
  align-items: center;
}

.project-cell span {
  color: #64748b;
  font-size: 12px;
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-detail-shell {
  display: grid;
  gap: 18px;
}

.resource-detail-hero {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  align-items: start;
  padding: 16px;
  border: 1px solid #dbe7f3;
  border-radius: 12px;
  background: linear-gradient(135deg, #f8fbff 0%, #eef6ff 100%);
  overflow: hidden;
}

.resource-kind-icon {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 14px;
  color: #ffffff;
  font-size: 22px;
  box-shadow: 0 14px 32px rgba(21, 36, 61, 0.18);
}

.resource-detail-heading {
  min-width: 0;
}

.resource-detail-title-row,
.section-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.resource-detail-title-row h2 {
  margin: 0;
  color: #111827;
  font-size: 22px;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.resource-detail-heading p {
  margin: 8px 0 12px;
  color: #64748b;
  line-height: 1.55;
}

.resource-detail-tags,
.detail-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-action-row {
  padding-bottom: 2px;
}

.detail-section {
  padding: 16px;
  border: 1px solid #e0e8f2;
  border-radius: 10px;
  background: #ffffff;
}

.detail-section h3,
.section-title-row h3 {
  margin: 0 0 12px;
  color: #172033;
  font-size: 16px;
}

.section-title-row h3 {
  margin-bottom: 0;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.detail-tile {
  display: grid;
  gap: 5px;
  min-width: 0;
  padding: 12px;
  border-radius: 8px;
  background: #f8fbff;
  border: 1px solid #e2ebf5;
}

.detail-tile span,
.detail-field-row span,
.detail-tile small {
  color: #64748b;
  font-size: 12px;
}

.detail-tile strong,
.detail-field-row strong {
  min-width: 0;
  color: #172033;
  overflow-wrap: anywhere;
}

.detail-field-list {
  display: grid;
  gap: 8px;
}

.detail-field-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  align-items: start;
  padding: 9px 0;
  border-bottom: 1px solid #eef2f7;
}

.detail-field-row:last-child {
  border-bottom: 0;
}

.binding-groups {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  justify-content: start;
}

.binding-group {
  min-width: 0;
  padding: 12px;
  border: 1px solid #e2ebf5;
  border-radius: 8px;
  background: #f8fbff;
}

.binding-group-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  color: #172033;
  font-weight: 700;
}

.binding-resource-list {
  display: grid;
  gap: 8px;
}

.binding-resource-item {
  display: grid;
  grid-template-columns: 1fr;
  min-width: 0;
  gap: 10px;
  align-items: center;
  padding: 9px 10px;
  border: 1px solid #e2ebf5;
  border-radius: 8px;
  background: #ffffff;
}

.binding-resource-item div {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.binding-resource-item strong {
  color: #172033;
  overflow-wrap: anywhere;
}

.binding-resource-item span {
  color: #64748b;
  font-size: 12px;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.binding-group p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.detail-description {
  margin: 0;
  color: #334155;
  line-height: 1.65;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.detail-config-json {
  max-height: 320px;
  margin: 12px 0 0;
  padding: 12px;
  overflow-x: hidden;
  overflow-y: auto;
  border-radius: 8px;
  border: 1px solid #e2eaf3;
  background: #0f172a;
  color: #dbeafe;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.mono-value {
  font-family: Consolas, "Courier New", monospace;
}

.tone-blue { background: linear-gradient(135deg, #2563eb, #0891b2); }
.tone-teal { background: linear-gradient(135deg, #0f766e, #14b8a6); }
.tone-violet { background: linear-gradient(135deg, #6d28d9, #7c3aed); }
.tone-cyan { background: linear-gradient(135deg, #0284c7, #06b6d4); }
.tone-amber { background: linear-gradient(135deg, #b45309, #f59e0b); }
.tone-rose { background: linear-gradient(135deg, #be123c, #f43f5e); }

@media (max-width: 760px) {
  .resource-detail-hero,
  .detail-grid,
  .binding-groups,
  .detail-field-row {
    grid-template-columns: 1fr;
  }
}
</style>
