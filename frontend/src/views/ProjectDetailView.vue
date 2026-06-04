<template>
  <div>
    <Card dis-hover>
      <template #title>
        <Space>
          <Button size="small" @click="backToProjects">Back</Button>
          <span>Project Detail</span>
        </Space>
      </template>

      <Skeleton v-if="loadingProject" :loading="loadingProject" animated>
        <div style="height: 80px"></div>
      </Skeleton>

      <div v-else-if="project">
        <Row :gutter="16">
          <Col :xs="24" :sm="12">
            <div class="detail-item">
              <div class="detail-label">Name</div>
              <div class="detail-value">{{ project.name || "-" }}</div>
            </div>
          </Col>
          <Col :xs="24" :sm="12">
            <div class="detail-item">
              <div class="detail-label">Owner</div>
              <div class="detail-value">{{ project.owner_name || project.owner_id || "-" }}</div>
            </div>
          </Col>
          <Col :xs="24" :sm="12">
            <div class="detail-item">
              <div class="detail-label">Project ID</div>
              <div class="detail-value detail-mono">{{ project.id || "-" }}</div>
            </div>
          </Col>
          <Col :xs="24" :sm="12">
            <div class="detail-item">
              <div class="detail-label">Created At</div>
              <div class="detail-value">{{ formatTime(project.created_at) }}</div>
            </div>
          </Col>
          <Col :xs="24" :sm="12">
            <div class="detail-item">
              <div class="detail-label">Updated At</div>
              <div class="detail-value">{{ formatTime(project.updated_at) }}</div>
            </div>
          </Col>
          <Col :xs="24" :sm="24">
            <div class="detail-item">
              <div class="detail-label">Members</div>
              <div class="detail-value">
                <Space wrap>
                  <Tag
                    v-for="(member, idx) in project.members || []"
                    :key="member"
                    color="blue"
                  >
                    {{ (project.member_names && project.member_names[idx]) || member }}
                  </Tag>
                  <span v-if="!(project.members || []).length">-</span>
                </Space>
              </div>
            </div>
          </Col>
          <Col :xs="24" :sm="24">
            <div class="detail-item">
              <div class="detail-label">Member Managers</div>
              <div class="detail-value">
                <Space wrap>
                  <Tag
                    v-for="(member, idx) in project.member_managers || []"
                    :key="`mgr-${member}`"
                    color="orange"
                  >
                    {{ (project.member_manager_names && project.member_manager_names[idx]) || member }}
                  </Tag>
                  <span v-if="!(project.member_managers || []).length">-</span>
                </Space>
              </div>
            </div>
          </Col>
          <Col :xs="24" :sm="24">
            <div class="detail-item">
              <div class="detail-label">Description</div>
              <div class="detail-value">{{ project.description || "-" }}</div>
            </div>
          </Col>
        </Row>
      </div>
    </Card>

    <Card class="mt16" dis-hover>
      <template #title>
        <Space>
          <span>Project Resources</span>
          <Button size="small" @click="loadResources" :loading="loadingResources">Refresh</Button>
        </Space>
      </template>

      <Form inline>
        <FormItem>
          <Input v-model="resourceQuery" clearable placeholder="Filter by resource name or id" style="width: 320px" />
        </FormItem>
        <FormItem>
          <Tag color="cyan">Matched: {{ filteredResources.length }}</Tag>
        </FormItem>
      </Form>

      <Table :columns="columns" :data="filteredResources" stripe>
        <template #action="{ row }">
          <Space>
            <Button size="small" :disabled="!canEditResource(row)" @click="openResourceEditDrawer(row)">Edit</Button>
            <Button
              size="small"
              type="error"
              ghost
              :disabled="!canEditResource(row)"
              @click="openDeleteResourceModal(row)"
            >
              Delete
            </Button>
          </Space>
        </template>
      </Table>
    </Card>

    <Drawer v-model="showEditDrawer" title="Edit Resource" width="520" :mask-closable="false">
      <Form :model="editForm" label-position="top">
        <FormItem label="Resource ID">
          <Input v-model="editForm.id" readonly />
        </FormItem>
        <FormItem label="Owner ID">
          <Input v-model="editForm.owner_id" readonly />
        </FormItem>
        <FormItem label="Kind">
          <Input v-model="editForm.kind" readonly />
        </FormItem>
        <FormItem label="Name">
          <Input v-model="editForm.name" maxlength="120" show-word-limit />
        </FormItem>
        <FormItem label="Visibility">
          <Select v-model="editForm.visibility">
            <Option v-for="item in visibilityOptions" :key="item" :value="item">{{ item }}</Option>
          </Select>
        </FormItem>
        <FormItem label="Model Provider">
          <Input v-model="editForm.model_provider" placeholder="Model provider" maxlength="60" />
        </FormItem>
        <FormItem label="Model Name">
          <Input v-model="editForm.model_name" placeholder="Model name" maxlength="120" />
        </FormItem>
        <FormItem label="Provider Profile">
          <Input v-model="editForm.provider_profile" placeholder="Provider profile" maxlength="60" />
        </FormItem>
        <FormItem label="Description">
          <Input v-model="editForm.description" type="textarea" :rows="4" maxlength="1000" show-word-limit />
        </FormItem>
      </Form>
      <template #footer>
        <Button @click="showEditDrawer = false">Cancel</Button>
        <Button type="primary" :loading="editSaving" @click="saveResource">Save</Button>
      </template>
    </Drawer>

    <Modal v-model="showDeleteModal" title="Delete Resource" :mask-closable="false">
      <p v-if="pendingDeleteResource">
        Confirm delete resource: <strong>{{ pendingDeleteResource.name }}</strong> ?
      </p>
      <p>This action cannot be undone.</p>
      <template #footer>
        <Button @click="showDeleteModal = false">Cancel</Button>
        <Button type="error" :loading="deleteBusy" @click="confirmDeleteResource">Delete</Button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Message } from "view-ui-plus";
import { api } from "../services/api";
import { authState } from "../stores/auth";

const route = useRoute();
const router = useRouter();

const project = ref(null);
const resources = ref([]);
const loadingProject = ref(false);
const loadingResources = ref(false);
const resourceQuery = ref("");
const showEditDrawer = ref(false);
const editSaving = ref(false);
const showDeleteModal = ref(false);
const deleteBusy = ref(false);
const pendingDeleteResource = ref(null);
const editForm = ref({
  id: "",
  owner_id: "",
  kind: "",
  name: "",
  visibility: "project",
  model_provider: "",
  model_name: "",
  provider_profile: "",
  description: ""
});
const visibilityOptions = ["private", "project", "public"];

const columns = [
  { title: "Kind", key: "kind", width: 130 },
  { title: "Name", key: "name", minWidth: 180 },
  { title: "Visibility", key: "visibility", width: 120 },
  { title: "Model Provider", key: "model_provider", minWidth: 140 },
  { title: "Model Name", key: "model_name", minWidth: 160 },
  { title: "Owner", key: "owner_id", minWidth: 140 },
  { title: "ID", key: "id", minWidth: 280 },
  { title: "Action", slot: "action", minWidth: 160 }
];

const projectId = computed(() => String(route.params.projectId || ""));
const currentUserId = computed(() => authState.user?.id || "");

const filteredResources = computed(() => {
  const q = resourceQuery.value.trim().toLowerCase();
  if (!q) {
    return resources.value;
  }
  return resources.value.filter((item) => item.id.toLowerCase().includes(q) || item.name.toLowerCase().includes(q));
});

function backToProjects() {
  router.push({ name: "projects" });
}

function canEditResource(resource) {
  if (!project.value || !currentUserId.value) {
    return false;
  }
  return currentUserId.value === project.value.owner_id || currentUserId.value === resource.owner_id;
}

function formatTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString();
}

function openResourceEditDrawer(resource) {
  if (!canEditResource(resource)) {
    Message.warning("No permission to edit this resource");
    return;
  }
  editForm.value = {
    id: resource.id,
    owner_id: resource.owner_id,
    kind: resource.kind || "",
    name: resource.name || "",
    visibility: resource.visibility || "project",
    model_provider: resource.model_provider || "",
    model_name: resource.model_name || "",
    provider_profile: resource.provider_profile || "",
    description: resource.description || ""
  };
  showEditDrawer.value = true;
}

async function saveResource() {
  if (!editForm.value.id) {
    return;
  }
  const name = editForm.value.name.trim();
  if (name.length < 2) {
    Message.warning("Resource name requires at least 2 chars");
    return;
  }

  editSaving.value = true;
  try {
    await api.updateResource(editForm.value.id, {
      name,
      description: editForm.value.description,
      visibility: editForm.value.visibility || undefined,
      model_provider: editForm.value.model_provider || null,
      model_name: editForm.value.model_name || null,
      provider_profile: editForm.value.provider_profile || null
    });
    Message.success("Resource updated");
    showEditDrawer.value = false;
    await loadResources();
  } catch (error) {
    Message.error(error.message || "Update resource failed");
  } finally {
    editSaving.value = false;
  }
}

function openDeleteResourceModal(resource) {
  if (!canEditResource(resource)) {
    Message.warning("No permission to delete this resource");
    return;
  }
  pendingDeleteResource.value = resource;
  showDeleteModal.value = true;
}

async function confirmDeleteResource() {
  if (!pendingDeleteResource.value) {
    return;
  }
  deleteBusy.value = true;
  try {
    await api.deleteResource(pendingDeleteResource.value.id);
    Message.success("Resource deleted");
    showDeleteModal.value = false;
    pendingDeleteResource.value = null;
    await loadResources();
  } catch (error) {
    Message.error(error.message || "Delete resource failed");
  } finally {
    deleteBusy.value = false;
  }
}

async function loadProject() {
  if (!projectId.value) {
    return;
  }
  loadingProject.value = true;
  try {
    project.value = await api.getProject(projectId.value);
  } catch (error) {
    Message.error(error.message || "Load project detail failed");
  } finally {
    loadingProject.value = false;
  }
}

async function loadResources() {
  if (!projectId.value) {
    return;
  }
  loadingResources.value = true;
  try {
    resources.value = await api.listResources(projectId.value);
  } catch (error) {
    Message.error(error.message || "Load resources failed");
  } finally {
    loadingResources.value = false;
  }
}

onMounted(async () => {
  await loadProject();
  await loadResources();
});
</script>

<style scoped>
.detail-item {
  border: 1px solid #e8eaec;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
  background: #fff;
}

.detail-label {
  font-size: 12px;
  color: #808695;
  margin-bottom: 6px;
}

.detail-value {
  font-size: 14px;
  color: #17233d;
  line-height: 1.6;
  word-break: break-word;
}

.detail-mono {
  font-family: Consolas, "Courier New", monospace;
}
</style>
