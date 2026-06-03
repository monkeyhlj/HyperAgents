<template>
  <div>
    <Card dis-hover>
      <template #title>Project Resources</template>
      <Form inline>
        <FormItem>
          <Input v-model="projectId" placeholder="Project ID" style="width: 360px" />
        </FormItem>
        <FormItem>
          <Button type="primary" @click="loadResources" :loading="loading">Load</Button>
        </FormItem>
      </Form>
      <Divider />
      <Form :model="form" inline>
        <FormItem>
          <Select v-model="form.kind" style="width: 160px">
            <Option v-for="item in kinds" :key="item" :value="item">{{ item }}</Option>
          </Select>
        </FormItem>
        <FormItem>
          <Input v-model="form.name" placeholder="Resource name" style="width: 220px" />
        </FormItem>
        <FormItem>
          <Select v-model="form.visibility" style="width: 130px">
            <Option value="private">private</Option>
            <Option value="project">project</Option>
            <Option value="public">public</Option>
          </Select>
        </FormItem>
        <FormItem>
          <Input v-model="form.model_provider" placeholder="Model provider" style="width: 180px" />
        </FormItem>
        <FormItem>
          <Input v-model="form.model_name" placeholder="Model name" style="width: 180px" />
        </FormItem>
        <FormItem>
          <Button type="success" @click="createResource" :loading="creating">Create</Button>
        </FormItem>
      </Form>
    </Card>

    <Card class="mt16" dis-hover>
      <template #title>Resources</template>
      <Table :columns="columns" :data="resources" stripe />
    </Card>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { Message } from "view-ui-plus";
import { api } from "../services/api";

const projectId = ref("");
const resources = ref([]);
const loading = ref(false);
const creating = ref(false);

const kinds = ["agent", "workflow", "tool", "skill", "mcp", "knowledge_base"];

const form = ref({
  kind: "agent",
  name: "",
  visibility: "project",
  model_provider: "",
  model_name: ""
});

const columns = [
  { title: "Kind", key: "kind", width: 120 },
  { title: "Name", key: "name", minWidth: 180 },
  { title: "Visibility", key: "visibility", width: 120 },
  { title: "Model Provider", key: "model_provider", minWidth: 160 },
  { title: "Model Name", key: "model_name", minWidth: 180 },
  { title: "Owner", key: "owner_id", minWidth: 140 },
  { title: "ID", key: "id", minWidth: 280 }
];

async function loadResources() {
  if (!projectId.value) {
    Message.warning("Please input project ID");
    return;
  }

  loading.value = true;
  try {
    resources.value = await api.listResources(projectId.value);
  } catch (error) {
    Message.error(error.message || "Load resources failed");
  } finally {
    loading.value = false;
  }
}

async function createResource() {
  if (!projectId.value) {
    Message.warning("Please input project ID");
    return;
  }
  if (!form.value.name || form.value.name.length < 2) {
    Message.warning("Resource name requires at least 2 chars");
    return;
  }

  creating.value = true;
  try {
    await api.createResource(projectId.value, {
      ...form.value,
      description: "",
      model_provider: form.value.model_provider || null,
      model_name: form.value.model_name || null,
      config: {}
    });
    Message.success("Resource created");
    form.value.name = "";
    form.value.model_provider = "";
    form.value.model_name = "";
    await loadResources();
  } catch (error) {
    Message.error(error.message || "Create resource failed");
  } finally {
    creating.value = false;
  }
}
</script>
