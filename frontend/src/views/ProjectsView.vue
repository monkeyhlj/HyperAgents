<template>
  <div>
    <Card dis-hover>
      <template #title>Create Project</template>
      <Form :model="form" inline>
        <FormItem>
          <Input v-model="form.name" placeholder="Project name" style="width: 220px" />
        </FormItem>
        <FormItem>
          <Input v-model="form.description" placeholder="Description" style="width: 320px" />
        </FormItem>
        <FormItem>
          <Button type="primary" :loading="creating" @click="createProject">Create</Button>
        </FormItem>
        <FormItem>
          <Button @click="loadProjects" :loading="loading">Refresh</Button>
        </FormItem>
      </Form>
    </Card>

    <Card class="mt16" dis-hover>
      <template #title>Search Projects</template>
      <Form inline>
        <FormItem>
          <Input v-model="projectQuery" clearable placeholder="Filter by project id or name" style="width: 360px" />
        </FormItem>
        <FormItem>
          <Tag color="blue">Matched: {{ filteredProjects.length }}</Tag>
        </FormItem>
      </Form>
    </Card>

    <Card class="mt16" dis-hover>
      <template #title>Project List</template>
      <Table :columns="columns" :data="filteredProjects" stripe>
        <template #name="{ row }">
          <a class="project-link" @click.prevent="openDetail(row)">{{ row.name }}</a>
        </template>
        <template #owner="{ row }">
          <Tag color="gold">{{ row.owner_id }}</Tag>
        </template>
        <template #members="{ row }">
          <Space>
            <Tag v-for="member in row.members" :key="member" color="blue">{{ member }}</Tag>
            <Button size="small" @click="openManageMembers(row)">Manage</Button>
          </Space>
        </template>
        <template #action="{ row }">
          <Button size="small" type="primary" ghost @click="openDetail(row)">View Detail</Button>
        </template>
      </Table>
    </Card>

    <Modal v-model="showMemberModal" title="Manage Members" width="680">
      <div v-if="selectedProject">
        <p><strong>Project:</strong> {{ selectedProject.name }}</p>
        <Form inline>
          <FormItem>
            <Input v-model="memberInput" placeholder="User ID to add" style="width: 280px" />
          </FormItem>
          <FormItem>
            <Button type="primary" :loading="memberBusy" @click="addMember">Add Member</Button>
          </FormItem>
        </Form>
        <Divider />
        <Space wrap>
          <Tag v-for="member in selectedProject.members" :key="member" color="cyan">
            {{ member }}
            <Icon
              v-if="member !== selectedProject.owner_id"
              type="md-close"
              style="margin-left: 8px; cursor: pointer"
              @click="removeMember(member)"
            />
          </Tag>
        </Space>
      </div>
      <template #footer>
        <Button @click="showMemberModal = false">Close</Button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { Message } from "view-ui-plus";
import { api } from "../services/api";

const router = useRouter();

const form = ref({ name: "", description: "" });
const projects = ref([]);
const projectQuery = ref("");
const loading = ref(false);
const creating = ref(false);
const showMemberModal = ref(false);
const selectedProject = ref(null);
const memberInput = ref("");
const memberBusy = ref(false);

const columns = [
  { title: "Name", slot: "name", minWidth: 200 },
  { title: "Description", key: "description", minWidth: 240 },
  { title: "Owner", slot: "owner", minWidth: 140 },
  { title: "Members", slot: "members", minWidth: 200 },
  { title: "ID", key: "id", minWidth: 280 },
  { title: "Action", slot: "action", width: 120 }
];

const filteredProjects = computed(() => {
  const q = projectQuery.value.trim().toLowerCase();
  if (!q) {
    return projects.value;
  }
  return projects.value.filter((item) => item.id.toLowerCase().includes(q) || item.name.toLowerCase().includes(q));
});

async function loadProjects() {
  loading.value = true;
  try {
    projects.value = await api.listProjects();
  } catch (error) {
    Message.error(error.message || "Load projects failed");
  } finally {
    loading.value = false;
  }
}

async function createProject() {
  if (!form.value.name || form.value.name.length < 2) {
    Message.warning("Project name requires at least 2 chars");
    return;
  }
  creating.value = true;
  try {
    await api.createProject(form.value);
    Message.success("Project created");
    form.value = { name: "", description: "" };
    await loadProjects();
  } catch (error) {
    Message.error(error.message || "Create project failed");
  } finally {
    creating.value = false;
  }
}

function openManageMembers(project) {
  selectedProject.value = project;
  memberInput.value = "";
  showMemberModal.value = true;
}

function openDetail(project) {
  router.push({ name: "project-detail", params: { projectId: project.id } });
}

async function addMember() {
  if (!selectedProject.value) {
    return;
  }
  if (!memberInput.value.trim()) {
    Message.warning("Please input user ID");
    return;
  }

  memberBusy.value = true;
  try {
    const updated = await api.addProjectMember(selectedProject.value.id, memberInput.value.trim());
    Message.success("Member added");
    selectedProject.value = updated;
    memberInput.value = "";
    await loadProjects();
  } catch (error) {
    Message.error(error.message || "Add member failed");
  } finally {
    memberBusy.value = false;
  }
}

async function removeMember(memberId) {
  if (!selectedProject.value) {
    return;
  }

  memberBusy.value = true;
  try {
    const updated = await api.removeProjectMember(selectedProject.value.id, memberId);
    Message.success("Member removed");
    selectedProject.value = updated;
    await loadProjects();
  } catch (error) {
    Message.error(error.message || "Remove member failed");
  } finally {
    memberBusy.value = false;
  }
}

onMounted(loadProjects);
</script>
