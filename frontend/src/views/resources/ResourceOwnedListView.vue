<template>
  <div>
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

      <Table :columns="columns" :data="resources" stripe>
        <template #project="{ row }">
          <Tag color="gold">{{ row.project_name }}</Tag>
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
            <Button size="small" @click="openDetail(row)">Detail</Button>
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
    </Card>

    <Drawer v-model="showDetail" :title="`Resource Detail - ${current?.name || ''}`" width="560">
      <Descriptions v-if="current" :column="1" bordered>
        <DescriptionsItem label="Kind">{{ current.kind }}</DescriptionsItem>
        <DescriptionsItem label="Name">{{ current.name }}</DescriptionsItem>
        <DescriptionsItem label="Project">{{ current.project_name }}</DescriptionsItem>
        <DescriptionsItem label="Visibility">{{ current.visibility }}</DescriptionsItem>
        <DescriptionsItem v-if="resourceKind === 'tool'" label="Tool Runtime">{{ toolConfig(current).runtime || '-' }}</DescriptionsItem>
        <DescriptionsItem v-if="resourceKind === 'tool'" label="Function Name">{{ toolConfig(current).entrypoint || '-' }}</DescriptionsItem>
        <DescriptionsItem v-if="resourceKind === 'tool'" label="Shared In Project">{{ toolConfig(current).shared_in_project === false ? 'false' : 'true' }}</DescriptionsItem>
        <DescriptionsItem v-if="resourceKind !== 'tool'" label="Model Provider">{{ current.model_provider || '-' }}</DescriptionsItem>
        <DescriptionsItem v-if="resourceKind !== 'tool'" label="Model Name">{{ current.model_name || '-' }}</DescriptionsItem>
        <DescriptionsItem v-if="resourceKind !== 'tool'" label="Provider Profile">{{ current.provider_profile || '-' }}</DescriptionsItem>
        <DescriptionsItem v-if="resourceKind === 'mcp'" label="Transport">{{ mcpConfig(current).transport || 'streamable_http' }}</DescriptionsItem>
        <DescriptionsItem v-if="resourceKind === 'mcp'" label="Endpoint URL">{{ mcpConfig(current).endpoint_url || '-' }}</DescriptionsItem>
        <DescriptionsItem v-if="resourceKind === 'mcp'" label="Command">{{ mcpConfig(current).command || '-' }}</DescriptionsItem>
        <DescriptionsItem label="Description">{{ current.description || '-' }}</DescriptionsItem>
        <DescriptionsItem label="Resource ID">{{ current.id }}</DescriptionsItem>
      </Descriptions>
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

const columns = computed(() => {
  if (resourceKind.value === "tool") {
    return [
      { title: "Kind", key: "kind", width: 100 },
      { title: "Name", key: "name", minWidth: 180 },
      { title: "Project", slot: "project", minWidth: 160 },
      { title: "Visibility", key: "visibility", width: 120 },
      { title: "Runtime", slot: "toolRuntime", width: 120 },
      { title: "Function", slot: "toolFunction", minWidth: 150 },
      { title: "Shared", slot: "toolShared", width: 100 },
      { title: "ID", key: "id", minWidth: 260 },
      { title: "Action", slot: "action", minWidth: 200 }
    ];
  }

  if (resourceKind.value === "mcp") {
    return [
      { title: "Kind", key: "kind", width: 100 },
      { title: "Name", key: "name", minWidth: 180 },
      { title: "Project", slot: "project", minWidth: 160 },
      { title: "Visibility", key: "visibility", width: 120 },
      { title: "Transport", slot: "mcpTransport", width: 150 },
      { title: "Endpoint/Command", slot: "mcpEndpoint", minWidth: 220 },
      { title: "Last Test", slot: "mcpLastProbe", width: 120 },
      { title: "ID", key: "id", minWidth: 220 },
      { title: "Action", slot: "action", minWidth: 240 }
    ];
  }

  return [
    { title: "Kind", key: "kind", width: 120 },
    { title: "Name", key: "name", minWidth: 180 },
    { title: "Project", slot: "project", minWidth: 160 },
    { title: "Visibility", key: "visibility", width: 120 },
    { title: "Model Provider", key: "model_provider", minWidth: 140 },
    { title: "Model Name", key: "model_name", minWidth: 160 },
    { title: "ID", key: "id", minWidth: 280 },
    { title: "Action", slot: "action", minWidth: 200 }
  ];
});

function toolConfig(resource) {
  return (resource && resource.config) || {};
}

function mcpConfig(resource) {
  return (resource && resource.config) || {};
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
