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
          <Tag color="gold">{{ row.owner_name || row.owner_id }}</Tag>
        </template>
        <template #members="{ row }">
          <Space>
            <Tag v-for="(member, idx) in visibleMembers(row)" :key="member" color="blue">
              {{ displayMemberName(row, idx) }}
            </Tag>
            <Poptip v-if="hiddenMemberNames(row).length > 0" trigger="hover" placement="bottom">
              <Tag color="geekblue">+{{ hiddenMemberNames(row).length }}</Tag>
              <template #content>
                <Space wrap>
                  <Tag v-for="name in hiddenMemberNames(row)" :key="name" color="blue">{{ name }}</Tag>
                </Space>
              </template>
            </Poptip>
            <Button v-if="canAddMembers(row)" size="small" @click="openManageMembers(row)">Manage</Button>
          </Space>
        </template>
        <template #action="{ row }">
          <Space>
            <Button size="small" type="primary" ghost @click="openDetail(row)">View Detail</Button>
            <Button v-if="isOwner(row)" size="small" @click="openEditDrawer(row)">Edit</Button>
            <Button v-if="isOwner(row)" size="small" type="error" ghost @click="openDeleteModal(row)">Delete</Button>
          </Space>
        </template>
      </Table>
    </Card>

    <Drawer v-model="showEditDrawer" title="Edit Project" width="480" :mask-closable="false">
      <Form :model="editForm" label-position="top">
        <FormItem label="Project ID">
          <Input v-model="editForm.id" readonly />
        </FormItem>
        <FormItem label="Owner">
          <Input v-model="editForm.ownerName" readonly />
        </FormItem>
        <FormItem label="Name">
          <Input v-model="editForm.name" placeholder="Project name" maxlength="80" show-word-limit />
        </FormItem>
        <FormItem label="Description">
          <Input
            v-model="editForm.description"
            type="textarea"
            :rows="5"
            placeholder="Project description"
            maxlength="500"
            show-word-limit
          />
        </FormItem>

        <Divider />

        <FormItem label="Members">
          <Space wrap>
            <Tag v-for="(member, idx) in editProjectMembers" :key="member" color="cyan">
              {{ editProjectMemberNames[idx] || member }}
              <Icon
                v-if="editTargetProject && isOwner(editTargetProject) && member !== editTargetProject.owner_id"
                type="md-close"
                style="margin-left: 8px; cursor: pointer"
                @click="removeMember(member)"
              />
            </Tag>
          </Space>
        </FormItem>

        <FormItem v-if="editTargetProject && canAddMembers(editTargetProject)" label="Add Member">
          <Space>
            <Input
              v-model="memberInput"
              placeholder="Search username / display name"
              style="width: 240px"
              @on-change="onMemberInputChange"
            />
            <Button @click="searchMembers" :loading="searchingUsers">Search</Button>
            <Button type="primary" :loading="memberBusy" @click="addMember">Add</Button>
          </Space>
        </FormItem>

        <FormItem v-if="userCandidates.length > 0" label="Candidates">
          <Space wrap>
            <Tag
              v-for="candidate in userCandidates"
              :key="candidate.id"
              color="blue"
              style="cursor: pointer"
              @click="selectCandidate(candidate)"
            >
              {{ candidate.username }}
            </Tag>
            <Button
              v-if="editTargetProject && isOwner(editTargetProject) && selectedCandidate"
              size="small"
              type="warning"
              ghost
              :loading="memberBusy"
              @click="grantMemberManager(selectedCandidate)"
            >
              Grant Add Permission
            </Button>
          </Space>
        </FormItem>
      </Form>
      <template #footer>
        <Button @click="showEditDrawer = false">Cancel</Button>
        <Button type="primary" :loading="editSaving" @click="saveProjectEdit">Save</Button>
      </template>
    </Drawer>

    <Modal v-model="showDeleteModal" title="Delete Project" :mask-closable="false">
      <p v-if="pendingDeleteProject">
        Confirm delete project: <strong>{{ pendingDeleteProject.name }}</strong> ?
      </p>
      <p>This action cannot be undone.</p>
      <template #footer>
        <Button @click="showDeleteModal = false">Cancel</Button>
        <Button type="error" :loading="deleting" @click="confirmDeleteProject">Delete</Button>
      </template>
    </Modal>

    <Modal v-model="showMemberModal" title="Manage Members" width="680">
      <div v-if="selectedProject">
        <p><strong>Project:</strong> {{ selectedProject.name }}</p>
        <Form v-if="canAddMembers(selectedProject)" inline>
          <FormItem>
            <Input
              v-model="memberInput"
              placeholder="Search username / display name"
              style="width: 280px"
              @on-change="onMemberInputChange"
            />
          </FormItem>
          <FormItem>
            <Button @click="searchMembers" :loading="searchingUsers">Search</Button>
          </FormItem>
          <FormItem>
            <Button type="primary" :loading="memberBusy" @click="addMember">Add Member</Button>
          </FormItem>
        </Form>
        <List v-if="userCandidates.length > 0" border size="small" style="margin-bottom: 12px">
          <ListItem v-for="candidate in userCandidates" :key="candidate.id">
            <Space>
              <Tag color="blue">{{ candidate.username }}</Tag>
              <span>{{ candidate.display_name }}</span>
              <span>{{ candidate.id }}</span>
              <Button size="small" @click="selectCandidate(candidate)">Select</Button>
              <Button
                v-if="selectedProject && isOwner(selectedProject)"
                size="small"
                type="warning"
                ghost
                @click="grantMemberManager(candidate)"
              >
                Grant Add Permission
              </Button>
            </Space>
          </ListItem>
        </List>
        <Divider v-if="selectedProject && isOwner(selectedProject)" />
        <div v-if="selectedProject && isOwner(selectedProject)">
          <p><strong>Delegated Add-Member Permission</strong></p>
          <Space wrap>
            <Tag
              v-for="(memberId, idx) in selectedProject.member_managers || []"
              :key="memberId"
              color="orange"
            >
              {{ (selectedProject.member_manager_names && selectedProject.member_manager_names[idx]) || memberId }}
              <Icon
                type="md-close"
                style="margin-left: 8px; cursor: pointer"
                @click="revokeMemberManager(memberId)"
              />
            </Tag>
          </Space>
        </div>
        <Divider />
        <Space wrap>
          <Tag v-for="(member, idx) in selectedProject.members" :key="member" color="cyan">
            {{ (selectedProject.member_names && selectedProject.member_names[idx]) || member }}
            <Icon
              v-if="isOwner(selectedProject) && member !== selectedProject.owner_id"
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
import { authState } from "../stores/auth";

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
const searchingUsers = ref(false);
const userCandidates = ref([]);
const selectedCandidate = ref(null);
const showEditDrawer = ref(false);
const editSaving = ref(false);
const deleting = ref(false);
const showDeleteModal = ref(false);
const pendingDeleteProject = ref(null);
const editForm = ref({ id: "", ownerName: "", name: "", description: "" });

const columns = [
  { title: "Name", slot: "name", minWidth: 200 },
  { title: "Description", key: "description", minWidth: 240 },
  { title: "Owner", slot: "owner", minWidth: 140 },
  { title: "Members", slot: "members", minWidth: 200 },
  { title: "ID", key: "id", minWidth: 280 },
  { title: "Action", slot: "action", minWidth: 260 }
];

const currentUserId = computed(() => authState.user?.id || "");
const editTargetProject = computed(() => projects.value.find((item) => item.id === editForm.value.id) || null);
const editProjectMembers = computed(() => editTargetProject.value?.members || []);
const editProjectMemberNames = computed(() => editTargetProject.value?.member_names || []);

function isOwner(project) {
  return !!project && !!currentUserId.value && project.owner_id === currentUserId.value;
}

function canAddMembers(project) {
  if (!project || !currentUserId.value) {
    return false;
  }
  if (project.owner_id === currentUserId.value) {
    return true;
  }
  return (project.member_managers || []).includes(currentUserId.value);
}

function displayMemberName(row, idx) {
  return (row.member_names && row.member_names[idx]) || row.members[idx];
}

function visibleMembers(row) {
  return (row.members || []).slice(0, 2);
}

function hiddenMemberNames(row) {
  const members = row.members || [];
  const names = row.member_names || [];
  return members.slice(2).map((member, idx) => names[idx + 2] || member);
}

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
    const list = await api.listProjects();
    projects.value = list;
    if (selectedProject.value) {
      selectedProject.value = list.find((item) => item.id === selectedProject.value.id) || selectedProject.value;
    }
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
  if (!canAddMembers(project)) {
    Message.warning("No permission to manage members");
    return;
  }
  selectedProject.value = project;
  memberInput.value = "";
  userCandidates.value = [];
  selectedCandidate.value = null;
  showMemberModal.value = true;
}

function openDetail(project) {
  router.push({ name: "project-detail", params: { projectId: project.id } });
}

async function addMember() {
  if (!selectedProject.value) {
    return;
  }
  if (!canAddMembers(selectedProject.value)) {
    Message.warning("No permission to add members");
    return;
  }
  const inputText = memberInput.value.trim();
  if (!selectedCandidate.value && !inputText) {
    Message.warning("Please search and select a user or input username");
    return;
  }

  memberBusy.value = true;
  try {
    const payload = selectedCandidate.value
      ? { user_id: selectedCandidate.value.id }
      : { account: inputText };
    const updated = await api.addProjectMember(selectedProject.value.id, payload);
    Message.success("Member added");
    selectedProject.value = updated;
    memberInput.value = "";
    userCandidates.value = [];
    selectedCandidate.value = null;
    await loadProjects();
  } catch (error) {
    Message.error(error.message || "Add member failed");
  } finally {
    memberBusy.value = false;
  }
}

function onMemberInputChange() {
  selectedCandidate.value = null;
}

function selectCandidate(candidate) {
  selectedCandidate.value = candidate;
  memberInput.value = candidate.username;
  Message.success(`Selected ${candidate.username}`);
}

async function searchMembers() {
  const q = memberInput.value.trim();
  if (!q) {
    userCandidates.value = [];
    return;
  }

  searchingUsers.value = true;
  try {
    userCandidates.value = await api.searchUsers(q, 10);
    if (userCandidates.value.length === 0) {
      Message.info("No matched users");
    }
  } catch (error) {
    Message.error(error.message || "Search users failed");
  } finally {
    searchingUsers.value = false;
  }
}

async function removeMember(memberId) {
  if (!selectedProject.value) {
    return;
  }
  if (!isOwner(selectedProject.value)) {
    Message.warning("Only owner can remove members");
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

async function grantMemberManager(candidate) {
  if (!selectedProject.value || !isOwner(selectedProject.value)) {
    Message.warning("Only owner can grant add-member permission");
    return;
  }

  memberBusy.value = true;
  try {
    const payload = candidate ? { user_id: candidate.id } : { account: memberInput.value.trim() };
    const updated = await api.grantProjectMemberManager(selectedProject.value.id, payload);
    Message.success("Grant succeeded");
    selectedProject.value = updated;
    await loadProjects();
  } catch (error) {
    Message.error(error.message || "Grant failed");
  } finally {
    memberBusy.value = false;
  }
}

async function revokeMemberManager(memberId) {
  if (!selectedProject.value || !isOwner(selectedProject.value)) {
    Message.warning("Only owner can revoke add-member permission");
    return;
  }

  memberBusy.value = true;
  try {
    const updated = await api.revokeProjectMemberManager(selectedProject.value.id, memberId);
    Message.success("Revoke succeeded");
    selectedProject.value = updated;
    await loadProjects();
  } catch (error) {
    Message.error(error.message || "Revoke failed");
  } finally {
    memberBusy.value = false;
  }
}

function openEditDrawer(project) {
  selectedProject.value = project;
  memberInput.value = "";
  userCandidates.value = [];
  selectedCandidate.value = null;
  editForm.value = {
    id: project.id,
    ownerName: project.owner_name || project.owner_id,
    name: project.name || "",
    description: project.description || ""
  };
  showEditDrawer.value = true;
}

async function saveProjectEdit() {
  if (!editForm.value.id) {
    return;
  }
  const nextName = editForm.value.name.trim();
  if (nextName.length < 2) {
    Message.warning("Project name requires at least 2 chars");
    return;
  }

  editSaving.value = true;
  try {
    await api.updateProject(editForm.value.id, {
      name: nextName,
      description: editForm.value.description
    });
    Message.success("Project updated");
    showEditDrawer.value = false;
    await loadProjects();
  } catch (error) {
    Message.error(error.message || "Update project failed");
  } finally {
    editSaving.value = false;
  }
}

function openDeleteModal(project) {
  pendingDeleteProject.value = project;
  showDeleteModal.value = true;
}

async function confirmDeleteProject() {
  if (!pendingDeleteProject.value) {
    return;
  }

  deleting.value = true;
  try {
    const projectId = pendingDeleteProject.value.id;
    await api.deleteProject(projectId);
    Message.success("Project deleted");
    if (selectedProject.value && selectedProject.value.id === projectId) {
      showMemberModal.value = false;
      selectedProject.value = null;
    }
    showDeleteModal.value = false;
    pendingDeleteProject.value = null;
    await loadProjects();
  } catch (error) {
    Message.error(error.message || "Delete project failed");
  } finally {
    deleting.value = false;
  }
}

onMounted(loadProjects);
</script>
