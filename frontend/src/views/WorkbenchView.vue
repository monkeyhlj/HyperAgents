<template>
  <div>
    <Card dis-hover>
      <template #title>Project Workbench Chat</template>
      <Form inline>
        <FormItem>
          <Input v-model="projectQuery" clearable placeholder="Filter project by id or name" style="width: 340px" />
        </FormItem>
        <FormItem>
          <Tag color="blue">Current: {{ selectedProject?.name || "none" }}</Tag>
        </FormItem>
        <FormItem>
          <Input v-model="sessionTitle" placeholder="Session title" style="width: 200px" />
        </FormItem>
        <FormItem>
          <Button type="primary" @click="createSession" :loading="creatingSession">Create Session</Button>
        </FormItem>
        <FormItem>
          <Button @click="loadSessions" :loading="loadingSessions">Load Sessions</Button>
        </FormItem>
      </Form>
      <List border size="small">
        <ListItem v-for="project in filteredProjects" :key="project.id">
          <Space>
            <Tag :color="selectedProject?.id === project.id ? 'green' : 'blue'">{{ project.name }}</Tag>
            <span>{{ project.id }}</span>
            <Button size="small" @click="selectProject(project)">Use</Button>
          </Space>
        </ListItem>
      </List>

      <Divider />
      <Alert v-if="sessionId" show-icon>Session ID: {{ sessionId }}</Alert>
      <Divider />
      <List border size="small">
        <ListItem v-for="session in sessions" :key="session.id">
          <Space>
            <Tag color="blue">{{ session.title }}</Tag>
            <span>{{ session.id }}</span>
            <Button size="small" @click="openSession(session.id)">Open</Button>
          </Space>
        </ListItem>
      </List>
      <Divider />
      <Form inline>
        <FormItem>
          <Input v-model="agentId" placeholder="Agent ID (optional)" style="width: 260px" />
        </FormItem>
        <FormItem>
          <Input v-model="message" placeholder="Type your prompt" style="width: 500px" @on-enter="sendMessage" />
        </FormItem>
        <FormItem>
          <Button type="success" :disabled="!sessionId" :loading="sending" @click="sendMessage">Send</Button>
        </FormItem>
      </Form>
    </Card>

    <Card class="mt16" dis-hover>
      <template #title>Conversation</template>
      <Timeline>
        <TimelineItem v-for="(item, index) in history" :key="index" :color="item.role === 'user' ? 'blue' : 'green'">
          <p><strong>{{ item.role }}</strong></p>
          <p>{{ item.text }}</p>
        </TimelineItem>
      </Timeline>
    </Card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { Message } from "view-ui-plus";
import { api } from "../services/api";

const projects = ref([]);
const projectQuery = ref("");
const selectedProject = ref(null);
const sessionTitle = ref("default");
const sessionId = ref("");
const agentId = ref("");
const message = ref("");
const history = ref([]);
const creatingSession = ref(false);
const loadingSessions = ref(false);
const sending = ref(false);
const sessions = ref([]);

const filteredProjects = computed(() => {
  const q = projectQuery.value.trim().toLowerCase();
  if (!q) {
    return projects.value;
  }
  return projects.value.filter((item) => item.id.toLowerCase().includes(q) || item.name.toLowerCase().includes(q));
});

function selectProject(project) {
  selectedProject.value = project;
  sessionId.value = "";
  sessions.value = [];
  history.value = [];
}

async function loadProjects() {
  try {
    projects.value = await api.listProjects();
    if (!selectedProject.value && projects.value.length > 0) {
      selectedProject.value = projects.value[0];
    }
  } catch (error) {
    Message.error(error.message || "Load projects failed");
  }
}

async function createSession() {
  if (!selectedProject.value) {
    Message.warning("Please select a project first");
    return;
  }

  creatingSession.value = true;
  try {
    const data = await api.createSession(selectedProject.value.id, sessionTitle.value || "default");
    sessionId.value = data.id;
    history.value = [];
    Message.success("Session created");
    await loadSessions();
  } catch (error) {
    Message.error(error.message || "Create session failed");
  } finally {
    creatingSession.value = false;
  }
}

async function loadSessions() {
  if (!selectedProject.value) {
    Message.warning("Please select a project first");
    return;
  }

  loadingSessions.value = true;
  try {
    sessions.value = await api.listSessions(selectedProject.value.id);
  } catch (error) {
    Message.error(error.message || "Load sessions failed");
  } finally {
    loadingSessions.value = false;
  }
}

async function openSession(id) {
  sessionId.value = id;
  try {
    history.value = await api.listMessages(id);
    Message.success("Session loaded");
  } catch (error) {
    Message.error(error.message || "Load messages failed");
  }
}

async function sendMessage() {
  if (!sessionId.value) {
    Message.warning("Please create a session first");
    return;
  }
  if (!message.value.trim()) {
    return;
  }

  sending.value = true;
  history.value.push({ role: "user", text: message.value });
  try {
    const data = await api.sendMessage(sessionId.value, {
      text: message.value,
      agent_id: agentId.value || null
    });
    history.value.push({ role: data.role, text: data.text });
    message.value = "";
  } catch (error) {
    Message.error(error.message || "Send message failed");
  } finally {
    sending.value = false;
  }
}

onMounted(loadProjects);
</script>
