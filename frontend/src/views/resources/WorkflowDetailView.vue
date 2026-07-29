<template>
  <div class="workflow-test-shell">
    <section class="workflow-chat-panel">
      <div class="workflow-chat-topbar">
        <div>
          <p class="eyebrow">Workflow Test</p>
          <h2>{{ workflow?.name || "Workflow" }}</h2>
          <span class="subline">{{ workflow?.description || `Workflow ${shortId(workflowId)}` }}</span>
        </div>
        <Space wrap>
          <Tag v-if="workflow" color="cyan">{{ workflow.visibility }}</Tag>
          <Button size="small" :loading="validating" @click="validateDefinition">Validate</Button>
          <Button size="small" type="primary" ghost @click="goEdit">Edit</Button>
          <Button size="small" @click="goBack">Back</Button>
        </Space>
      </div>

      <Alert v-if="loadError" type="error" show-icon class="result-alert">{{ loadError }}</Alert>
      <Alert v-if="validation" :type="validation.ok ? 'success' : 'error'" show-icon class="result-alert">
        {{ validation.ok ? 'Workflow definition is valid' : 'Workflow definition has errors' }}
        <template #desc>
          <div v-if="validation.errors?.length">Errors: {{ validation.errors.join('; ') }}</div>
          <div v-if="validation.warnings?.length">Warnings: {{ validation.warnings.join('; ') }}</div>
        </template>
      </Alert>
      <Spin v-if="loading" fix />

      <div ref="chatStreamRef" class="workflow-chat-stream">
        <div v-if="messages.length === 0" class="workflow-welcome">
          <div class="welcome-mark">WF</div>
          <h1>Run this workflow like a conversation.</h1>
          <p>Type a task in natural language. It will be sent as <code>{{ '{ "task": "..." }' }}</code> and each node will run in order or by graph dependencies.</p>
          <div class="prompt-chips">
            <button type="button" @click="message = '做一个关于如何养成阅读习惯的1分钟短视频，输出脚本、分镜和配乐建议'">短视频脚本</button>
            <button type="button" @click="message = '帮我分析这个客户问题，并给出处理建议和下一步动作'">客户问题分析</button>
            <button type="button" @click="message = '生成一个产品发布方案，包含目标用户、核心卖点和执行计划'">产品发布方案</button>
          </div>
        </div>

        <div v-for="item in messages" :key="item.id" class="message-row" :class="`role-${item.role}`">
          <div class="message-avatar">{{ item.role === 'user' ? 'U' : 'WF' }}</div>
          <div class="message-bubble">
            <div class="message-meta">
              <strong>{{ item.role === 'user' ? 'You' : 'Workflow' }}</strong>
              <span v-if="item.duration_ms !== undefined">{{ item.duration_ms || 0 }} ms</span>
              <Tag v-if="item.status" :color="statusColor(item.status)">{{ item.status }}</Tag>
            </div>
            <p v-if="item.role === 'user'" class="plain-message">{{ item.text }}</p>
            <div v-else-if="item.pending" class="assistant-loading">
              <span>Workflow is running</span>
              <i></i><i></i><i></i>
            </div>
            <template v-else>
              <div class="assistant-output markdown-content" v-html="renderMarkdown(formatWorkflowOutput(item.run))"></div>
              <Button v-if="item.run" size="small" type="primary" ghost @click="inspectRunSteps(item.run)">View Step Trace</Button>
            </template>
          </div>
        </div>
      </div>

      <div class="composer">
        <Input
          v-model="message"
          type="textarea"
          :rows="3"
          placeholder="输入 workflow 测试任务，例如：做一个关于如何养成阅读习惯的1分钟短视频"
          @keydown.enter.ctrl.prevent="runChatTest"
        />
        <div class="composer-footer">
          <span>发送后会作为 <code>input.task</code> 传入 workflow</span>
          <Space>
            <Button :disabled="running" @click="showAdvancedInput = !showAdvancedInput">{{ showAdvancedInput ? 'Hide JSON' : 'JSON Input' }}</Button>
            <Button type="primary" :loading="running" :disabled="!message.trim()" @click="runChatTest">Run</Button>
          </Space>
        </div>
        <div v-if="showAdvancedInput" class="advanced-input">
          <CodeEditor v-model="inputJson" language="json" min-height="140px" />
        </div>
        <Alert v-if="runError" type="error" show-icon class="result-alert">{{ runError }}</Alert>
      </div>
    </section>

    <aside ref="sidePanelRef" class="workflow-side-panel">
      <Card dis-hover class="side-card">
        <template #title>
          <Space>
            <span>Current Run</span>
            <Button size="small" :loading="runsLoading" @click="loadRuns">Refresh</Button>
          </Space>
        </template>
        <div v-if="currentRun" class="run-summary">
          <Tag :color="statusColor(currentRun.status)">{{ currentRun.status }}</Tag>
          <span>{{ currentRun.duration_ms || 0 }} ms</span>
          <small>{{ currentRun.id }}</small>
        </div>
        <Timeline v-if="currentRun?.steps?.length" class="step-timeline">
          <TimelineItem v-for="step in currentRun.steps" :key="step.id" :color="statusColor(step.status)">
            <div class="step-title">{{ step.step_name || step.step_id }} <Tag>{{ step.status }}</Tag></div>
            <div class="step-meta">Agent: {{ shortId(step.agent_id) }} · {{ step.duration_ms || 0 }} ms</div>
            <Collapse simple>
              <Panel :name="`${step.id}-input`">
                Input
                <template #content><pre class="json-preview compact">{{ stringify(step.input_data) }}</pre></template>
              </Panel>
              <Panel :name="`${step.id}-output`">
                Output
                <template #content><pre class="json-preview compact">{{ stringify(step.output_data || { error: step.error_message }) }}</pre></template>
              </Panel>
            </Collapse>
          </TimelineItem>
        </Timeline>
        <div v-else class="mini-empty">Run a workflow to inspect step outputs.</div>
      </Card>

      <Card dis-hover class="side-card">
        <template #title>Run History</template>
        <div class="run-list">
          <button
            v-for="run in runs"
            :key="run.id"
            type="button"
            class="run-item"
            :class="{ active: currentRun?.id === run.id }"
            @click="openRun(run)"
          >
            <Tag :color="statusColor(run.status)">{{ run.status }}</Tag>
            <span>{{ shortId(run.id) }}</span>
            <small>{{ run.duration_ms || 0 }} ms</small>
          </button>
          <div v-if="runs.length === 0" class="mini-empty">No runs yet</div>
        </div>
      </Card>

      <Card dis-hover class="side-card definition-card">
        <template #title>Definition</template>
        <CodeEditor :model-value="definitionJson" language="json" min-height="260px" readonly />
      </Card>
    </aside>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Message } from "view-ui-plus";
import { marked } from "marked";
import DOMPurify from "dompurify";
import CodeEditor from "../../components/CodeEditor.vue";
import { api } from "../../services/api";

defineOptions({ name: "WorkflowDetailView" });

const route = useRoute();
const router = useRouter();
const workflowId = computed(() => String(route.params.resourceId || ""));

const workflow = ref(null);
const loading = ref(false);
const loadError = ref("");
const validating = ref(false);
const validation = ref(null);
const running = ref(false);
const runError = ref("");
const currentRun = ref(null);
const runs = ref([]);
const runsLoading = ref(false);
const message = ref("");
const messages = ref([]);
const showAdvancedInput = ref(false);
const inputJson = ref("{\n  \"task\": \"\"\n}");
const chatStreamRef = ref(null);
const sidePanelRef = ref(null);
const activePendingMessage = ref(null);
const activePendingStartedAt = ref(0);
let runPollTimer = null;

const definitionJson = computed(() => stringify(workflow.value?.config || {}));

function stringify(value) {
  return JSON.stringify(value || {}, null, 2);
}

function renderMarkdown(text) {
  const rawHtml = marked.parse(String(text || ""));
  return DOMPurify.sanitize(rawHtml);
}

function shortId(value) {
  const text = String(value || "");
  if (!text) return "-";
  return text.length > 12 ? `${text.slice(0, 8)}...${text.slice(-4)}` : text;
}

function statusColor(status) {
  const map = { completed: "green", running: "blue", failed: "red", pending: "default" };
  return map[status] || "default";
}

function formatWorkflowOutput(run) {
  if (!run) return "";
  if (run.status === "failed") {
    return run.error_message || stringify(run.output_data || { status: "failed" });
  }
  const output = run.output_data || {};
  if (typeof output === "string") return output;
  if (typeof output.summary === "string") return output.summary;
  if (typeof output.output === "string") return output.output;
  return stringify(output);
}

function inputTextFromRun(run) {
  const input = run?.input_data || {};
  if (typeof input.task === "string") return input.task;
  if (typeof input.text === "string") return input.text;
  if (typeof input.prompt === "string") return input.prompt;
  return stringify(input);
}

function hasConversationRun(runId) {
  return messages.value.some((item) => item.run_id === runId || item.run?.id === runId);
}

async function applyRunToConversation(run, options = {}) {
  if (!run) return;
  currentRun.value = run;

  const pending = activePendingMessage.value;
  if (pending?.pending) {
    Object.assign(pending, {
      pending: false,
      run,
      run_id: run.id,
      status: run.status,
      duration_ms: run.duration_ms
    });
    activePendingMessage.value = null;
    stopRunPolling();
    await scrollChatToBottom();
    return;
  }

  const existing = messages.value.find((item) => item.run_id === run.id || item.run?.id === run.id);
  if (existing) {
    if (existing.role === "assistant") {
      Object.assign(existing, { pending: false, run, status: run.status, duration_ms: run.duration_ms });
    }
    await scrollChatToBottom();
    return;
  }

  if (options.addToChat !== false) {
    messages.value.push(
      { id: `user-history-${run.id}`, role: "user", text: inputTextFromRun(run), run_id: run.id },
      { id: `workflow-history-${run.id}`, role: "assistant", pending: false, run, run_id: run.id, status: run.status, duration_ms: run.duration_ms }
    );
    await scrollChatToBottom();
  }
}

function stopRunPolling() {
  if (runPollTimer) {
    clearInterval(runPollTimer);
    runPollTimer = null;
  }
}

function startRunPolling() {
  stopRunPolling();
  runPollTimer = window.setInterval(() => {
    loadRuns({ silent: true });
  }, 5000);
}

async function reconcilePendingFromRuns() {
  const pending = activePendingMessage.value;
  if (!pending?.pending) return;
  const threshold = activePendingStartedAt.value - 5000;
  const terminalRun = runs.value.find((run) => {
    const createdAt = Date.parse(run.created_at || "");
    return ["completed", "failed"].includes(run.status) && (!threshold || Number.isNaN(createdAt) || createdAt >= threshold);
  });
  if (!terminalRun) return;
  try {
    const detail = await api.getWorkflowRun(workflowId.value, terminalRun.id);
    await applyRunToConversation(detail);
  } catch {
    // Keep polling; the run detail may briefly lag behind the history row.
  }
}

async function scrollChatToBottom() {
  await nextTick();
  const el = chatStreamRef.value;
  if (el) el.scrollTop = el.scrollHeight;
}

async function inspectRunSteps(run) {
  if (!run) return;
  currentRun.value = run;
  await nextTick();
  if (sidePanelRef.value) {
    sidePanelRef.value.scrollTo({ top: 0, behavior: "smooth" });
  }
  Message.info("Step trace is shown in the right panel");
}

function goBack() {
  router.push({ name: "workflows" });
}

function goEdit() {
  router.push({ name: "workflows-edit", params: { resourceId: workflowId.value } });
}

async function loadWorkflow() {
  loading.value = true;
  loadError.value = "";
  try {
    workflow.value = await api.getResource(workflowId.value);
  } catch (error) {
    loadError.value = error.message || "Load workflow failed";
  } finally {
    loading.value = false;
  }
}

async function validateDefinition() {
  validating.value = true;
  validation.value = null;
  try {
    validation.value = await api.validateWorkflow(workflowId.value);
    if (validation.value.ok) Message.success("Workflow definition is valid");
    else Message.error("Workflow definition has errors");
  } catch (error) {
    Message.error(error.message || "Validate workflow failed");
  } finally {
    validating.value = false;
  }
}

function buildInputData(text) {
  if (!showAdvancedInput.value) {
    inputJson.value = JSON.stringify({ task: text }, null, 2);
    return { task: text };
  }
  const data = JSON.parse(inputJson.value || "{}");
  if (!data.task) data.task = text;
  return data;
}

async function runChatTest() {
  const text = message.value.trim();
  if (!text || running.value) return;

  let inputData;
  try {
    inputData = buildInputData(text);
  } catch {
    Message.error("Input JSON is invalid");
    return;
  }

  running.value = true;
  runError.value = "";
  message.value = "";
  const userMessage = { id: `user-${Date.now()}`, role: "user", text };
  const pendingMessage = { id: `workflow-${Date.now()}`, role: "assistant", pending: true, text: "" };
  activePendingMessage.value = pendingMessage;
  activePendingStartedAt.value = Date.now();
  messages.value.push(userMessage, pendingMessage);
  await scrollChatToBottom();
  startRunPolling();

  try {
    const result = await api.runWorkflow(workflowId.value, { input_data: inputData, trigger_type: "manual" });
    await applyRunToConversation(result);
    await loadRuns({ silent: true });
    if (result.status === "completed") Message.success("Workflow completed");
    else Message.error(result.error_message || "Workflow failed");
  } catch (error) {
    stopRunPolling();
    pendingMessage.pending = false;
    activePendingMessage.value = null;
    pendingMessage.status = "failed";
    pendingMessage.run = { status: "failed", error_message: error.message || "Run workflow failed" };
    runError.value = error.message || "Run workflow failed";
    Message.error(runError.value);
  } finally {
    running.value = false;
    await scrollChatToBottom();
  }
}

async function loadRuns(options = {}) {
  runsLoading.value = !options.silent;
  try {
    runs.value = await api.listWorkflowRuns(workflowId.value, { limit: 50 });
    await reconcilePendingFromRuns();
  } catch (error) {
    if (!options.silent) Message.error(error.message || "Load workflow runs failed");
  } finally {
    runsLoading.value = false;
  }
}

async function openRun(row) {
  try {
    const detail = await api.getWorkflowRun(workflowId.value, row.id);
    await applyRunToConversation(detail, { addToChat: true });
  } catch (error) {
    Message.error(error.message || "Load run detail failed");
  }
}

onMounted(async () => {
  await loadWorkflow();
  await loadRuns();
});

onUnmounted(stopRunPolling);
</script>

<style scoped>
.workflow-test-shell {
  height: calc(100vh - 124px);
  min-height: 720px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 16px;
}

.workflow-chat-panel,
.workflow-side-panel .side-card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: var(--shadow-sm);
}

.workflow-chat-panel {
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  overflow: hidden;
}

.workflow-chat-topbar {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
  padding: 18px 20px;
  border-bottom: 1px solid var(--line);
  background: rgba(248, 250, 252, 0.86);
}

.workflow-chat-topbar h2 {
  margin: 0;
  color: var(--ink);
  font-size: 22px;
  line-height: 1.15;
}

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
  margin-top: 6px;
  color: var(--muted);
  font-size: 12px;
}

.workflow-chat-stream {
  overflow: auto;
  padding: 28px min(5vw, 56px);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.72), rgba(255, 255, 255, 0.96));
}

.workflow-welcome {
  max-width: 760px;
  margin: 10vh auto 0;
  text-align: center;
}

.welcome-mark {
  width: 56px;
  height: 56px;
  display: grid;
  place-items: center;
  margin: 0 auto 18px;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--accent), var(--warning));
  color: #fff;
  font-weight: 900;
}

.workflow-welcome h1 {
  margin: 0;
  color: var(--ink);
  font-size: clamp(32px, 5vw, 52px);
  line-height: 1.05;
  letter-spacing: 0;
}

.workflow-welcome p {
  max-width: 640px;
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
  max-width: 900px;
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
  width: min(100%, 800px);
  padding: 14px 16px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
}

.message-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 8px;
  color: var(--muted);
  font-size: 12px;
}

.message-meta strong { color: var(--ink); }
.plain-message { margin: 0; white-space: pre-wrap; line-height: 1.7; }

.assistant-output {
  margin: 0 0 12px;
  color: var(--ink);
  line-height: 1.7;
}

.markdown-content :deep(p) {
  margin: 0 0 10px;
}

.markdown-content :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-content :deep(strong) {
  color: var(--ink);
  font-weight: 850;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 8px 0 12px 20px;
  padding: 0;
}

.markdown-content :deep(li) {
  margin: 4px 0;
}

.markdown-content :deep(code) {
  padding: 2px 5px;
  border-radius: 5px;
  background: #eef4fb;
  color: #20304a;
}

.markdown-content :deep(pre) {
  margin: 10px 0;
  padding: 12px;
  border: 1px solid #e3ebf6;
  border-radius: 8px;
  background: #f8fbff;
  overflow: auto;
}

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

.assistant-loading i:nth-child(3) { animation-delay: 0.15s; }
.assistant-loading i:nth-child(4) { animation-delay: 0.3s; }

@keyframes assistant-pulse {
  0%, 80%, 100% { opacity: 0.25; transform: translateY(0); }
  40% { opacity: 1; transform: translateY(-3px); }
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
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-top: 10px;
  color: var(--muted);
  font-size: 12px;
}

.advanced-input,
.result-alert { margin-top: 12px; }

.workflow-side-panel {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow: auto;
}

.side-card { flex: none; }
.definition-card { min-height: 320px; }

.run-summary {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  color: var(--muted);
}

.run-summary small { width: 100%; color: var(--muted); }

.run-list {
  display: grid;
  gap: 8px;
  max-height: 220px;
  overflow: auto;
}

.run-item {
  width: 100%;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  border: 1px solid transparent;
  border-radius: 8px;
  background: var(--surface-soft);
  color: var(--ink);
  cursor: pointer;
  padding: 10px;
  text-align: left;
}

.run-item:hover,
.run-item.active {
  border-color: rgba(15, 118, 110, 0.25);
  background: #edf7f5;
}

.run-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 750;
}

.run-item small { color: var(--muted); }

.json-preview {
  margin: 0;
  padding: 12px;
  border: 1px solid #e3ebf6;
  border-radius: 8px;
  background: #f8fbff;
  color: #18233a;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 360px;
  overflow: auto;
}

.json-preview.compact { max-height: 240px; }
.step-timeline { margin-top: 8px; }
.step-title { display: flex; gap: 8px; align-items: center; font-weight: 700; }
.step-meta { margin: 4px 0 8px; color: #718096; font-size: 13px; }

.mini-empty {
  color: var(--muted);
  text-align: center;
  padding: 18px 12px;
  border: 1px dashed var(--line-strong);
  border-radius: 8px;
  background: var(--surface-soft);
  font-size: 12px;
}

@media (max-width: 1180px) {
  .workflow-test-shell {
    height: auto;
    grid-template-columns: 1fr;
  }
  .workflow-chat-panel { min-height: 720px; }
}

@media (max-width: 760px) {
  .workflow-chat-topbar,
  .composer-footer { display: grid; }
  .message-row,
  .message-row.role-user { grid-template-columns: 34px minmax(0, 1fr); }
  .message-row.role-user .message-avatar { grid-column: 1; }
  .message-row.role-user .message-bubble { grid-column: 2; justify-self: stretch; }
}
</style>