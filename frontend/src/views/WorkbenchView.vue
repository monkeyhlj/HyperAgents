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
        <FormItem>
          <Button @click="loadAgents" :loading="loadingAgents">Load Agents</Button>
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
          <Select v-model="agentId" clearable placeholder="Select Agent (optional)" style="width: 320px">
            <Option v-for="agent in agents" :key="agent.id" :value="agent.id">
              {{ agent.name }} ({{ agent.id }})
            </Option>
          </Select>
        </FormItem>
        <FormItem>
          <Input v-model="message" placeholder="Type your prompt" style="width: 500px" @on-enter="sendMessage" />
        </FormItem>
        <FormItem>
          <Button type="success" :loading="sending" @click="sendMessage">Send</Button>
        </FormItem>
      </Form>
    </Card>

    <Card class="mt16" dis-hover>
      <template #title>Conversation</template>
      <Timeline>
        <TimelineItem v-for="(item, index) in history" :key="index" :color="item.role === 'user' ? 'blue' : 'green'">
          <p><strong>{{ item.role }}</strong></p>
          <p v-if="item.role === 'user'">{{ item.text }}</p>
          <div v-else>
            <div v-if="item.used_tools && item.used_tools.length > 0" style="margin-bottom: 8px">
              <Tag v-for="tool in item.used_tools" :key="tool" color="orange">{{ tool }}</Tag>
            </div>
            <div class="markdown-content" v-html="renderMarkdown(item.text)" @click="onMarkdownClick"></div>
          </div>
        </TimelineItem>
      </Timeline>
    </Card>

    <Card class="mt16" dis-hover>
      <template #title>Run Timeline</template>
      <List border size="small">
        <ListItem v-for="run in runs" :key="run.id">
          <Space>
            <Tag :color="run.status === 'succeeded' ? 'green' : run.status === 'failed' ? 'red' : 'blue'">
              {{ run.status }}
            </Tag>
            <span>{{ run.id }}</span>
            <Button size="small" @click="openRun(run.id)">Events</Button>
          </Space>
        </ListItem>
      </List>

      <Divider />
      <Timeline>
        <TimelineItem
          v-for="event in runEvents"
          :key="event.id"
          :color="event.status === 'succeeded' ? 'green' : event.status === 'failed' ? 'red' : 'blue'"
        >
          <p><strong>{{ event.stage }} / {{ event.status }}</strong></p>
          <p>{{ event.message }}</p>
        </TimelineItem>
      </Timeline>
    </Card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { marked } from "marked";
import DOMPurify from "dompurify";
import { Message } from "view-ui-plus";
import { api } from "../services/api";

const projects = ref([]);
const projectQuery = ref("");
const selectedProject = ref(null);
const sessionTitle = ref("default");
const sessionId = ref("");
const agentId = ref("");
const agents = ref([]);
const message = ref("");
const history = ref([]);
const creatingSession = ref(false);
const loadingSessions = ref(false);
const loadingAgents = ref(false);
const sending = ref(false);
const sessions = ref([]);
const runs = ref([]);
const runEvents = ref([]);

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function encodeCodePayload(text) {
  return btoa(unescape(encodeURIComponent(text)));
}

function decodeCodePayload(text) {
  return decodeURIComponent(escape(atob(text)));
}

const markdownRenderer = new marked.Renderer();

markdownRenderer.code = ({ text, lang }) => {
  const language = (lang || "text").trim() || "text";
  const safeCode = escapeHtml(text || "");
  const encoded = encodeCodePayload(text || "");
  return `
    <div class="md-code-block">
      <div class="md-code-header">
        <span class="md-code-lang">${escapeHtml(language)}</span>
        <button class="md-copy-btn" data-code="${encoded}" type="button">Copy</button>
      </div>
      <pre><code class="language-${escapeHtml(language)}">${safeCode}</code></pre>
    </div>
  `;
};

markdownRenderer.table = (header, body) => {
  return `
    <div class="md-table-wrap">
      <table>
        <thead>${header}</thead>
        <tbody>${body}</tbody>
      </table>
    </div>
  `;
};

function renderMarkdown(text) {
  const rawHtml = marked.parse(text || "", { renderer: markdownRenderer });
  return DOMPurify.sanitize(rawHtml, {
    ADD_ATTR: ["data-code"]
  });
}

async function onMarkdownClick(event) {
  const button = event.target.closest(".md-copy-btn");
  if (!button) {
    return;
  }

  const encoded = button.getAttribute("data-code");
  if (!encoded) {
    return;
  }

  try {
    const plainCode = decodeCodePayload(encoded);
    await navigator.clipboard.writeText(plainCode);
    Message.success("Code copied");
  } catch {
    Message.error("Copy failed");
  }
}

const filteredProjects = computed(() => {
  const q = projectQuery.value.trim().toLowerCase();
  if (!q) {
    return projects.value;
  }
  return projects.value.filter((item) => item.id.toLowerCase().includes(q) || item.name.toLowerCase().includes(q));
});

async function selectProject(project) {
  selectedProject.value = project;
  sessionId.value = "";
  sessions.value = [];
  history.value = [];
  runs.value = [];
  runEvents.value = [];
  agents.value = [];
  agentId.value = "";
  await loadAgents();
  await loadSessions();
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
    await loadRuns();
  } catch (error) {
    Message.error(error.message || "Create session failed");
  } finally {
    creatingSession.value = false;
  }
}

async function loadAgents() {
  if (!selectedProject.value) {
    Message.warning("Please select a project first");
    return;
  }

  loadingAgents.value = true;
  try {
    agents.value = await api.listProjectAgents(selectedProject.value.id);
  } catch (error) {
    Message.error(error.message || "Load agents failed");
  } finally {
    loadingAgents.value = false;
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
    await loadRuns();
    Message.success("Session loaded");
  } catch (error) {
    Message.error(error.message || "Load messages failed");
  }
}

async function loadRuns() {
  if (!sessionId.value) {
    return;
  }
  try {
    runs.value = await api.listRuns(sessionId.value);
    if (runs.value.length > 0) {
      await openRun(runs.value[0].id);
    } else {
      runEvents.value = [];
    }
  } catch (error) {
    Message.error(error.message || "Load run timeline failed");
  }
}

async function openRun(runId) {
  try {
    runEvents.value = await api.listRunEvents(runId);
  } catch (error) {
    Message.error(error.message || "Load run events failed");
  }
}

async function sendMessage() {
  if (!selectedProject.value) {
    Message.warning("Please select a project first");
    return;
  }
  if (!message.value.trim()) {
    return;
  }

  sending.value = true;
  const textToSend = message.value;
  history.value.push({ role: "user", text: textToSend });
  try {
    if (!sessionId.value) {
      const created = await api.createSession(selectedProject.value.id, sessionTitle.value || "default");
      sessionId.value = created.id;
      await loadSessions();
    }
    const data = await api.sendMessage(sessionId.value, {
      text: textToSend,
      agent_id: agentId.value || null
    });
    history.value.push({ role: data.role, text: data.text, used_tools: data.used_tools || [] });
    message.value = "";
    await loadRuns();
  } catch (error) {
    Message.error(error.message || "Send message failed");
  } finally {
    sending.value = false;
  }
}

onMounted(async () => {
  await loadProjects();
  await loadAgents();
});
</script>
