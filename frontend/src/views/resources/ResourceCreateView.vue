<template>
  <div>
    <Row :gutter="16">
      <Col v-if="isAgentKind" :xs="24" :lg="8">
        <Card dis-hover class="chat-test-card">
          <template #title>
            <Space>
              <span>Dialog Test</span>
              <Tag color="green">Draft</Tag>
            </Space>
          </template>

          <Alert show-icon>
            Fill model settings and system prompt first, then use this chat to dry-run agent behavior.
          </Alert>

          <div class="chat-messages">
            <div v-if="testMessages.length === 0" class="chat-empty">No test message yet.</div>
            <div v-for="(item, idx) in testMessages" :key="idx" class="chat-message" :class="`role-${item.role}`">
              <div class="chat-role">{{ item.role }}</div>
              <div class="chat-text">{{ item.text }}</div>
            </div>
          </div>

          <Input v-model="testInput" type="textarea" :rows="3" placeholder="Type prompt for test" />
          <Space style="margin-top: 10px">
            <Button @click="clearTest">Clear</Button>
            <Button type="primary" :loading="testing" @click="runDraftTest">Send</Button>
          </Space>
        </Card>
      </Col>

      <Col :xs="24" :lg="isAgentKind ? 16 : 24">
        <Card dis-hover>
          <template #title>
            <Space>
              <Button size="small" @click="goBack">Back</Button>
              <span>{{ pageTitle }}</span>
              <Tag v-if="isEditMode" color="orange">Edit Mode</Tag>
            </Space>
          </template>

          <Form :model="form" label-position="top">
            <Row :gutter="16">
              <Col :xs="24" :md="12">
                <FormItem label="Project">
                  <Select v-model="form.project_id" filterable placeholder="Select project" @on-change="refreshAssociationOptions">
                    <Option v-for="item in projects" :key="item.id" :value="item.id">{{ item.name }} ({{ item.id }})</Option>
                  </Select>
                </FormItem>
              </Col>
              <Col :xs="24" :md="12">
                <FormItem label="Kind">
                  <Input :value="kind" readonly />
                </FormItem>
              </Col>
            </Row>

            <Row :gutter="16">
              <Col :xs="24" :md="12">
                <FormItem label="Name">
                  <Input v-model="form.name" maxlength="120" show-word-limit />
                </FormItem>
              </Col>
              <Col :xs="24" :md="12">
                <FormItem label="Visibility">
                  <Select v-model="form.visibility">
                    <Option value="private">private</Option>
                    <Option value="project">project</Option>
                    <Option value="public">public</Option>
                  </Select>
                </FormItem>
              </Col>
            </Row>

            <FormItem label="Description">
              <Input v-model="form.description" type="textarea" :rows="3" maxlength="1000" show-word-limit />
            </FormItem>

            <Row v-if="isAgentKind" :gutter="16">
              <Col :xs="24" :md="12">
                <FormItem label="Agent Run Mode">
                  <Select v-model="form.run_mode">
                    <Option value="llm">llm (model inference)</Option>
                    <Option value="code">code (custom code execution)</Option>
                  </Select>
                </FormItem>
              </Col>
            </Row>

            <template v-if="isAgentKind">
              <Divider />

              <FormItem label="Model Preset">
                <RadioGroup v-model="form.model_mode">
                  <Radio label="default">Use default template</Radio>
                  <Radio label="custom">Custom model settings</Radio>
                </RadioGroup>
              </FormItem>

              <Row v-if="form.model_mode === 'default'" :gutter="16">
                <Col :xs="24" :md="12">
                  <FormItem label="Template">
                    <Select v-model="form.template_id" clearable filterable @on-change="applyTemplate">
                      <Option v-for="item in templates" :key="item.template_id" :value="item.template_id">
                        {{ item.name }} ({{ item.model_provider || '-' }} / {{ item.model_name || '-' }})
                      </Option>
                    </Select>
                  </FormItem>
                </Col>
              </Row>

              <Row v-else :gutter="16">
                <Col :xs="24" :md="8">
                  <FormItem label="Model Provider">
                    <Input v-model="form.model_provider" />
                  </FormItem>
                </Col>
                <Col :xs="24" :md="8">
                  <FormItem label="Model Name">
                    <Input v-model="form.model_name" />
                  </FormItem>
                </Col>
                <Col :xs="24" :md="8">
                  <FormItem label="Provider Profile">
                    <Input v-model="form.provider_profile" />
                  </FormItem>
                </Col>
              </Row>

              <Divider />

              <FormItem label="System Prompt">
                <Input v-model="form.system_prompt" type="textarea" :rows="4" placeholder="Define system behavior for this resource" />
              </FormItem>

              <Row :gutter="16">
                <Col :xs="24" :md="12">
                  <FormItem label="Associate Tools">
                    <Select v-model="form.tool_ids" multiple filterable>
                      <Option v-for="item in toolOptions" :key="item.id" :value="item.id">{{ item.name }}</Option>
                    </Select>
                  </FormItem>
                </Col>
                <Col :xs="24" :md="12">
                  <FormItem label="Associate Skills">
                    <Select v-model="form.skill_ids" multiple filterable>
                      <Option v-for="item in skillOptions" :key="item.id" :value="item.id">{{ item.name }}</Option>
                    </Select>
                  </FormItem>
                </Col>
              </Row>

              <Row :gutter="16">
                <Col :xs="24" :md="12">
                  <FormItem label="Associate MCPs">
                    <Select v-model="form.mcp_ids" multiple filterable>
                      <Option v-for="item in mcpOptions" :key="item.id" :value="item.id">{{ item.name }}</Option>
                    </Select>
                  </FormItem>
                </Col>
                <Col :xs="24" :md="12">
                  <FormItem label="Associate Knowledge Bases">
                    <Select v-model="form.knowledge_base_ids" multiple filterable>
                      <Option v-for="item in kbOptions" :key="item.id" :value="item.id">{{ item.name }}</Option>
                    </Select>
                  </FormItem>
                </Col>
              </Row>

              <Divider />

              <Alert show-icon class="authoring-guide-alert">
                <template #desc>
                  <div class="authoring-guide-copy">
                    <div>
                      <strong>Authoring guide:</strong>
                      <a :href="authoringGuideUrl" target="_blank" rel="noopener noreferrer">{{ authoringGuidePath }}</a>
                    </div>
                    <div>
                      `Custom Code` runs only in <strong>code</strong> mode. `Advanced Config JSON` is merged into `context.config` for both draft testing and saved execution.
                    </div>
                  </div>
                </template>
              </Alert>

              <FormItem label="Custom Code (Editable)">
                <CodeEditor
                  v-model="form.custom_code"
                  language="python"
                  min-height="260px"
                  placeholder="Write run(input_text, context) for code-mode agents"
                />
              </FormItem>
            </template>
            <template v-else>
              <Alert show-icon>
                {{ nonAgentHint }}
              </Alert>

              <template v-if="isToolKind">
                <Divider />

                <Row :gutter="16">
                  <Col :xs="24" :md="8">
                    <FormItem label="Tool Runtime">
                      <Select v-model="form.tool_runtime">
                        <Option value="python">python</Option>
                        <Option value="javascript">javascript</Option>
                      </Select>
                    </FormItem>
                  </Col>
                  <Col :xs="24" :md="8">
                    <FormItem label="Function Name">
                      <Input v-model="form.tool_entrypoint" placeholder="e.g. run" />
                    </FormItem>
                  </Col>
                  <Col :xs="24" :md="8">
                    <FormItem label="Shared In Project">
                      <Select v-model="form.tool_shared">
                        <Option :value="true">true</Option>
                        <Option :value="false">false</Option>
                      </Select>
                    </FormItem>
                  </Col>
                </Row>

                <FormItem label="Tool Code (Editable)">
                  <CodeEditor
                    v-model="form.tool_code"
                    :language="form.tool_runtime === 'javascript' ? 'javascript' : 'python'"
                    min-height="260px"
                    placeholder="Implement your tool function here"
                  />
                </FormItem>

                <Row :gutter="16">
                  <Col :xs="24" :md="12">
                    <FormItem label="Input Schema JSON">
                      <CodeEditor
                        v-model="form.tool_input_schema_json"
                        language="json"
                        min-height="200px"
                        placeholder="JSON Schema for tool input"
                      />
                    </FormItem>
                  </Col>
                  <Col :xs="24" :md="12">
                    <FormItem label="Output Schema JSON">
                      <CodeEditor
                        v-model="form.tool_output_schema_json"
                        language="json"
                        min-height="200px"
                        placeholder="JSON Schema for tool output"
                      />
                    </FormItem>
                  </Col>
                </Row>
              </template>
            </template>

            <FormItem v-if="showConfigEditor" :label="configEditorLabel">
              <Alert show-icon class="authoring-guide-alert">
                <template #desc>
                  <div class="authoring-guide-copy">
                    <div>
                      <strong>Advanced Config example:</strong>
                      provider_profile decides which .env prefix the backend reads. For example, provider_profile=qwen means QWEN_API_KEY / QWEN_BASE_URL / QWEN_DEFAULT_MODEL must exist in .env. role_name is optional and only used as a human-readable label inside the config.
                    </div>
                    <pre class="config-example-block">{
  "provider_profile": "qwen",
  "temperature": 0.2
}</pre>
                  </div>
                </template>
              </Alert>
              <CodeEditor
                v-model="form.config_json"
                language="json"
                min-height="220px"
                placeholder="Add extra runtime settings such as provider_profile, role_name, temperature, routes, or feature flags"
              />
            </FormItem>

            <FormItem>
              <Space>
                <Button @click="goBack">Cancel</Button>
                <Button type="primary" :loading="saving" @click="submitForm">{{ submitLabel }}</Button>
              </Space>
            </FormItem>
          </Form>
        </Card>
      </Col>
    </Row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Message } from "view-ui-plus";
import CodeEditor from "../../components/CodeEditor.vue";
import { api } from "../../services/api";

const route = useRoute();
const router = useRouter();

const projects = ref([]);
const templates = ref([]);
const ownedResources = ref([]);
const saving = ref(false);
const testing = ref(false);
const testInput = ref("");
const testMessages = ref([]);
const loadedResource = ref(null);

const form = ref({
  project_id: "",
  name: "",
  visibility: "project",
  description: "",
  model_mode: "default",
  run_mode: "llm",
  template_id: "",
  model_provider: "",
  model_name: "",
  provider_profile: "",
  system_prompt: "",
  custom_code: "def run(input_text, context):\n    text = input_text.strip()\n\n    if text == \"ping\":\n        return call_tool(\"testping\", {\"action\": \"ping\", \"text\": text})\n\n    if text == \"show config\":\n        return {\n            \"project_id\": context.get(\"project_id\"),\n            \"tool_ids\": context.get(\"config\", {}).get(\"tool_ids\", []),\n            \"tools\": list_tools(),\n        }\n\n    return {\"echo\": text}\n",
  tool_runtime: "python",
  tool_entrypoint: "run",
  tool_shared: true,
  tool_code: "def run(input_data: dict, context: dict) -> dict:\n    # Implement tool logic here\n    return {\"ok\": True, \"echo\": input_data}\n",
  tool_input_schema_json: "{\n  \"type\": \"object\",\n  \"properties\": {\n    \"query\": { \"type\": \"string\" }\n  },\n  \"required\": [\"query\"]\n}",
  tool_output_schema_json: "{\n  \"type\": \"object\",\n  \"properties\": {\n    \"ok\": { \"type\": \"boolean\" },\n    \"echo\": { \"type\": \"object\" }\n  }\n}",
  config_json: "{\n  \"provider_profile\": \"qwen\",\n  \"temperature\": 0.2\n}",
  tool_ids: [],
  skill_ids: [],
  mcp_ids: [],
  knowledge_base_ids: []
});

const kind = computed(() => route.meta.kind || "agent");
const isAgentKind = computed(() => kind.value === "agent");
const isToolKind = computed(() => kind.value === "tool");
const pageTitle = computed(() => route.meta.title || "Create Resource");
const backRoute = computed(() => route.meta.backRoute || "resources-overview");
const isEditMode = computed(() => route.meta.mode === "edit");
const resourceId = computed(() => String(route.params.resourceId || ""));
const submitLabel = computed(() => (isEditMode.value ? "Save Changes" : "Create"));
const showConfigEditor = computed(() => !isToolKind.value);
const configEditorLabel = computed(() => {
  if (isAgentKind.value) {
    return "Advanced Config JSON (Editable)";
  }
  if (isToolKind.value) {
    return "Advanced Tool Config JSON";
  }
  return "Config JSON";
});
const nonAgentHint = computed(() => {
  const map = {
    tool: "Tools are programmable helpers. Define function code and schema below. Tool resources can be reused by agents in the same project.",
    skill: "Skills orchestrate tools and logic. Put your composition settings in Config JSON.",
    mcp: "MCP resources are integration descriptors. Use Config JSON to define server and protocol options.",
    knowledge_base: "Knowledge resources are retrieval/config containers. Define datasource and indexing settings in Config JSON."
  };
  return map[kind.value] || "Configure this resource with Config JSON.";
});
const authoringGuidePath = "docs/modules/agents.zh-en.md";
const authoringGuideUrl = "https://github.com/monkeyhlj/HyperAgents/blob/main/docs/modules/agents.zh-en.md";

const scopedOwned = computed(() => {
  if (!form.value.project_id) {
    return [];
  }
  return ownedResources.value.filter((item) => item.project_id === form.value.project_id);
});

const toolOptions = computed(() => scopedOwned.value.filter((item) => item.kind === "tool"));
const skillOptions = computed(() => scopedOwned.value.filter((item) => item.kind === "skill"));
const mcpOptions = computed(() => scopedOwned.value.filter((item) => item.kind === "mcp"));
const kbOptions = computed(() => scopedOwned.value.filter((item) => item.kind === "knowledge_base"));

function goBack() {
  router.push({ name: backRoute.value });
}

async function loadProjects() {
  projects.value = await api.listProjects();
  if (projects.value.length > 0 && !form.value.project_id) {
    form.value.project_id = projects.value[0].id;
  }
}

async function loadTemplates() {
  if (!isAgentKind.value) {
    templates.value = [];
    return;
  }
  templates.value = await api.listDefaultResources({ kind: kind.value });
}

async function loadOwnedResources() {
  ownedResources.value = await api.listOwnedResources();
}

async function loadResource() {
  if (!isEditMode.value || !resourceId.value) {
    return;
  }
  loadedResource.value = await api.getResource(resourceId.value);
  const config = loadedResource.value.config || {};
  form.value.project_id = loadedResource.value.project_id || "";
  form.value.name = loadedResource.value.name || "";
  form.value.visibility = loadedResource.value.visibility || "project";
  form.value.description = loadedResource.value.description || "";
  form.value.run_mode = config.run_mode || "llm";
  form.value.model_mode = loadedResource.value.model_provider || loadedResource.value.model_name ? "custom" : "default";
  form.value.template_id = "";
  if (isAgentKind.value) {
    form.value.model_provider = loadedResource.value.model_provider || "";
    form.value.model_name = loadedResource.value.model_name || "";
    form.value.provider_profile = loadedResource.value.provider_profile || "";
    form.value.system_prompt = config.system_prompt || "";
    form.value.custom_code = config.custom_code || "";
    form.value.tool_ids = config.tool_ids || [];
    form.value.skill_ids = config.skill_ids || [];
    form.value.mcp_ids = config.mcp_ids || [];
    form.value.knowledge_base_ids = config.knowledge_base_ids || [];

    const advancedConfig = { ...config };
    delete advancedConfig.run_mode;
    delete advancedConfig.system_prompt;
    delete advancedConfig.custom_code;
    delete advancedConfig.tool_ids;
    delete advancedConfig.skill_ids;
    delete advancedConfig.mcp_ids;
    delete advancedConfig.knowledge_base_ids;
    form.value.config_json = JSON.stringify(advancedConfig, null, 2);
    return;
  }

  if (isToolKind.value) {
    form.value.tool_runtime = config.runtime || "python";
    form.value.tool_entrypoint = config.entrypoint || "run";
    form.value.tool_shared = config.shared_in_project !== false;
    form.value.tool_code = config.code || "";
    form.value.tool_input_schema_json = JSON.stringify(config.input_schema || {}, null, 2);
    form.value.tool_output_schema_json = JSON.stringify(config.output_schema || {}, null, 2);

    form.value.model_provider = "";
    form.value.model_name = "";
    form.value.provider_profile = "";
    form.value.system_prompt = "";
    form.value.custom_code = "";
    form.value.tool_ids = [];
    form.value.skill_ids = [];
    form.value.mcp_ids = [];
    form.value.knowledge_base_ids = [];
    form.value.config_json = "{}";
    return;
  }

  form.value.model_provider = "";
  form.value.model_name = "";
  form.value.provider_profile = "";
  form.value.system_prompt = "";
  form.value.custom_code = "";
  form.value.tool_ids = [];
  form.value.skill_ids = [];
  form.value.mcp_ids = [];
  form.value.knowledge_base_ids = [];
  form.value.config_json = JSON.stringify(config, null, 2);
}

function applyTemplate() {
  if (!form.value.template_id) {
    return;
  }
  const template = templates.value.find((item) => item.template_id === form.value.template_id);
  if (!template) {
    return;
  }
  form.value.model_provider = template.model_provider || "";
  form.value.model_name = template.model_name || "";
  form.value.provider_profile = template.provider_profile || "";
    form.value.name = template.name;
    form.value.description = template.description || "";
}

function refreshAssociationOptions() {
  form.value.tool_ids = form.value.tool_ids.filter((id) => toolOptions.value.some((item) => item.id === id));
  form.value.skill_ids = form.value.skill_ids.filter((id) => skillOptions.value.some((item) => item.id === id));
  form.value.mcp_ids = form.value.mcp_ids.filter((id) => mcpOptions.value.some((item) => item.id === id));
  form.value.knowledge_base_ids = form.value.knowledge_base_ids.filter((id) => kbOptions.value.some((item) => item.id === id));
}

function clearTest() {
  testMessages.value = [];
}

function parseAdvancedConfig() {
  const rawJson = form.value.config_json.trim();
  if (!rawJson) {
    return {};
  }
  try {
    return JSON.parse(rawJson);
  } catch {
    throw new Error("Advanced config JSON is invalid");
  }
}

function parseToolSchema(rawJson, label) {
  const text = (rawJson || "").trim();
  if (!text) {
    return {};
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`${label} is invalid JSON`);
  }
}

function buildRuntimeConfig() {
  if (isToolKind.value) {
    const entrypoint = form.value.tool_entrypoint.trim();
    if (!entrypoint) {
      throw new Error("Tool function name is required");
    }
    return {
      runtime: form.value.tool_runtime,
      entrypoint,
      shared_in_project: !!form.value.tool_shared,
      code: form.value.tool_code,
      input_schema: parseToolSchema(form.value.tool_input_schema_json, "Tool input schema"),
      output_schema: parseToolSchema(form.value.tool_output_schema_json, "Tool output schema")
    };
  }
  if (!isAgentKind.value) {
    return parseAdvancedConfig();
  }
  return {
    run_mode: form.value.run_mode,
    system_prompt: form.value.system_prompt,
    custom_code: form.value.custom_code,
    tool_ids: form.value.tool_ids,
    skill_ids: form.value.skill_ids,
    mcp_ids: form.value.mcp_ids,
    knowledge_base_ids: form.value.knowledge_base_ids,
    ...parseAdvancedConfig()
  };
}

async function runDraftTest() {
  if (!isAgentKind.value) {
    Message.warning("Draft chat test is available for agent resources only");
    return;
  }
  const text = testInput.value.trim();
  if (!form.value.project_id) {
    Message.warning("Please select project first");
    return;
  }
  if (!text) {
    Message.warning("Please input test message");
    return;
  }

  testing.value = true;
  testMessages.value.push({ role: "user", text });
  testInput.value = "";
  try {
    const runtimeConfig = buildRuntimeConfig();
    const result = await api.previewResourceChat({
      project_id: form.value.project_id,
      text,
      run_mode: form.value.run_mode,
      model_provider: form.value.model_provider || null,
      model_name: form.value.model_name || null,
      provider_profile: form.value.provider_profile || null,
      system_prompt: form.value.system_prompt || null,
      custom_code: form.value.custom_code,
      config: runtimeConfig
    });
    testMessages.value.push({ role: "assistant", text: result.text || "" });
  } catch (error) {
    const textError = error.message || "Preview failed";
    testMessages.value.push({ role: "assistant", text: `[error] ${textError}` });
    Message.error(textError);
  } finally {
    testing.value = false;
  }
}

async function submitForm() {
  if (!form.value.project_id) {
    Message.warning("Please select project");
    return;
  }
  const name = form.value.name.trim();
  if (name.length < 2) {
    Message.warning("Resource name requires at least 2 chars");
    return;
  }

  if (isAgentKind.value && form.value.model_mode === "default") {
    if (!form.value.template_id) {
      Message.warning("Please select a template or switch to custom model settings");
      return;
    }
  }

  saving.value = true;
  try {
    const config = buildRuntimeConfig();
    const payload = {
      kind: kind.value,
      name,
      visibility: form.value.visibility,
      description: form.value.description,
      model_provider: isAgentKind.value ? (form.value.model_provider || null) : null,
      model_name: isAgentKind.value ? (form.value.model_name || null) : null,
      provider_profile: isAgentKind.value ? (form.value.provider_profile || null) : null,
      config
    };
    if (isEditMode.value && resourceId.value) {
      await api.updateResource(resourceId.value, { ...payload, project_id: form.value.project_id });
      Message.success(`${kind.value} updated`);
    } else {
      await api.createResource(form.value.project_id, payload);
      Message.success(`${kind.value} created`);
    }
    goBack();
  } catch (error) {
    Message.error(error.message || `${isEditMode.value ? "Update" : "Create"} resource failed`);
  } finally {
    saving.value = false;
  }
}

onMounted(async () => {
  try {
    await Promise.all([loadProjects(), loadTemplates(), loadOwnedResources()]);
    await loadResource();
  } catch (error) {
    Message.error(error.message || "Load create form data failed");
  }
});
</script>

<style scoped>
.chat-test-card {
  min-height: 780px;
}

.chat-messages {
  border: 1px solid #dcdee2;
  border-radius: 8px;
  padding: 8px;
  margin: 12px 0;
  height: 420px;
  overflow-y: auto;
  background: #fafafa;
}

.chat-empty {
  color: #808695;
  text-align: center;
  margin-top: 180px;
}

.chat-message {
  margin-bottom: 8px;
  padding: 8px;
  border-radius: 6px;
  background: #fff;
}

.chat-message.role-user {
  border-left: 3px solid #2d8cf0;
}

.chat-message.role-assistant {
  border-left: 3px solid #19be6b;
}

.chat-role {
  font-size: 12px;
  color: #808695;
  margin-bottom: 4px;
}

.chat-text {
  white-space: pre-wrap;
  word-break: break-word;
}

.authoring-guide-alert {
  margin-bottom: 16px;
}

.authoring-guide-copy {
  display: grid;
  gap: 8px;
  line-height: 1.6;
}

.authoring-guide-copy a {
  margin-left: 6px;
  color: #0f6fb8;
  font-weight: 600;
}

.config-example-block {
  margin: 0;
  padding: 10px 12px;
  border-radius: 6px;
  background: #f8f9fb;
  border: 1px solid #e8eaec;
  font-family: Consolas, "Courier New", monospace;
  white-space: pre-wrap;
  overflow-x: auto;
}
</style>
