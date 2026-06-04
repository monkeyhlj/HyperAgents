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
        <template #action="{ row }">
          <Space>
            <Button size="small" @click="openDetail(row)">Detail</Button>
            <Button size="small" type="primary" ghost @click="openEditPage(row)">Edit</Button>
            <Button
              size="small"
              ghost
              type="warning"
              :disabled="row.kind !== 'agent'"
              @click="openCodeVersions(row)"
            >
              Code Versions
            </Button>
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
        <DescriptionsItem label="Model Provider">{{ current.model_provider || '-' }}</DescriptionsItem>
        <DescriptionsItem label="Model Name">{{ current.model_name || '-' }}</DescriptionsItem>
        <DescriptionsItem label="Provider Profile">{{ current.provider_profile || '-' }}</DescriptionsItem>
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

    <Drawer v-model="showCodeVersions" :title="`Code Versions - ${current?.name || ''}`" width="760" :mask-closable="false">
      <Alert show-icon>Publish current custom code as immutable version, then rollback any version when needed.</Alert>
      <Form label-position="top" style="margin-top: 10px">
        <FormItem label="Publish Note">
          <Input v-model="publishNote" maxlength="200" placeholder="e.g. Add MCP fallback logic" />
        </FormItem>
      </Form>
      <Space style="margin-bottom: 10px">
        <Button :loading="publishing" type="primary" @click="publishCurrentCode">Publish Current Code</Button>
        <Button :loading="loadingVersions" @click="loadCodeVersions">Refresh</Button>
      </Space>
      <Table :columns="versionColumns" :data="codeVersions" stripe>
        <template #code="{ row }">
          <pre class="code-preview">{{ row.code }}</pre>
        </template>
        <template #versionAction="{ row }">
          <Button size="small" :loading="rollingBack" @click="rollbackVersion(row)">Rollback</Button>
        </template>
      </Table>
    </Drawer>
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
const queryText = ref("");
const projectQuery = ref("");

const showDetail = ref(false);
const showDelete = ref(false);
const showCodeVersions = ref(false);
const current = ref(null);
const codeVersions = ref([]);
const loadingVersions = ref(false);
const publishing = ref(false);
const rollingBack = ref(false);
const publishNote = ref("");

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

const columns = [
  { title: "Kind", key: "kind", width: 120 },
  { title: "Name", key: "name", minWidth: 180 },
  { title: "Project", slot: "project", minWidth: 160 },
  { title: "Visibility", key: "visibility", width: 120 },
  { title: "Model Provider", key: "model_provider", minWidth: 140 },
  { title: "Model Name", key: "model_name", minWidth: 160 },
  { title: "ID", key: "id", minWidth: 280 },
  { title: "Action", slot: "action", minWidth: 200 }
];

const versionColumns = [
  { title: "Version ID", key: "version_id", minWidth: 220 },
  { title: "Note", key: "note", minWidth: 180 },
  { title: "Created By", key: "created_by", width: 140 },
  { title: "Created At", key: "created_at", minWidth: 180 },
  { title: "Code", slot: "code", minWidth: 260 },
  { title: "Action", slot: "versionAction", width: 110 }
];

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

async function openCodeVersions(row) {
  if (row.kind !== "agent") {
    Message.warning("Code version management is available for agents only");
    return;
  }
  current.value = row;
  showCodeVersions.value = true;
  publishNote.value = "";
  await loadCodeVersions();
}

async function loadCodeVersions() {
  if (!current.value) {
    return;
  }
  loadingVersions.value = true;
  try {
    codeVersions.value = await api.listResourceCodeVersions(current.value.id);
  } catch (error) {
    Message.error(error.message || "Load code versions failed");
  } finally {
    loadingVersions.value = false;
  }
}

async function publishCurrentCode() {
  if (!current.value) {
    return;
  }
  publishing.value = true;
  try {
    codeVersions.value = await api.publishResourceCodeVersion(current.value.id, { note: publishNote.value || null });
    Message.success("Code version published");
    await loadData();
  } catch (error) {
    Message.error(error.message || "Publish code version failed");
  } finally {
    publishing.value = false;
  }
}

async function rollbackVersion(item) {
  if (!current.value) {
    return;
  }
  rollingBack.value = true;
  try {
    codeVersions.value = await api.rollbackResourceCodeVersion(current.value.id, item.version_id);
    Message.success("Rollback succeeded");
    await loadData();
  } catch (error) {
    Message.error(error.message || "Rollback failed");
  } finally {
    rollingBack.value = false;
  }
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
.code-preview {
  margin: 0;
  max-height: 140px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}
</style>
