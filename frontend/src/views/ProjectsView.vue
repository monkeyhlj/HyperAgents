<template>
  <section>
    <h2>Projects</h2>
    <form class="form" @submit.prevent="createProject">
      <input v-model="name" placeholder="Project name" required />
      <input v-model="description" placeholder="Description" />
      <button>Create</button>
    </form>

    <ul class="list">
      <li v-for="project in projects" :key="project.id" class="row">
        <strong>{{ project.name }}</strong>
        <span>{{ project.description }}</span>
        <small>ID: {{ project.id }}</small>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";

const api = "http://localhost:8000/api/v1/projects";
const headers = { "Content-Type": "application/json", "x-user-id": "demo-user" };

const name = ref("");
const description = ref("");
const projects = ref([]);

async function loadProjects() {
  const response = await fetch(api, { headers });
  projects.value = await response.json();
}

async function createProject() {
  await fetch(api, {
    method: "POST",
    headers,
    body: JSON.stringify({ name: name.value, description: description.value })
  });
  name.value = "";
  description.value = "";
  await loadProjects();
}

onMounted(loadProjects);
</script>
