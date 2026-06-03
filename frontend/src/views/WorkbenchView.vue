<template>
  <section>
    <h2>Project Workbench Chat</h2>
    <form class="form" @submit.prevent="createSession">
      <input v-model="projectId" placeholder="Project ID" required />
      <input v-model="sessionTitle" placeholder="Session title" required />
      <button>Create Session</button>
    </form>

    <p v-if="sessionId">Session: {{ sessionId }}</p>

    <form class="form" @submit.prevent="sendMessage" v-if="sessionId">
      <input v-model="agentId" placeholder="Agent ID (optional)" />
      <input v-model="message" placeholder="Type your test prompt" required />
      <button>Send</button>
    </form>

    <ul class="list">
      <li v-for="(item, index) in history" :key="index" class="row">
        <strong>{{ item.role }}</strong>
        <span>{{ item.text }}</span>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { ref } from "vue";
import { API_BASE_URL } from "../config";

const headers = { "Content-Type": "application/json", "x-user-id": "demo-user" };

const projectId = ref("");
const sessionTitle = ref("default");
const sessionId = ref("");
const agentId = ref("");
const message = ref("");
const history = ref([]);

async function createSession() {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/chat/projects/${projectId.value}/sessions`,
    {
      method: "POST",
      headers,
      body: JSON.stringify({ title: sessionTitle.value })
    }
  );
  const data = await response.json();
  sessionId.value = data.id;
  history.value = [];
}

async function sendMessage() {
  history.value.push({ role: "user", text: message.value });
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions/${sessionId.value}/messages`, {
    method: "POST",
    headers,
    body: JSON.stringify({ text: message.value, agent_id: agentId.value || null })
  });
  const data = await response.json();
  history.value.push({ role: data.role, text: data.text });
  message.value = "";
}
</script>
