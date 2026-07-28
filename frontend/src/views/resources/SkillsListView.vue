<template>
  <div>
    <Card dis-hover>
      <template #title>
        <Space>
          <span>Skills</span>
          <Button type="primary" size="small" @click="goCreate">Add Skill</Button>
          <Button size="small" :loading="loading" @click="loadData">Refresh</Button>
        </Space>
      </template>

      <Form inline style="margin-bottom: 16px">
        <FormItem>
          <Input v-model="queryText" clearable placeholder="Search skill name/id" style="width: 280px" />
        </FormItem>
        <FormItem>
          <Select v-model="statusFilter" clearable placeholder="Filter by status" style="width: 180px">
            <Option label="Active" value="active"></Option>
            <Option label="Inactive" value="inactive"></Option>
            <Option label="Deprecated" value="deprecated"></Option>
          </Select>
        </FormItem>
        <FormItem>
          <Button @click="loadData" :loading="loading">Search</Button>
        </FormItem>
        <FormItem>
          <Tag color="cyan">Total: {{ filteredSkills.length }}</Tag>
        </FormItem>
      </Form>

      <Table :columns="columns" :data="pagedSkills" stripe>
        <template #version="{ row }">
          <Tag color="blue">{{ row.version }}</Tag>
        </template>
        <template #status="{ row }">
          <Tag :color="row.status === 'active' ? 'green' : 'default'">
            {{ row.status }}
          </Tag>
        </template>
        <template #capabilities="{ row }">
          <Space wrap>
            <Tag v-for="cap in (row.capabilities || [])" :key="cap" size="small">
              {{ cap }}
            </Tag>
          </Space>
        </template>
        <template #createdAt="{ row }">
          {{ new Date(row.created_at).toLocaleString() }}
        </template>
        <template #action="{ row }">
          <Space>
            <Button size="small" @click="openDetail(row)">Detail</Button>
            <Button size="small" type="primary" ghost @click="openEditPage(row)">Edit</Button>
            <Button size="small" type="error" ghost @click="openDelete(row)">Delete</Button>
          </Space>
        </template>
      </Table>
      <Page
        v-if="filteredSkills.length > pageSize"
        class="table-pagination"
        :total="filteredSkills.length"
        :current="skillPage"
        :page-size="pageSize"
        show-total
        @on-change="skillPage = $event"
      />

      <div v-if="filteredSkills.length === 0" style="text-align: center; padding: 40px">
        <p>No skills found. Create your first skill to get started.</p>
      </div>
    </Card>

    <!-- Detail Drawer -->
    <Drawer v-model="showDetail" :title="`Skill - ${current?.name || ''}`" width="560">
      <Descriptions v-if="current" :column="1" bordered>
        <DescriptionsItem label="Name">{{ current.name }}</DescriptionsItem>
        <DescriptionsItem label="Version">{{ current.version }}</DescriptionsItem>
        <DescriptionsItem label="Author">{{ current.author }}</DescriptionsItem>
        <DescriptionsItem label="Status">
          <Tag :color="current.status === 'active' ? 'green' : 'default'">
            {{ current.status }}
          </Tag>
        </DescriptionsItem>
        <DescriptionsItem label="Entrypoint">
          <code>{{ current.entrypoint }}</code>
        </DescriptionsItem>
        <DescriptionsItem label="Capabilities">
          <Space wrap>
            <Tag v-for="cap in (current.capabilities || [])" :key="cap">
              {{ cap }}
            </Tag>
          </Space>
        </DescriptionsItem>
        <DescriptionsItem label="Skill ID">{{ current.skill_id }}</DescriptionsItem>
        <DescriptionsItem label="Created At">
          {{ new Date(current.created_at).toLocaleString() }}
        </DescriptionsItem>
      </Descriptions>
    </Drawer>

    <!-- Delete Confirmation Modal -->
    <Modal v-model="showDeleteConfirm" title="Delete Skill" width="400">
      <p>Confirm delete skill: <strong>{{ current?.name }}</strong>?</p>
      <p style="color: #ff4d4f">This action cannot be undone.</p>
      <template #footer>
        <Button @click="showDeleteConfirm = false">Cancel</Button>
        <Button type="error" :loading="deleting" @click="confirmDelete">Delete</Button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { Message, Modal } from "view-ui-plus";
import { api } from "../../services/api";
import { useProjectStore } from "../../stores/project";

const router = useRouter();
const projectStore = useProjectStore();

const skills = ref([]);
const skillPage = ref(1);
const pageSize = 10;
const loading = ref(false);
const deleting = ref(false);
const queryText = ref("");
const statusFilter = ref("");
const showDetail = ref(false);
const showDeleteConfirm = ref(false);
const current = ref(null);

const columns = computed(() => [
  {
    title: "Name",
    key: "name",
    width: 180,
    ellipsis: true,
  },
  {
    title: "Version",
    slot: "version",
    width: 100,
  },
  {
    title: "Author",
    key: "author",
    width: 120,
    ellipsis: true,
  },
  {
    title: "Status",
    slot: "status",
    width: 100,
  },
  {
    title: "Entrypoint",
    key: "entrypoint",
    width: 160,
    ellipsis: true,
  },
  {
    title: "Capabilities",
    slot: "capabilities",
    width: 200,
  },
  {
    title: "Created",
    slot: "createdAt",
    width: 160,
  },
  {
    title: "Action",
    slot: "action",
    width: 260,
    align: "center",
  },
]);

const pagedSkills = computed(() => {
  const start = (skillPage.value - 1) * pageSize;
  return filteredSkills.value.slice(start, start + pageSize);
});

const filteredSkills = computed(() => {
  return skills.value.filter((skill) => {
    const matchQuery =
      !queryText.value ||
      skill.name?.toLowerCase().includes(queryText.value.toLowerCase()) ||
      skill.skill_id?.includes(queryText.value);

    const matchStatus = !statusFilter.value || skill.status === statusFilter.value;

    return matchQuery && matchStatus;
  });
});

watch([queryText, statusFilter], () => { skillPage.value = 1; });

onMounted(() => {
  loadData();
});

async function loadData() {
  loading.value = true;
  try {
    const response = await api.listProjectSkills(projectStore.currentProject?.id || "");
    skills.value = response.skills || [];
    skillPage.value = 1;
  } catch (error) {
    Message.error("Failed to load skills");
    console.error(error);
  } finally {
    loading.value = false;
  }
}

function goCreate() {
  router.push({ name: "resources-create", params: { kind: "skill" } });
}

function openDetail(skill) {
  current.value = skill;
  showDetail.value = true;
}

function openEditPage(skill) {
  router.push({
    name: "resources-skill-detail",
    params: { resourceId: skill.skill_id },
  });
}

function openDelete(skill) {
  current.value = skill;
  showDeleteConfirm.value = true;
}

async function confirmDelete() {
  if (!current.value) return;

  deleting.value = true;
  try {
    await api.deleteResource(current.value.skill_id);
    Message.success("Skill deleted successfully");
    showDeleteConfirm.value = false;
    loadData();
  } catch (error) {
    Message.error("Failed to delete skill");
    console.error(error);
  } finally {
    deleting.value = false;
  }
}
</script>

<style scoped>
code {
  background-color: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
}
</style>
