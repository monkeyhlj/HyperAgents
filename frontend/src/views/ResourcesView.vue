<template>
  <section>
    <h2>Resource Registry (Project Scoped)</h2>
    <p>Use a project ID to manage Agent, Workflow, Tool, Skill, MCP, and Knowledge Base.</p>

    <form class="form" @submit.prevent="loadResources">
      <input v-model="projectId" placeholder="Project ID" required />
      <button>Load</button>
    </form>

    <form class="form" @submit.prevent="createResource" v-if="projectId">
      <select v-model="kind">
        <option value="agent">agent</option>
        <option value="workflow">workflow</option>
        <option value="tool">tool</option>
        <option value="skill">skill</option>
        <option value="mcp">mcp</option>
        <option value="knowledge_base">knowledge_base</option>
      </select>
      <input v-model="name" placeholder="Resource name" required />
      <select v-model="visibility">
        <option value="private">private</option>
        <option value="project">project</option>
        <option value="public">public</option>
      </select>
      <input v-model="modelProvider" placeholder="Model provider (optional)" />
      <input v-model="modelName" placeholder="Model name (optional)" />
      <button>Create Resource</button>
    </form>

    <ul class="list">
      <li v-for="resource in resources" :key="resource.id" class="row">
        <strong>{{ resource.kind }} / {{ resource.name }}</strong>
        <span>visibility: {{ resource.visibility }}</span>
        <small>model: {{ resource.model_provider || "-" }} {{ resource.model_name || "" }}</small>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { ref } from "vue";

const headers = { "Content-Type": "application/json", "x-user-id": "demo-user" };

const projectId = ref("");
const resources = ref([]);
const kind = ref("agent");
const name = ref("");
const visibility = ref("project");
const modelProvider = ref("");
const modelName = ref("");

async function loadResources() {
  const response = await fetch(`http://localhost:8000/api/v1/resources/projects/${projectId.value}`, {
    headers
  });
  resources.value = await response.json();
}

async function createResource() {
  await fetch(`http://localhost:8000/api/v1/resources/projects/${projectId.value}`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      kind: kind.value,
      name: name.value,
      description: "",
      visibility: visibility.value,
      model_provider: modelProvider.value || null,
      model_name: modelName.value || null,
      config: {}
    })
  });
  name.value = "";
  modelProvider.value = "";
  modelName.value = "";
  await loadResources();
}
</script>
