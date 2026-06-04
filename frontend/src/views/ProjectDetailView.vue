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
        <Descriptions :column="2" bordered>
          <DescriptionsItem label="Name">{{ project.name }}</DescriptionsItem>
          <DescriptionsItem label="Owner">{{ project.owner_name || project.owner_id }}</DescriptionsItem>
          <DescriptionsItem label="Project ID">{{ project.id }}</DescriptionsItem>
          <DescriptionsItem label="Created At">{{ project.created_at }}</DescriptionsItem>
          <DescriptionsItem label="Updated At">{{ project.updated_at }}</DescriptionsItem>
          <DescriptionsItem label="Members">
            <Space wrap>
              <Tag
                v-for="(member, idx) in project.members || []"
                :key="member"
                color="blue"
              >
                {{ (project.member_names && project.member_names[idx]) || member }}
              </Tag>
            </Space>
          </DescriptionsItem>
          <DescriptionsItem label="Member Managers">
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
          </DescriptionsItem>
          <DescriptionsItem label="Description" :span="2">{{ project.description || "-" }}</DescriptionsItem>
        </Descriptions>
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
        <FormItem label="Name">
          <Input v-model="editForm.name" maxlength="120" show-word-limit />
        </FormItem>
        <FormItem label="Description">
          <Input v-model="editForm.description" type="textarea" :rows="4" maxlength="500" show-word-limit />
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
const editForm = ref({ id: "", owner_id: "", name: "", description: "" });

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

function openResourceEditDrawer(resource) {
  if (!canEditResource(resource)) {
    Message.warning("No permission to edit this resource");
    return;
  }
  editForm.value = {
    id: resource.id,
    owner_id: resource.owner_id,
    name: resource.name || "",
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
      description: editForm.value.description
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
