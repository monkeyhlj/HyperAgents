<template>
  <div class="workbench-shell">
    <aside class="workbench-panel project-panel">
      <div class="panel-title-row">
        <div>
          <p class="eyebrow">Workspace</p>
          <h2>Projects</h2>
        </div>
        <Button size="small" :loading="loadingSessions" @click="loadSessions">Sync</Button>
      </div>

      <Input v-model="projectQuery" clearable search placeholder="Search project" />

      <div class="project-list">
        <button
          v-for="project in filteredProjects"
          :key="project.id"
          type="button"
          class="project-item"
          :class="{ active: selectedProject?.id === project.id }"
          @click="selectProject(project)"
        >
          <span class="project-dot"></span>
          <span class="project-name">{{ project.name }}</span>
          <small>{{ shortId(project.id) }}</small>
        </button>
        <div v-if="filteredProjects.length === 0" class="mini-empty">No project matched</div>
      </div>

      <div class="session-create">
        <Input v-model="sessionTitle" placeholder="New session title" />
        <Button long type="primary" :loading="creatingSession" @click="createSession">New Chat</Button>
      </div>

      <div class="section-divider"></div>

      <div class="panel-title-row compact">
        <div>
          <p class="eyebrow">History</p>
          <h3>Sessions</h3>
        </div>
        <Button size="small" :loading="loadingSessions" @click="loadSessions">Refresh</Button>
      </div>
      <div class="session-list">
        <button
          v-for="session in sessions"
          :key="session.id"
          type="button"
          class="session-item"
          :class="{ active: sessionId === session.id }"
          @click="openSession(session.id)"
        >
          <Icon type="ios-chatbubble-outline" />
          <span>{{ session.title || 'Untitled session' }}</span>
          <small>{{ shortId(session.id) }}</small>
        </button>
        <div v-if="sessions.length === 0" class="mini-empty">No sessions yet</div>
      </div>
    </aside>

    <main class="chat-panel">
      <div class="chat-topbar">
        <div>
          <p class="eyebrow">Workbench Chat</p>
          <h2>{{ selectedProject?.name || 'Select a project' }}</h2>
          <span v-if="sessionId" class="subline">Session {{ shortId(sessionId) }}</span>
          <span v-else class="subline">A session will be created automatically when you send.</span>
        </div>
        <div class="agent-select-wrap">
          <Select v-model="agentId" clearable filterable placeholder="Agent optional" :loading="loadingAgents">
            <Option v-for="agent in agents" :key="agent.id" :value="agent.id">
              {{ agent.name }} · {{ shortId(agent.id) }}
            </Option>
          </Select>
          <Button :loading="loadingAgents" @click="loadAgents">Agents</Button>
        </div>
      </div>

      <div ref="chatStreamRef" class="chat-stream">
        <div v-if="history.length === 0" class="chat-welcome">
          <div class="welcome-mark">HA</div>
          <h1>Ask your agent anything.</h1>
          <p>Choose a project, optionally bind an agent, then test skills, tools, MCPs, knowledge, and file outputs in one calm surface.</p>
          <div class="prompt-chips">
            <button type="button" @click="message = '你有哪些 skills？'">你有哪些 skills？</button>
            <button type="button" @click="message = '使用 xlsx skill 帮我生成一个项目排期表，包含任务、负责人、开始日期、结束日期、状态'">Generate spreadsheet</button>
            <button type="button" @click="message = '使用 front-design skill 帮我设计一个高端产品官网首页'">Design homepage</button>
          </div>
        </div>

        <div v-for="(item, index) in history" :key="index" class="message-row" :class="`role-${item.role}`">
          <div class="message-avatar">{{ item.role === 'user' ? 'U' : 'AI' }}</div>
          <div class="message-bubble">
            <div class="message-meta">
              <strong>{{ roleLabel(item.role) }}</strong>
              <span v-if="item.role === 'assistant'">Agent: {{ messageAgentLabel(item) }}</span>
              <span v-if="item.used_skills?.length">Skill: {{ item.used_skills.join(', ') }}</span>
            </div>
            <p v-if="item.role === 'user'" class="plain-message">{{ item.text }}</p>
            <div v-else-if="item.pending" class="assistant-loading">
              <span>Assistant is thinking</span>
              <i></i><i></i><i></i>
            </div>
            <div v-else>
              <div class="capability-tags" v-if="capabilityTags(item).length">
                <Tag v-for="tag in capabilityTags(item)" :key="tag.key" :color="tag.color">{{ tag.label }}</Tag>
              </div>
              <div class="markdown-content" v-html="renderMarkdown(item.text)" @click="onMarkdownClick"></div>
            </div>
          </div>
        </div>
      </div>

      <div class="composer">
        <Input
          v-model="message"
          type="textarea"
          :rows="3"
          placeholder="Message HyperAgents..."
          @keydown.enter.ctrl.prevent="sendMessage"
        />
        <div class="composer-footer">
          <span>{{ selectedAgent ? `Agent: ${selectedAgent.name}` : 'No agent selected' }}</span>
          <Button type="primary" :loading="sending" :disabled="!message.trim()" @click="sendMessage">
            Send
          </Button>
        </div>
      </div>
    </main>

    <aside class="workbench-panel run-panel">
      <div class="panel-title-row">
        <div>
          <p class="eyebrow">Runtime</p>
          <h2>Trace</h2>
        </div>
        <Button size="small" :disabled="!sessionId" @click="loadRuns">Refresh</Button>
      </div>

      <div class="run-list">
        <button
          v-for="run in runs"
          :key="run.id"
          type="button"
          class="run-item"
          :class="{ active: currentRunId === run.id }"
          @click="openRun(run.id)"
        >
          <Tag :color="run.status === 'succeeded' ? 'green' : run.status === 'failed' ? 'red' : 'blue'">
            {{ run.status }}
          </Tag>
          <span>{{ shortId(run.id) }}</span>
        </button>
        <div v-if="runs.length === 0" class="mini-empty">No runs yet</div>
      </div>

      <div class="section-divider"></div>

      <Timeline class="event-timeline">
        <TimelineItem
          v-for="event in runEvents"
          :key="event.id"
          :color="eventColor(event.status)"
        >
          <div class="event-card">
            <strong>{{ event.stage }}</strong>
            <Tag :color="eventColor(event.status)">{{ event.status }}</Tag>
            <p>{{ event.message }}</p>
          </div>
        </TimelineItem>
      </Timeline>
      <div v-if="runEvents.length === 0" class="mini-empty large">Open a run to inspect events</div>
    </aside>
  </div>
</template>
<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
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
const currentRunId = ref("");
const chatStreamRef = ref(null);

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

function extractStandaloneHtml(text) {
  const value = String(text || "").trim();
  if (!value || value.startsWith("```")) {
    return "";
  }

  const normalized = value.toLowerCase();
  const htmlStart = normalized.search(/<!doctype\s+html|<html[\s>]/);
  if (htmlStart >= 0) {
    return value.slice(htmlStart);
  }

  if (normalized.includes("<style") && normalized.includes("</style>") && normalized.includes("<body")) {
    return value;
  }

  return "";
}

function normalizeAssistantMarkdown(text) {
  const value = String(text || "");
  const html = extractStandaloneHtml(value);
  if (html) {
    return `\`\`\`html\n${html}\n\`\`\``;
  }
  return value;
}

function renderMarkdown(text) {
  const rawHtml = marked.parse(normalizeAssistantMarkdown(text), { renderer: markdownRenderer });
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

const selectedAgent = computed(() => agents.value.find((item) => item.id === agentId.value) || null);

function shortId(value) {
  const text = String(value || "");
  if (!text) return "-";
  return text.length > 10 ? `${text.slice(0, 6)}...${text.slice(-4)}` : text;
}

function roleLabel(role) {
  return role === "user" ? "You" : "Assistant";
}

function messageAgentLabel(item) {
  if (item.agent_name) {
    return item.agent_name;
  }
  if (item.agent_id) {
    const matched = agents.value.find((agent) => agent.id === item.agent_id);
    return matched?.name || shortId(item.agent_id);
  }
  return "No agent selected";
}

function eventColor(status) {
  if (status === "succeeded" || status === "completed") return "green";
  if (status === "failed" || status === "error") return "red";
  if (status === "skipped") return "orange";
  return "blue";
}

function capabilityTags(item) {
  const tags = [];
  for (const skill of item.used_skills || []) tags.push({ key: `skill-${skill}`, color: "purple", label: `skill: ${skill}` });
  for (const tool of item.used_tools || []) tags.push({ key: `tool-${tool}`, color: "orange", label: `tool: ${tool}` });
  for (const kb of item.used_knowledge_bases || []) tags.push({ key: `kb-${kb}`, color: "cyan", label: `kb: ${kb}` });
  for (const call of item.used_mcps || []) tags.push({ key: `mcp-${call.mcp || ""}-${call.tool || ""}`, color: "geekblue", label: `mcp: ${call.mcp || "-"}/${call.tool || "-"}` });
  return tags;
}

async function scrollChatToBottom() {
  await nextTick();
  const el = chatStreamRef.value;
  if (el) {
    el.scrollTop = el.scrollHeight;
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
  if (!message.value.trim() || sending.value) {
    return;
  }

  sending.value = true;
  const textToSend = message.value;
  message.value = "";
  const pendingMessage = {
    role: "assistant",
    text: "",
    pending: true,
    agent_id: agentId.value || null,
    agent_name: selectedAgent.value?.name || null,
    used_tools: [],
    used_mcps: [],
    used_knowledge_bases: [],
    used_skills: []
  };
  history.value.push({ role: "user", text: textToSend }, pendingMessage);
  await scrollChatToBottom();

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
    Object.assign(pendingMessage, {
      role: data.role || "assistant",
      agent_id: data.agent_id || agentId.value || null,
      agent_name: data.agent_name || selectedAgent.value?.name || null,
      text: data.text || "[empty response]",
      pending: false,
      used_tools: data.used_tools || [],
      used_mcps: data.used_mcps || [],
      used_knowledge_bases: data.used_knowledge_bases || [],
      used_skills: data.used_skills || []
    });
    await scrollChatToBottom();
    await loadRuns();
  } catch (error) {
    pendingMessage.pending = false;
    pendingMessage.text = `Request failed: ${error.message || "Send message failed"}`;
    Message.error(error.message || "Send message failed");
    await scrollChatToBottom();
  } finally {
    sending.value = false;
  }
}
onMounted(async () => {
  await loadProjects();
  await loadAgents();
});
</script>

<style scoped>
.workbench-shell {
  height: calc(100vh - 124px);
  min-height: 720px;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 320px;
  gap: 16px;
}

.workbench-panel,
.chat-panel {
  min-height: 0;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: var(--shadow-sm);
}

.workbench-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  overflow: hidden;
}

.panel-title-row,
.chat-topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.panel-title-row h2,
.panel-title-row h3,
.chat-topbar h2 {
  margin: 0;
  color: var(--ink);
  line-height: 1.15;
}

.panel-title-row h2,
.chat-topbar h2 { font-size: 20px; }
.panel-title-row h3 { font-size: 15px; }
.panel-title-row.compact { align-items: center; }

.eyebrow {
  margin: 0 0 5px;
  color: var(--accent);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.subline {
  display: block;
  margin-top: 5px;
  color: var(--muted);
  font-size: 12px;
}

.project-list,
.session-list,
.run-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: auto;
  padding-right: 2px;
}

.project-list { max-height: 220px; }
.session-list { flex: 1; }
.run-list { max-height: 210px; }

.project-item,
.session-item,
.run-item {
  width: 100%;
  border: 1px solid transparent;
  border-radius: 8px;
  background: var(--surface-soft);
  color: var(--ink);
  cursor: pointer;
  text-align: left;
  transition: all 0.15s ease;
}

.project-item {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr);
  gap: 8px 10px;
  align-items: center;
  padding: 11px 12px;
}

.project-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
}

.project-name,
.session-item span,
.run-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 750;
}

.project-item small {
  grid-column: 2;
  color: var(--muted);
}

.session-item,
.run-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 11px;
}

.session-item small {
  margin-left: auto;
  color: var(--muted);
  font-size: 11px;
}

.project-item:hover,
.session-item:hover,
.run-item:hover,
.project-item.active,
.session-item.active,
.run-item.active {
  border-color: rgba(15, 118, 110, 0.25);
  background: #edf7f5;
}

.session-create {
  display: grid;
  gap: 8px;
}

.section-divider {
  height: 1px;
  background: var(--line);
  margin: 2px 0;
}

.chat-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  overflow: hidden;
}

.chat-topbar {
  padding: 18px 20px;
  border-bottom: 1px solid var(--line);
  background: rgba(248, 250, 252, 0.78);
}

.agent-select-wrap {
  display: grid;
  grid-template-columns: minmax(220px, 320px) auto;
  gap: 8px;
  align-items: center;
}

.chat-stream {
  overflow: auto;
  padding: 26px min(5vw, 56px);
  background:
    linear-gradient(180deg, rgba(248, 250, 252, 0.72), rgba(255, 255, 255, 0.96));
}

.chat-welcome {
  max-width: 720px;
  margin: 10vh auto 0;
  text-align: center;
}

.welcome-mark {
  width: 54px;
  height: 54px;
  display: grid;
  place-items: center;
  margin: 0 auto 18px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--accent), var(--warning));
  color: #fff;
  font-weight: 900;
}

.chat-welcome h1 {
  margin: 0;
  font-size: clamp(32px, 5vw, 52px);
  line-height: 1.05;
  letter-spacing: 0;
}

.chat-welcome p {
  max-width: 620px;
  margin: 16px auto 0;
  color: var(--muted);
  font-size: 15px;
  line-height: 1.8;
}

.prompt-chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  margin-top: 24px;
}

.prompt-chips button {
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #fff;
  padding: 9px 13px;
  color: var(--ink);
  cursor: pointer;
}

.message-row {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 12px;
  max-width: 880px;
  margin: 0 auto 22px;
}

.message-row.role-user {
  grid-template-columns: minmax(0, 1fr) 38px;
}

.message-row.role-user .message-avatar { grid-column: 2; background: #20304a; }
.message-row.role-user .message-bubble { grid-column: 1; grid-row: 1; justify-self: end; background: #ecf7f5; border-color: #cce8e3; }

.message-avatar {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  font-size: 12px;
  font-weight: 900;
}

.message-bubble {
  width: min(100%, 780px);
  padding: 14px 16px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  color: var(--muted);
  font-size: 12px;
}

.message-meta strong { color: var(--ink); }
.plain-message { margin: 0; white-space: pre-wrap; line-height: 1.7; }
.capability-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }

.assistant-loading {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 26px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
}

.assistant-loading i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  animation: assistant-pulse 1s infinite ease-in-out;
}

.assistant-loading i:nth-child(3) {
  animation-delay: 0.15s;
}

.assistant-loading i:nth-child(4) {
  animation-delay: 0.3s;
}

@keyframes assistant-pulse {
  0%, 80%, 100% {
    opacity: 0.25;
    transform: translateY(0);
  }
  40% {
    opacity: 1;
    transform: translateY(-3px);
  }
}

.composer {
  padding: 14px 18px 16px;
  border-top: 1px solid var(--line);
  background: #fff;
}

.composer :deep(textarea) {
  resize: none;
  border-radius: 8px;
  padding: 12px 13px;
  font-size: 14px;
}

.composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
  color: var(--muted);
  font-size: 12px;
}

.event-timeline {
  overflow: auto;
  padding: 4px 2px 0;
}

.event-card {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface-soft);
  padding: 10px;
}

.event-card strong {
  display: inline-block;
  margin-right: 6px;
}

.event-card p {
  margin: 8px 0 0;
  color: var(--muted);
  line-height: 1.5;
}

.mini-empty {
  color: var(--muted);
  text-align: center;
  padding: 14px;
  border: 1px dashed var(--line-strong);
  border-radius: 8px;
  background: var(--surface-soft);
  font-size: 12px;
}

.mini-empty.large { margin-top: 20px; padding: 28px 12px; }

@media (max-width: 1280px) {
  .workbench-shell {
    height: auto;
    min-height: 0;
    grid-template-columns: 260px minmax(0, 1fr);
  }
  .run-panel { grid-column: 1 / -1; min-height: 320px; }
}

@media (max-width: 900px) {
  .workbench-shell { grid-template-columns: 1fr; }
  .chat-panel { min-height: 720px; }
  .agent-select-wrap { grid-template-columns: 1fr; width: 100%; }
  .chat-topbar { display: grid; }
  .message-row,
  .message-row.role-user { grid-template-columns: 34px minmax(0, 1fr); }
  .message-row.role-user .message-avatar { grid-column: 1; }
  .message-row.role-user .message-bubble { grid-column: 2; justify-self: stretch; }
}
</style>