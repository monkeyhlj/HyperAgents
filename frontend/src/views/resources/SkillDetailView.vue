<template>
  <div>
    <Card dis-hover>
      <template #title>
        <Space>
          <Button size="small" @click="goBack">Back</Button>
          <span>{{ skill?.name || 'Skill' }} - Details</span>
        </Space>
      </template>

      <Row :gutter="16" style="margin-bottom: 20px">
        <Col :xs="24" :md="12">
          <Card dis-hover>
            <template #title>
              <Space>
                <span>Upload Skill Package</span>
                <Button v-if="uploadSuccess" size="small" type="primary" ghost @click="resetUpload">Upload Again</Button>
              </Space>
            </template>
            
            <div v-if="!uploadSuccess" class="upload-area" :class="{ dragover }" @dragover.prevent="dragover = true" @dragleave="dragover = false" @drop.prevent="handleDrop">
              <div v-if="dragover" class="drag-hint">Drop folder or .zip file here</div>
              <div v-else class="upload-content">
                <Icon type="ios-cloud-upload-outline" size="64" />
                <p>Drag your skill folder or .zip package here</p>
                <p class="file-hint">Folder must contain SKILL.md, scripts/ is optional</p>
                <Space>
                  <input
                    ref="zipInput"
                    type="file"
                    accept=".zip"
                    style="display: none"
                    @change="handleFileSelect"
                  />
                  <input
                    ref="folderInput"
                    type="file"
                    webkitdirectory
                    style="display: none"
                    @change="handleFolderSelect"
                  />
                  <Button type="primary" @click="$refs.zipInput.click()">Select .zip File</Button>
                  <Button @click="$refs.folderInput.click()">Select Folder</Button>
                </Space>
              </div>
            </div>

            <div v-if="uploading" style="margin-top: 10px">
              <Progress :percent="uploadProgress" />
              <p style="text-align: center; margin-top: 5px">{{ uploadProgress }}%</p>
            </div>

            <Alert v-if="uploadError" show-icon type="error" style="margin-top: 10px; cursor: pointer;" closable @on-close="uploadError = ''">
              {{ uploadError }}
            </Alert>

            <Alert v-if="uploadSuccess" show-icon type="success" style="margin-top: 10px">
              <template #desc>
                <div>
                  <strong>✅ Skill uploaded successfully!</strong>
                  <div style="margin-top: 8px; line-height: 1.6;">
                    <div><strong>Entrypoint:</strong> {{ skillMetadata?.entrypoint || '-' }}</div>
                    <div><strong>Version:</strong> {{ skillMetadata?.version || '-' }}</div>
                    <div><strong>Author:</strong> {{ skillMetadata?.author || '-' }}</div>
                    <div v-if="skillMetadata?.capabilities?.length"><strong>Capabilities:</strong> {{ skillMetadata.capabilities.join(', ') }}</div>
                  </div>
                  <div style="margin-top: 10px">
                    <Button size="small" @click="resetUpload">Upload Again</Button>
                  </div>
                </div>
              </template>
            </Alert>
          </Card>
        </Col>

        <Col :xs="24" :md="12">
          <Card dis-hover>
            <template #title>
              <Space>
                <span>Skill Info</span>
                <Tag v-if="skillMetadata?.entrypoint" color="green">✅ Uploaded</Tag>
                <Tag v-else color="orange">⚠️ Not Uploaded</Tag>
              </Space>
            </template>
            
            <Descriptions v-if="skill" :column="1" bordered>
              <DescriptionsItem label="Name">{{ skill.name }}</DescriptionsItem>
              <DescriptionsItem label="Version">{{ skillMetadata?.version || '-' }}</DescriptionsItem>
              <DescriptionsItem label="Author">{{ skillMetadata?.author || '-' }}</DescriptionsItem>
              <DescriptionsItem label="Status">
                <Tag :color="skillMetadata?.status === 'active' ? 'green' : 'default'">
                  {{ skillMetadata?.status || '-' }}
                </Tag>
              </DescriptionsItem>
              <DescriptionsItem label="Entrypoint">
                <code>{{ skillMetadata?.entrypoint || '-' }}</code>
              </DescriptionsItem>
              <DescriptionsItem label="Capabilities">
                <div v-if="skillMetadata?.capabilities">
                  <Tag v-for="cap in skillMetadata.capabilities" :key="cap" color="cyan">
                    {{ cap }}
                  </Tag>
                </div>
                <span v-else>-</span>
              </DescriptionsItem>
              <DescriptionsItem label="Project">{{ skill.project_name }}</DescriptionsItem>
              <DescriptionsItem label="Visibility">{{ skill.visibility }}</DescriptionsItem>
              <DescriptionsItem label="Created At">
                {{ skill.created_at ? new Date(skill.created_at).toLocaleString() : '-' }}
              </DescriptionsItem>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      <Tabs v-model="activeTab" style="margin-bottom: 20px">
        <!-- Documentation Tab -->
        <TabPane label="Documentation" name="docs">
          <Card dis-hover>
            <template #title>
              <span>SKILL.md Documentation</span>
            </template>
            <div v-if="skillMetadata?.skill_md_content" class="markdown-content" v-html="renderMarkdown(skillMetadata.skill_md_content)"></div>
            <div v-else style="text-align: center; padding: 40px; color: #999">
              No documentation available
            </div>
          </Card>
        </TabPane>

        <TabPane label="Files" name="files">
          <Card dis-hover>
            <template #title>
              <span>Uploaded Files</span>
            </template>
            <div v-if="skillMetadata?.uploaded_files?.length">
              <div style="margin-bottom: 10px; color: #666;">
                Total files: {{ skillMetadata.uploaded_files.length }}
              </div>
              <Row :gutter="16">
                <Col :xs="24" :md="10">
                  <div class="schema-display" style="max-height: 420px;">
                    <div
                      v-for="filePath in skillMetadata.uploaded_files"
                      :key="filePath"
                      class="file-item"
                      :class="{ active: selectedFilePath === filePath }"
                      @click="previewFile(filePath)"
                    >
                      {{ filePath }}
                    </div>
                  </div>
                </Col>
                <Col :xs="24" :md="14">
                  <div class="schema-display" style="min-height: 220px; max-height: 420px;">
                    <div v-if="!selectedFilePath" style="color: #999">Click a file to preview its content</div>
                    <div v-else-if="filePreviewLoading" style="color: #666">Loading...</div>
                    <div v-else-if="filePreviewError" style="color: #ff4d4f">{{ filePreviewError }}</div>
                    <div v-else>
                      <div style="margin-bottom: 10px; color: #666;">
                        <strong>{{ selectedFilePath }}</strong>
                        <span v-if="filePreview?.size_bytes"> ({{ filePreview.size_bytes }} bytes)</span>
                        <span v-if="filePreview?.truncated"> - preview truncated</span>
                      </div>
                      <div v-if="filePreview?.is_text">
                        <pre class="file-preview-content">{{ filePreview?.content || '' }}</pre>
                      </div>
                      <div v-else style="color: #999">
                        Binary file is not previewable in browser
                      </div>
                    </div>
                  </div>
                </Col>
              </Row>
            </div>
            <div v-else style="color: #999">No uploaded files found</div>
          </Card>
        </TabPane>

        <!-- Input/Output Schema Tab -->
        <TabPane label="Schema" name="schema">
          <Row :gutter="16">
            <Col :xs="24" :md="12">
              <Card dis-hover>
                <template #title>
                  <span>Input Schema</span>
                </template>
                <pre v-if="skillMetadata?.input_schema" class="schema-display">{{ JSON.stringify(skillMetadata.input_schema, null, 2) }}</pre>
                <div v-else style="color: #999">No input schema defined</div>
              </Card>
            </Col>
            <Col :xs="24" :md="12">
              <Card dis-hover>
                <template #title>
                  <span>Output Schema</span>
                </template>
                <pre v-if="skillMetadata?.output_schema" class="schema-display">{{ JSON.stringify(skillMetadata.output_schema, null, 2) }}</pre>
                <div v-else style="color: #999">No output schema defined</div>
              </Card>
            </Col>
          </Row>
        </TabPane>

        <!-- Requirements Tab -->
        <TabPane label="Requirements" name="requirements">
          <Card dis-hover>
            <template #title>
              <span>Dependencies</span>
            </template>
            <pre v-if="skillMetadata?.requirements" class="schema-display">{{ JSON.stringify(skillMetadata.requirements, null, 2) }}</pre>
            <div v-else style="color: #999">No requirements defined</div>
          </Card>
        </TabPane>

        <!-- Test Tab -->
        <TabPane label="Test" name="test">
          <Card dis-hover>
            <template #title>
              <span>Test Skill Execution</span>
            </template>
            
            <Form :model="testForm" label-position="top">
              <FormItem label="Input Data (JSON)">
                <Input
                  v-model="testForm.inputJson"
                  type="textarea"
                  :rows="8"
                  placeholder='{"key": "value"}'
                />
              </FormItem>

              <FormItem>
                <Space>
                  <Button type="primary" :loading="testing" @click="runTest">
                    Run Test
                  </Button>
                  <Button @click="testForm.inputJson = ''">Clear</Button>
                </Space>
              </FormItem>

              <Alert v-if="testError" show-icon type="error" style="margin-bottom: 10px">
                {{ testError }}
              </Alert>

              <div v-if="testResult" style="margin-top: 10px">
                <Divider orientation="left">Test Result</Divider>
                <Tag :color="testResult.status === 'completed' ? 'green' : 'red'">
                  {{ testResult.status }}
                </Tag>
                <div v-if="testResult.output_data" style="margin-top: 10px">
                  <strong>Output:</strong>
                  <pre class="schema-display">{{ JSON.stringify(testResult.output_data, null, 2) }}</pre>
                </div>
                <div v-if="testResult.error_message" style="margin-top: 10px; color: #ff4d4f">
                  <strong>Error:</strong>
                  <p>{{ testResult.error_message }}</p>
                </div>
              </div>
            </Form>
          </Card>
        </TabPane>

        <!-- Bindings Tab -->
        <TabPane label="Agent Bindings" name="bindings">
          <Card dis-hover>
            <template #title>
              <Space>
                <span>Bound to Agents</span>
                <Button size="small" :loading="bindingLoading" @click="loadBindings">Refresh</Button>
              </Space>
            </template>

            <Table v-if="bindings.length > 0" :columns="bindingColumns" :data="bindings" stripe>
              <template #enabled="{ row }">
                <Switch v-model="row.enabled" size="small" @on-change="updateBinding(row)" />
              </template>
              <template #priority="{ row }">
                <InputNumber v-model="row.priority" size="small" @on-change="updateBinding(row)" />
              </template>
              <template #action="{ row }">
                <Button size="small" type="error" ghost @click="unbindSkill(row)">
                  Unbind
                </Button>
              </template>
            </Table>

            <div v-else style="text-align: center; padding: 40px; color: #999">
              This skill is not bound to any agents yet
            </div>
          </Card>
        </TabPane>
      </Tabs>
    </Card>

    <!-- Error Modal -->
    <Modal v-model="showErrorModal" title="Error Details" width="600">
      <p v-if="errorDetail">{{ errorDetail }}</p>
      <template #footer>
        <Button type="primary" @click="showErrorModal = false">Close</Button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  Message,
  Modal,
  Card,
  Row,
  Col,
  Space,
  Button,
  Icon,
  Descriptions,
  DescriptionsItem,
  Tag,
  Alert,
  TabPane,
  Tabs,
  Form,
  FormItem,
  Input,
  Switch,
  InputNumber,
  Table,
  Divider,
  Progress,
} from "view-ui-plus";
import { api } from "../../services/api";
import { marked } from 'marked';

const route = useRoute();
const router = useRouter();

const skill = ref(null);
const skillMetadata = ref(null);
const bindings = ref([]);
const loading = ref(false);
const bindingLoading = ref(false);
const uploading = ref(false);
const uploadProgress = ref(0);
const uploadError = ref("");
const uploadSuccess = ref(false);
const dragover = ref(false);
const activeTab = ref("docs");
const zipInput = ref(null);
const folderInput = ref(null);
const selectedFilePath = ref("");
const filePreview = ref(null);
const filePreviewLoading = ref(false);
const filePreviewError = ref("");

// Test form
const testForm = ref({ inputJson: "" });
const testing = ref(false);
const testError = ref("");
const testResult = ref(null);

// Error modal
const showErrorModal = ref(false);
const errorDetail = ref("");

const resourceId = computed(() => route.params.resourceId);

const bindingColumns = computed(() => [
  {
    title: "Agent Name",
    key: "agent_name",
    width: 200,
  },
  {
    title: "Priority",
    slot: "priority",
    width: 100,
  },
  {
    title: "Enabled",
    slot: "enabled",
    width: 80,
  },
  {
    title: "Action",
    slot: "action",
    width: 100,
    align: "center",
  },
]);

watch(
  () => resourceId.value,
  () => {
    loadData();
  },
  { immediate: true }
);

async function loadData() {
  await Promise.all([loadSkill(), loadBindings()]);
}

async function loadSkill() {
  loading.value = true;
  try {
    const response = await api.getSkill(resourceId.value);
    skill.value = response;
    // Extract metadata
    skillMetadata.value = {
      version: response.version,
      author: response.author,
      status: response.status,
      entrypoint: response.entrypoint,
      capabilities: response.capabilities,
      requirements: response.requirements,
      input_schema: response.input_schema,
      output_schema: response.output_schema,
      skill_md_content: response.skill_md_content,
      uploaded_files: response.uploaded_files || [],
    };

    if (!skillMetadata.value.uploaded_files.includes(selectedFilePath.value)) {
      selectedFilePath.value = "";
      filePreview.value = null;
      filePreviewError.value = "";
    }
  } catch (error) {
    Message.error("Failed to load skill");
    console.error(error);
  } finally {
    loading.value = false;
  }
}

async function loadBindings() {
  bindingLoading.value = true;
  try {
    const response = await api.listSkillBindings(resourceId.value);
    bindings.value = response.agents || [];
  } catch (error) {
    // Silently ignore if endpoint not available yet
    console.warn("Failed to load bindings:", error);
  } finally {
    bindingLoading.value = false;
  }
}

function handleFileSelect(e) {
  const files = e.target.files;
  if (files.length > 0) {
    uploadZipFile(files[0]);
  }
}

function handleFolderSelect(e) {
  const files = e.target.files;
  if (files.length > 0) {
    uploadFolderFiles(files);
  }
}

function handleDrop(e) {
  dragover.value = false;
  const files = e.dataTransfer.files;
  if (files.length === 0) return;
  
  // Check if it's a folder (multiple files with same base path) or single zip
  const fileList = Array.from(files);
  const hasSkillMd = fileList.some(f => f.webkitRelativePath?.endsWith('SKILL.md') || f.name === 'SKILL.md');
  const isFolder = fileList.some(f => f.webkitRelativePath);
  const isZip = fileList[0].name.endsWith('.zip');
  
  if (isFolder || hasSkillMd) {
    uploadFolderFiles(files);
  } else if (isZip || files.length === 1) {
    uploadZipFile(files[0]);
  } else {
    uploadError.value = "Please drop a .zip file or a folder containing SKILL.md";
  }
}

function resetUpload() {
  uploadSuccess.value = false;
  uploadError.value = "";
  uploadProgress.value = 0;
  // Reset file inputs
  if (zipInput.value) zipInput.value.value = '';
  if (folderInput.value) folderInput.value.value = '';
}

async function uploadZipFile(file) {
  uploadError.value = "";
  uploadSuccess.value = false;

  if (!file.name.endsWith(".zip")) {
    uploadError.value = "File must be a .zip archive";
    return;
  }

  uploading.value = true;
  uploadProgress.value = 0;

  try {
    const formData = new FormData();
    formData.append("file", file);

    const interval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += Math.random() * 30;
      }
    }, 200);

    await api.uploadSkill(resourceId.value, formData);

    clearInterval(interval);
    uploadProgress.value = 100;
    uploadSuccess.value = true;

    setTimeout(() => {
      loadSkill();
      uploadSuccess.value = false;
      uploading.value = false;
      uploadProgress.value = 0;
    }, 1500);
  } catch (error) {
    uploadError.value = error.response?.data?.detail || error.message || "Failed to upload skill. Please try again.";
    console.error(error);
    uploading.value = false;
    uploadProgress.value = 0;
  }
}

async function uploadFolderFiles(fileList) {
  uploadError.value = "";
  uploadSuccess.value = false;

  const files = Array.from(fileList);
  
  // Validate that SKILL.md exists
  const hasSkillMd = files.some(f => {
    const path = f.webkitRelativePath || f.name;
    return path.endsWith('SKILL.md');
  });

  if (!hasSkillMd) {
    uploadError.value = "Folder must contain SKILL.md file";
    return;
  }

  uploading.value = true;
  uploadProgress.value = 0;

  try {
    const formData = new FormData();
    
    // Add all files with their relative paths
    files.forEach(file => {
      const path = file.webkitRelativePath || file.name;
      formData.append("files", file, path);
    });

    const interval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += Math.random() * 30;
      }
    }, 200);

    await api.uploadSkillFolder(resourceId.value, formData);

    clearInterval(interval);
    uploadProgress.value = 100;
    uploadSuccess.value = true;

    setTimeout(() => {
      loadSkill();
      uploadSuccess.value = false;
      uploading.value = false;
      uploadProgress.value = 0;
    }, 1500);
  } catch (error) {
    uploadError.value = error.response?.data?.detail || error.message || "Failed to upload skill folder. Please try again.";
    console.error(error);
    uploading.value = false;
    uploadProgress.value = 0;
  }
}

async function runTest() {
  testError.value = "";
  testResult.value = null;

  // Parse JSON input
  let inputData;
  try {
    inputData = JSON.parse(testForm.value.inputJson || "{}");
  } catch (e) {
    testError.value = `Invalid JSON: ${e.message}`;
    return;
  }

  testing.value = true;
  try {
    const response = await api.testSkill(resourceId.value, inputData);
    testResult.value = response;
  } catch (error) {
    testError.value =
      error.response?.data?.detail ||
      error.message ||
      "Test execution failed";
    console.error(error);
  } finally {
    testing.value = false;
  }
}

async function previewFile(filePath) {
  selectedFilePath.value = filePath;
  filePreviewError.value = "";
  filePreview.value = null;
  filePreviewLoading.value = true;

  try {
    const response = await api.getSkillFileContent(resourceId.value, filePath);
    filePreview.value = response;
  } catch (error) {
    filePreviewError.value = error.response?.data?.detail || error.message || "Failed to load file content";
  } finally {
    filePreviewLoading.value = false;
  }
}

async function updateBinding(binding) {
  try {
    await api.updateAgentSkillBinding(binding.agent_id, resourceId.value, {
      priority: binding.priority,
      enabled: binding.enabled,
    });
    Message.success("Binding updated");
  } catch (error) {
    Message.error("Failed to update binding");
    console.error(error);
    loadBindings(); // Reload to reset changes
  }
}

async function unbindSkill(binding) {
  Modal.confirm({
    title: "Unbind Skill",
    content: `Unbind skill from agent: ${binding.agent_name}?`,
    okText: "Unbind",
    cancelText: "Cancel",
    onOk: async () => {
      try {
        await api.unbindSkillFromAgent(binding.agent_id, resourceId.value);
        Message.success("Skill unbound successfully");
        loadBindings();
      } catch (error) {
        Message.error("Failed to unbind skill");
        console.error(error);
      }
    },
  });
}

function renderMarkdown(content) {
  try {
    return marked(content);
  } catch (e) {
    return `<p>${content}</p>`;
  }
}

function goBack() {
  router.push({ name: "resources-skills" });
}
</script>

<style scoped>
.upload-area {
  border: 2px dashed #d9d9d9;
  border-radius: 4px;
  padding: 40px 20px;
  text-align: center;
  transition: all 0.3s;
  cursor: pointer;
}

.upload-area:hover {
  border-color: #40a9ff;
  background-color: #f5f7fa;
}

.upload-area.dragover {
  border-color: #40a9ff;
  background-color: #f5f7fa;
}

.drag-hint {
  padding: 40px;
  font-size: 16px;
  font-weight: bold;
  color: #40a9ff;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.upload-content p {
  margin: 0;
  color: #666;
}

.file-hint {
  font-size: 12px;
  color: #999 !important;
}

.markdown-content {
  line-height: 1.6;
  color: #333;
}

.markdown-content h1,
.markdown-content h2,
.markdown-content h3,
.markdown-content h4,
.markdown-content h5,
.markdown-content h6 {
  margin-top: 20px;
  margin-bottom: 10px;
  font-weight: bold;
}

.markdown-content h1 {
  font-size: 28px;
  border-bottom: 2px solid #eee;
  padding-bottom: 10px;
}

.markdown-content h2 {
  font-size: 24px;
}

.markdown-content h3 {
  font-size: 20px;
}

.markdown-content code {
  background-color: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
}

.markdown-content pre {
  background-color: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
}

.markdown-content pre code {
  background-color: transparent;
  padding: 0;
}

.schema-display {
  background-color: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.4;
  max-height: 400px;
  overflow-y: auto;
}

.file-item {
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  word-break: break-all;
}

.file-item:hover {
  background-color: #e8f4ff;
}

.file-item.active {
  background-color: #d5ecff;
  color: #0f5e96;
}

.file-preview-content {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
