<template>
  <div>
    <Card dis-hover>
      <template #title>
        <Space>
          <Button size="small" @click="goBack">Back</Button>
          <span>{{ knowledge?.name || 'Knowledge Base' }} - Documents</span>
        </Space>
      </template>

      <Row :gutter="16" style="margin-bottom: 20px">
        <Col :xs="24" :md="12">
          <Card dis-hover>
            <template #title>
              <span>Upload Document</span>
            </template>
            
            <div class="upload-area" :class="{ dragover }" @dragover.prevent="dragover = true" @dragleave="dragover = false" @drop.prevent="handleDrop">
              <div v-if="dragover" class="drag-hint">Drop file here</div>
              <div v-else class="upload-content">
                <Icon type="ios-cloud-upload-outline" size="64" />
                <p>Drag files here or click to select</p>
                <p class="file-hint">Supported: PDF, DOCX, MD, TXT</p>
                <input
                  ref="fileInput"
                  type="file"
                  accept=".pdf,.docx,.md,.txt"
                  style="display: none"
                  @change="handleFileSelect"
                />
                <Button type="primary" @click="$refs.fileInput.click()">Select File</Button>
              </div>
            </div>

            <div v-if="uploading" style="margin-top: 10px">
              <Progress :percent="uploadProgress" />
              <p style="text-align: center; margin-top: 5px">{{ uploadProgress }}%</p>
            </div>

            <Alert v-if="uploadError" show-icon type="error" style="margin-top: 10px">
              {{ uploadError }}
            </Alert>

            <Alert v-if="uploadSuccess" show-icon type="success" style="margin-top: 10px">
              Document uploaded successfully! Processing will start shortly.
            </Alert>
          </Card>
        </Col>

        <Col :xs="24" :md="12">
          <Card dis-hover>
            <template #title>
              <span>Knowledge Base Info</span>
            </template>
            
            <Descriptions v-if="knowledge" :column="1" bordered>
              <DescriptionsItem label="Name">{{ knowledge.name }}</DescriptionsItem>
              <DescriptionsItem label="Project">{{ knowledge.project_name }}</DescriptionsItem>
              <DescriptionsItem label="Visibility">{{ knowledge.visibility }}</DescriptionsItem>
              <DescriptionsItem label="Description">{{ knowledge.description || '-' }}</DescriptionsItem>
              <DescriptionsItem label="Total Documents">{{ documents.length }}</DescriptionsItem>
              <DescriptionsItem label="Ready Documents">
                {{ documents.filter((d) => d.status === 'ready').length }}
              </DescriptionsItem>
              <DescriptionsItem label="Created At">
                {{ knowledge.created_at ? new Date(knowledge.created_at).toLocaleString() : '-' }}
              </DescriptionsItem>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      <Card dis-hover>
        <template #title>
          <Space>
            <span>Documents</span>
            <Tag color="cyan">Total: {{ documents.length }}</Tag>
            <Button size="small" :loading="loading" @click="loadDocuments">Refresh</Button>
            <Button
              v-if="hasFailedDocuments"
              size="small"
              type="warning"
              :loading="reprocessing"
              @click="reprocessFailed"
            >
              Reprocess Failed
            </Button>
          </Space>
        </template>

        <Table :columns="columns" :data="documents" stripe>
          <template #status="{ row }">
            <Tag v-if="row.status === 'ready'" color="green">{{ row.status }}</Tag>
            <Tag v-else-if="row.status === 'processing'" color="blue">{{ row.status }}</Tag>
            <Tag v-else-if="row.status === 'failed'" color="red">{{ row.status }}</Tag>
            <Tag v-else color="default">{{ row.status }}</Tag>
          </template>
          <template #fileSize="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
          <template #createdAt="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
          <template #action="{ row }">
            <Space>
              <Button
                v-if="row.error_message"
                size="small"
                type="text"
                @click="showErrorDetail(row)"
              >
                Error
              </Button>
              <Button size="small" type="error" ghost @click="deleteDocument(row)">
                Delete
              </Button>
            </Space>
          </template>
        </Table>

        <div v-if="documents.length === 0" style="text-align: center; padding: 40px">
          <p>No documents yet. Upload your first document to get started.</p>
        </div>
      </Card>
    </Card>

    <Modal v-model="showErrorModal" title="Processing Error" width="600">
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
import { Message, Modal } from "view-ui-plus";
import { api } from "../../services/api";

const route = useRoute();
const router = useRouter();

const knowledge = ref(null);
const documents = ref([]);
const loading = ref(false);
const uploading = ref(false);
const uploadProgress = ref(0);
const uploadError = ref("");
const uploadSuccess = ref(false);
const reprocessing = ref(false);
const dragover = ref(false);
const showErrorModal = ref(false);
const errorDetail = ref("");
const fileInput = ref(null);

const resourceId = computed(() => route.params.resourceId);

const hasFailedDocuments = computed(() =>
  documents.value.some((d) => d.status === "failed")
);

const columns = computed(() => [
  {
    title: "Filename",
    key: "filename",
    width: 200,
    ellipsis: true,
  },
  {
    title: "Type",
    key: "file_type",
    width: 80,
  },
  {
    title: "Size",
    slot: "fileSize",
    width: 100,
  },
  {
    title: "Status",
    slot: "status",
    width: 100,
  },
  {
    title: "Chunks",
    key: "chunk_count",
    width: 80,
  },
  {
    title: "Tokens",
    key: "total_tokens",
    width: 80,
  },
  {
    title: "Created",
    slot: "createdAt",
    width: 160,
  },
  {
    title: "Action",
    slot: "action",
    width: 160,
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
  await Promise.all([loadKnowledge(), loadDocuments()]);
}

async function loadKnowledge() {
  try {
    const response = await api.getResource(resourceId.value);
    knowledge.value = response;
  } catch (error) {
    Message.error("Failed to load knowledge base");
    console.error(error);
  }
}

async function loadDocuments() {
  loading.value = true;
  try {
    const response = await api.getKnowledgeDocuments(resourceId.value, {
      limit: 100,
      offset: 0,
    });
    documents.value = response.items || [];
  } catch (error) {
    Message.error("Failed to load documents");
    console.error(error);
  } finally {
    loading.value = false;
  }
}

function handleFileSelect(e) {
  const files = e.target.files;
  if (files.length > 0) {
    uploadFile(files[0]);
  }
}

function handleDrop(e) {
  dragover.value = false;
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    uploadFile(files[0]);
  }
}

async function uploadFile(file) {
  uploadError.value = "";
  uploadSuccess.value = false;

  // Validate file type
  const allowedTypes = ["pdf", "docx", "md", "txt"];
  const fileExt = file.name.split(".").pop().toLowerCase();

  if (!allowedTypes.includes(fileExt)) {
    uploadError.value = `Unsupported file type: ${fileExt}. Allowed: ${allowedTypes.join(
      ", "
    )}`;
    return;
  }

  uploading.value = true;
  uploadProgress.value = 0;

  try {
    const formData = new FormData();
    formData.append("file", file);

    // Simulate upload progress
    const interval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += Math.random() * 30;
      }
    }, 200);

    await api.uploadKnowledgeDocument(resourceId.value, formData);

    clearInterval(interval);
    uploadProgress.value = 100;
    uploadSuccess.value = true;

    // Clear input and reload documents
    fileInput.value.value = "";
    setTimeout(() => {
      loadDocuments();
      uploadSuccess.value = false;
      uploading.value = false;
      uploadProgress.value = 0;
    }, 1500);
  } catch (error) {
    uploadError.value =
      error.response?.data?.detail ||
      error.message ||
      "Failed to upload document. Please try again.";
    console.error(error);
    uploading.value = false;
    uploadProgress.value = 0;
  }
}

function deleteDocument(document) {
  Modal.confirm({
    title: "Delete Document",
    content: `Confirm delete document: ${document.filename}?`,
    okText: "Delete",
    cancelText: "Cancel",
    onOk: async () => {
      try {
        await api.deleteKnowledgeDocument(
          resourceId.value,
          document.id
        );
        Message.success("Document deleted successfully");
        loadDocuments();
      } catch (error) {
        Message.error("Failed to delete document");
        console.error(error);
      }
    },
  });
}

async function reprocessFailed() {
  Modal.confirm({
    title: "Reprocess Failed Documents",
    content: "Reprocess all failed documents?",
    okText: "Reprocess",
    cancelText: "Cancel",
    onOk: async () => {
      reprocessing.value = true;
      try {
        await api.reprocessKnowledgeDocuments(resourceId.value);
        Message.success("Failed documents marked for reprocessing");
        loadDocuments();
      } catch (error) {
        Message.error("Failed to reprocess documents");
        console.error(error);
      } finally {
        reprocessing.value = false;
      }
    },
  });
}

function showErrorDetail(document) {
  errorDetail.value = document.error_message || "Unknown error";
  showErrorModal.value = true;
}

function formatFileSize(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

function goBack() {
  router.push({ name: "resources-knowledge-bases" });
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
</style>
