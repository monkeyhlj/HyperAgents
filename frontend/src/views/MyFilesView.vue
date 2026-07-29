<template>
  <div class="page-shell files-page">
    <section class="page-hero files-hero">
      <div>
        <p class="eyebrow">File Library</p>
        <h1>My Files</h1>
        <p>Download generated artifacts, upload inputs for skills, and keep every agent output in one personal workspace.</p>
      </div>
      <Button :loading="loading" @click="loadFiles">Refresh</Button>
    </section>

    <Card dis-hover class="upload-card">
      <div class="upload-layout">
        <div>
          <h2>Upload working files</h2>
          <p>{{ uploadHint }}</p>
          <div v-if="selectedFiles.length" class="selected-list">
            <Tag v-for="file in selectedFiles" :key="fileKey(file)" color="gold">{{ file.name }}</Tag>
          </div>
        </div>
        <div class="upload-actions">
          <input ref="fileInput" type="file" multiple hidden @change="onSelectFiles" />
          <Button type="primary" ghost @click="pickFiles">Choose Files</Button>
          <Button :disabled="selectedFiles.length === 0" :loading="uploading" type="primary" @click="uploadFiles">
            Upload Selected
          </Button>
        </div>
      </div>
    </Card>

    <Card dis-hover>
      <template #title>
        <div class="library-head">
          <div class="library-title">
            <span>Library</span>
            <Tag color="cyan">{{ filteredFiles.length }} files</Tag>
          </div>
          <Input v-model="fileQuery" class="library-search" clearable search placeholder="Search file path" />
        </div>
      </template>

      <Table :columns="columns" :data="pagedFiles" stripe :loading="loading">
        <template #path="{ row }">
          <span class="file-path">{{ row.path }}</span>
        </template>
        <template #size="{ row }">
          {{ formatSize(row.size_bytes) }}
        </template>
        <template #updated="{ row }">
          {{ row.updated_at ? new Date(row.updated_at).toLocaleString() : "-" }}
        </template>
        <template #action="{ row }">
          <div class="file-actions">
            <Button size="small" type="primary" ghost :loading="downloadingPath === row.path" @click="downloadFile(row)">
              Download
            </Button>
            <Button size="small" type="error" ghost :loading="deletingPath === row.path" @click="confirmDelete(row)">
              Delete
            </Button>
          </div>
        </template>
      </Table>

      <Page
        v-if="filteredFiles.length > pageSize"
        class="table-pagination"
        :total="filteredFiles.length"
        :current="filePage"
        :page-size="pageSize"
        show-total
        @on-change="filePage = $event"
      />

      <div v-if="!loading && filteredFiles.length === 0" class="empty-state">
        No files matched. Adjust the search or ask an agent to generate an artifact.
      </div>
    </Card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { Message, Modal } from "view-ui-plus";
import { api } from "../services/api";

const loading = ref(false);
const uploading = ref(false);
const files = ref([]);
const fileQuery = ref("");
const filePage = ref(1);
const pageSize = 10;
const downloadingPath = ref("");
const deletingPath = ref("");
const selectedFiles = ref([]);
const fileInput = ref(null);

const columns = [
  { title: "Path", slot: "path", minWidth: 420 },
  { title: "Size", slot: "size", width: 120 },
  { title: "Updated", slot: "updated", width: 210 },
  { title: "Action", slot: "action", width: 220, align: "center", fixed: "right" },
];

function formatSize(bytes) {
  const size = Number(bytes || 0);
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

const filteredFiles = computed(() => {
  const q = fileQuery.value.trim().toLowerCase();
  if (!q) return files.value;
  return files.value.filter((item) => String(item.path || "").toLowerCase().includes(q));
});

const pagedFiles = computed(() => {
  const start = (filePage.value - 1) * pageSize;
  return filteredFiles.value.slice(start, start + pageSize);
});

const uploadHint = computed(() => {
  if (!selectedFiles.value.length) return "Select one or more files, then upload them to your personal file library.";
  if (selectedFiles.value.length === 1) return `Ready to upload 1 file: ${selectedFiles.value[0].name}`;
  return `Ready to upload ${selectedFiles.value.length} files.`;
});

function fileKey(file) {
  return `${file.name}-${file.size}-${file.lastModified}`;
}

function pickFiles() {
  fileInput.value?.click();
}

function onSelectFiles(event) {
  const nextFiles = Array.from(event.target.files || []);
  selectedFiles.value = nextFiles;
  event.target.value = "";
}

async function uploadFiles() {
  if (!selectedFiles.value.length) return;

  uploading.value = true;
  try {
    const response = await api.uploadMyFiles(selectedFiles.value);
    Message.success(`Uploaded ${response.count || selectedFiles.value.length} file(s)`);
    selectedFiles.value = [];
    await loadFiles();
  } catch (error) {
    Message.error(error.message || "Upload failed");
  } finally {
    uploading.value = false;
  }
}

async function loadFiles() {
  loading.value = true;
  try {
    const response = await api.listMyFiles();
    files.value = response.files || [];
    filePage.value = 1;
  } catch (error) {
    Message.error(error.message || "Failed to load files");
  } finally {
    loading.value = false;
  }
}

async function downloadFile(row) {
  downloadingPath.value = row.path;
  try {
    const response = await api.downloadMyFile(row.path);
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Download failed (${response.status})`);
    }

    const blob = await response.blob();
    const disposition = response.headers.get("content-disposition") || "";
    const match = /filename="?([^";]+)"?/i.exec(disposition);
    const filename = match?.[1] || row.path.split("/").pop() || "download.bin";

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (error) {
    Message.error(error.message || "Download failed");
  } finally {
    downloadingPath.value = "";
  }
}

function confirmDelete(row) {
  Modal.confirm({
    title: "Delete file",
    content: `Delete ${row.path}? This will remove the file from My Files.`,
    okText: "Delete",
    cancelText: "Cancel",
    loading: true,
    async onOk() {
      try {
        await deleteFile(row);
        Modal.remove();
      } catch (_) {
        Modal.remove();
      }
    },
  });
}

async function deleteFile(row) {
  deletingPath.value = row.path;
  try {
    await api.deleteMyFile(row.path);
    Message.success("File deleted");
    files.value = files.value.filter((item) => item.path !== row.path);
    const maxPage = Math.max(1, Math.ceil(filteredFiles.value.length / pageSize));
    if (filePage.value > maxPage) {
      filePage.value = maxPage;
    }
  } catch (error) {
    Message.error(error.message || "Delete failed");
    throw error;
  } finally {
    deletingPath.value = "";
  }
}
watch(fileQuery, () => {
  filePage.value = 1;
});

onMounted(loadFiles);
</script>

<style scoped>
.files-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.files-hero h1 {
  margin: 0;
  font-size: clamp(30px, 5vw, 48px);
  line-height: 1.05;
}

.upload-layout {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.upload-layout h2 {
  margin: 0 0 6px;
  font-size: 18px;
}

.upload-layout p {
  margin: 0;
  color: var(--muted);
}

.library-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
}

.library-title {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.library-title span {
  color: var(--ink);
  font-size: 17px;
  font-weight: 800;
}

.library-search {
  width: min(360px, 42vw);
  flex: 0 0 auto;
}

.upload-actions,
.selected-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.selected-list {
  margin-top: 12px;
}

.file-path {
  font-family: Consolas, "Courier New", monospace;
  color: #20304a;
}
.file-actions {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  white-space: nowrap;
}

@media (max-width: 760px) {
  .files-hero,
  .upload-layout,
  .library-head {
    display: grid;
  }

  .library-search {
    width: 100%;
  }
}
</style>