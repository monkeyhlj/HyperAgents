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
          <Select v-model="selectedTemplateId" clearable filterable placeholder="Template (optional)" style="width: 260px">
            <Option v-for="item in templateOptions" :key="item.template_id" :value="item.template_id">
              {{ item.name }} ({{ item.kind }})
            </Option>
          </Select>
        </FormItem>
        <FormItem>
          <Button @click="applyTemplate" :disabled="!selectedTemplateId">Apply Template</Button>
        </FormItem>
        <FormItem>
          <span class="template-hint">OpenAI templates use OPENAI_API_KEY / OPENAI_BASE_URL from .env.</span>
        </FormItem>
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
          <Input v-model="form.provider_profile" placeholder="Provider profile" style="width: 180px" />
        </FormItem>
        <FormItem>
          <Button type="success" @click="createResource" :loading="creating">Create</Button>
        </FormItem>
      </Form>
    </Card>

    <Card class="mt16" dis-hover>
      <template #title>Resources</template>
      <Table :columns="columns" :data="resources" stripe>
        <template #action="{ row }">
          <Space>
            <Button size="small" :disabled="row.source === 'default'" @click="editResource(row)">Edit</Button>
            <Button size="small" type="error" ghost :disabled="row.source === 'default'" @click="deleteResource(row)">
              Delete
            </Button>
          </Space>
        </template>
      </Table>
    </Card>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { Message } from "view-ui-plus";
import { api } from "../services/api";

const projectId = ref("");
const resources = ref([]);
const templates = ref([]);
const selectedTemplateId = ref("");
const loading = ref(false);
const creating = ref(false);

const kinds = ["agent", "workflow", "tool", "skill", "mcp", "knowledge_base"];

const form = ref({
  kind: "agent",
  name: "",
  visibility: "project",
  model_provider: "",
  model_name: "",
  provider_profile: "",
  description: "",
  config: {}
});

const templateOptions = ref([]);

const columns = [
  { title: "Source", key: "source", width: 100 },
  { title: "Kind", key: "kind", width: 120 },
  { title: "Name", key: "name", minWidth: 180 },
  { title: "Visibility", key: "visibility", width: 120 },
  { title: "Model Provider", key: "model_provider", minWidth: 160 },
  { title: "Model Name", key: "model_name", minWidth: 180 },
  { title: "Owner", key: "owner_id", minWidth: 140 },
  { title: "ID", key: "id", minWidth: 280 },
  { title: "Action", slot: "action", width: 140 }
];

async function loadTemplates() {
  try {
    templates.value = await api.listDefaultResources();
    templateOptions.value = templates.value;
  } catch (error) {
    Message.error(error.message || "Load templates failed");
  }
}

function applyTemplate() {
  if (!selectedTemplateId.value) {
    return;
  }
  const template = templates.value.find((item) => item.template_id === selectedTemplateId.value);
  if (!template) {
    return;
  }
  form.value.kind = template.kind;
  form.value.name = template.name;
  form.value.visibility = template.visibility;
  form.value.model_provider = template.model_provider || "";
  form.value.model_name = template.model_name || "";
  form.value.provider_profile = template.provider_profile || "";
  form.value.description = template.description || "";
  form.value.config = template.config || {};
}

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
      description: form.value.description || "",
      model_provider: form.value.model_provider || null,
      model_name: form.value.model_name || null,
      provider_profile: form.value.provider_profile || null,
      config: form.value.config || {}
    });
    Message.success("Resource created");
    form.value.name = "";
    form.value.description = "";
    form.value.config = {};
    form.value.model_provider = "";
    form.value.model_name = "";
    form.value.provider_profile = "";
    await loadResources();
  } catch (error) {
    Message.error(error.message || "Create resource failed");
  } finally {
    creating.value = false;
  }
}

async function editResource(row) {
  if (row.source === "default") {
    Message.warning("Default templates cannot be edited directly");
    return;
  }

  const nextName = window.prompt("Resource name", row.name);
  if (nextName === null) {
    return;
  }
  const nextDescription = window.prompt("Resource description", row.description || "");
  if (nextDescription === null) {
    return;
  }

  try {
    await api.updateResource(row.id, {
      name: nextName.trim() || row.name,
      description: nextDescription,
      model_provider: row.model_provider,
      model_name: row.model_name,
      provider_profile: row.provider_profile
    });
    Message.success("Resource updated");
    await loadResources();
  } catch (error) {
    Message.error(error.message || "Update resource failed");
  }
}

async function deleteResource(row) {
  if (row.source === "default") {
    Message.warning("Default templates cannot be deleted");
    return;
  }
  const confirmed = window.confirm(`Delete resource ${row.name}?`);
  if (!confirmed) {
    return;
  }

  try {
    await api.deleteResource(row.id);
    Message.success("Resource deleted");
    await loadResources();
  } catch (error) {
    Message.error(error.message || "Delete resource failed");
  }
}

loadTemplates();
</script>
