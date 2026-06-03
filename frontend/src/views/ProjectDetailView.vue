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
          <DescriptionsItem label="Owner">{{ project.owner_id }}</DescriptionsItem>
          <DescriptionsItem label="Project ID">{{ project.id }}</DescriptionsItem>
          <DescriptionsItem label="Members">
            <Space wrap>
              <Tag v-for="member in project.members" :key="member" color="blue">{{ member }}</Tag>
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

      <Table :columns="columns" :data="filteredResources" stripe></Table>
    </Card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Message } from "view-ui-plus";
import { api } from "../services/api";

const route = useRoute();
const router = useRouter();

const project = ref(null);
const resources = ref([]);
const loadingProject = ref(false);
const loadingResources = ref(false);
const resourceQuery = ref("");

const columns = [
  { title: "Kind", key: "kind", width: 130 },
  { title: "Name", key: "name", minWidth: 180 },
  { title: "Visibility", key: "visibility", width: 120 },
  { title: "Model Provider", key: "model_provider", minWidth: 140 },
  { title: "Model Name", key: "model_name", minWidth: 160 },
  { title: "ID", key: "id", minWidth: 280 }
];

const projectId = computed(() => String(route.params.projectId || ""));

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
