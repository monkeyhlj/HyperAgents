import { API_BASE_URL } from "../config";
import { authState } from "../stores/auth";

function buildHeaders(extraHeaders = {}, includeContentType = true) {
  const headers = includeContentType ? { "Content-Type": "application/json", ...extraHeaders } : { ...extraHeaders };
  if (authState.token) {
    headers.Authorization = `Bearer ${authState.token}`;
  }
  return headers;
}

async function parseResponse(response) {
  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = text ? { detail: text } : {};
  }

  if (!response.ok) {
    const detail = data?.detail || `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return data;
}

export async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: buildHeaders(options.headers || {})
  });

  return parseResponse(response);
}

function withQuery(path, query = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  });
  const text = params.toString();
  return text ? `${path}?${text}` : path;
}

export const api = {
  register(payload) {
    return request("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  login(payload) {
    return request("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  me() {
    return request("/api/v1/auth/me");
  },
  searchUsers(queryText, limit = 10) {
    return request(withQuery("/api/v1/auth/users/search", { q: queryText, limit }));
  },
  listProjects() {
    return request("/api/v1/projects");
  },
  getProject(projectId) {
    return request(`/api/v1/projects/${projectId}`);
  },
  createProject(payload) {
    return request("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  updateProject(projectId, payload) {
    return request(`/api/v1/projects/${projectId}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
  },
  deleteProject(projectId) {
    return request(`/api/v1/projects/${projectId}`, {
      method: "DELETE"
    });
  },
  addProjectMember(projectId, payload) {
    return request(`/api/v1/projects/${projectId}/members`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  removeProjectMember(projectId, memberId) {
    return request(`/api/v1/projects/${projectId}/members/${memberId}`, {
      method: "DELETE"
    });
  },
  grantProjectMemberManager(projectId, payload) {
    return request(`/api/v1/projects/${projectId}/member-managers`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  revokeProjectMemberManager(projectId, memberId) {
    return request(`/api/v1/projects/${projectId}/member-managers/${memberId}`, {
      method: "DELETE"
    });
  },
  listResources(projectId, query = {}) {
    return request(withQuery(`/api/v1/resources/projects/${projectId}`, query));
  },
  listOwnedResources(query = {}) {
    return request(withQuery("/api/v1/resources/mine", query));
  },
  previewResourceChat(payload) {
    return request("/api/v1/resources/preview-chat", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  listCodeExecutionAudits(query = {}) {
    return request(withQuery("/api/v1/chat/code-execution-audits", query));
  },
  listMyFiles() {
    return request("/api/v1/files/me");
  },
  downloadMyFile(filePath) {
    const headers = {};
    if (authState.token) {
      headers.Authorization = `Bearer ${authState.token}`;
    }
    return fetch(`${API_BASE_URL}${withQuery("/api/v1/files/me/download", { path: filePath })}`, {
      method: "GET",
      headers,
    });
  },
  deleteMyFile(filePath) {
    return request(withQuery("/api/v1/files/me", { path: filePath }), {
      method: "DELETE",
    });
  },  async uploadMyFiles(files, targetDir = "") {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file, file.webkitRelativePath || file.name);
    });
    if (targetDir) {
      formData.append("target_dir", targetDir);
    }

    const headers = buildHeaders({}, false);
    const response = await fetch(`${API_BASE_URL}/api/v1/files/me/upload`, {
      method: "POST",
      headers,
      body: formData,
    });
    return parseResponse(response);
  },
  probeMcp(payload) {
    return request("/api/v1/registry/mcp/probe", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  listProviderConnections(projectId) {
    return request(`/api/v1/provider-connections/projects/${projectId}`);
  },
  createProviderConnection(projectId, payload) {
    return request(`/api/v1/provider-connections/projects/${projectId}`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  updateProviderConnection(connectionId, payload) {
    return request(`/api/v1/provider-connections/${connectionId}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
  },
  probeProviderModels(projectId, payload) {
    return request(`/api/v1/provider-connections/projects/${projectId}/probe-models`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  testProviderConnectionDraft(projectId, payload) {
    return request(`/api/v1/provider-connections/projects/${projectId}/test`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  listDefaultResources(query = {}) {
    return request(withQuery("/api/v1/resources/defaults", query));
  },
  listProjectAgents(projectId) {
    return request(withQuery(`/api/v1/resources/projects/${projectId}`, { kind: "agent", include_defaults: false }));
  },
  createResource(projectId, payload) {
    return request(`/api/v1/resources/projects/${projectId}`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  getResource(resourceId) {
    return request(`/api/v1/resources/${resourceId}`);
  },
  updateResource(resourceId, payload) {
    return request(`/api/v1/resources/${resourceId}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
  },
  deleteResource(resourceId) {
    return request(`/api/v1/resources/${resourceId}`, {
      method: "DELETE"
    });
  },
  createSession(projectId, title) {
    return request(`/api/v1/chat/projects/${projectId}/sessions`, {
      method: "POST",
      body: JSON.stringify({ title })
    });
  },
  listSessions(projectId) {
    return request(`/api/v1/chat/projects/${projectId}/sessions`);
  },
  listRuns(sessionId) {
    return request(`/api/v1/chat/sessions/${sessionId}/runs`);
  },
  listRunEvents(runId) {
    return request(`/api/v1/chat/runs/${runId}/events`);
  },
  sendMessage(sessionId, payload) {
    return request(`/api/v1/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  listMessages(sessionId) {
    return request(`/api/v1/chat/sessions/${sessionId}/messages`);
  },
  getKnowledgeDocuments(knowledgeId, query = {}) {
    return request(withQuery(`/api/v1/knowledge/${knowledgeId}/documents`, query));
  },
  uploadKnowledgeDocument(knowledgeId, formData) {
    const headers = { Authorization: "" };
    if (authState.token) {
      headers.Authorization = `Bearer ${authState.token}`;
    }
    return fetch(`${API_BASE_URL}/api/v1/knowledge/${knowledgeId}/documents/upload`, {
      method: "POST",
      body: formData,
      headers: {
        ...headers
      }
    }).then(async (response) => {
      const text = await response.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        data = text ? { detail: text } : {};
      }

      if (!response.ok) {
        const detail = data?.detail || `Request failed (${response.status})`;
        const error = new Error(detail);
        error.response = { data };
        throw error;
      }
      return data;
    });
  },
  deleteKnowledgeDocument(knowledgeId, documentId) {
    return request(`/api/v1/knowledge/${knowledgeId}/documents/${documentId}`, {
      method: "DELETE"
    });
  },
  reprocessKnowledgeDocuments(knowledgeId) {
    return request(`/api/v1/knowledge/${knowledgeId}/reprocess`, {
      method: "POST"
    });
  },

  // ==================== Skills APIs ====================
  
  getSkill(skillId) {
    return request(`/api/v1/skills/${skillId}`);
  },

  listProjectSkills(projectId, query = {}) {
    return request(withQuery(`/api/v1/skills/projects/${projectId}/skills`, query));
  },

  uploadSkill(skillId, formData) {
    const headers = { Authorization: "" };
    if (authState.token) {
      headers.Authorization = `Bearer ${authState.token}`;
    }
    return fetch(`${API_BASE_URL}/api/v1/skills/${skillId}/upload`, {
      method: "POST",
      body: formData,
      headers: {
        ...headers
      }
    }).then(async (response) => {
      const text = await response.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        data = text ? { detail: text } : {};
      }

      if (!response.ok) {
        const detail = data?.detail || `Request failed (${response.status})`;
        const error = new Error(detail);
        error.response = { data };
        throw error;
      }
      return data;
    });
  },

  uploadSkillFolder(skillId, formData) {
    const headers = { Authorization: "" };
    if (authState.token) {
      headers.Authorization = `Bearer ${authState.token}`;
    }
    return fetch(`${API_BASE_URL}/api/v1/skills/${skillId}/upload-folder`, {
      method: "POST",
      body: formData,
      headers: {
        ...headers
      }
    }).then(async (response) => {
      const text = await response.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        data = text ? { detail: text } : {};
      }

      if (!response.ok) {
        const detail = data?.detail || `Request failed (${response.status})`;
        const error = new Error(detail);
        error.response = { data };
        throw error;
      }
      return data;
    });
  },

  getSkillFileContent(skillId, filePath) {
    return request(withQuery(`/api/v1/skills/${skillId}/files/content`, { path: filePath }));
  },

  testSkill(skillId, inputData) {
    return request(`/api/v1/skills/${skillId}/test`, {
      method: "POST",
      body: JSON.stringify(inputData)
    });
  },

  bindSkillToAgent(agentId, skillBinding) {
    return request(`/api/v1/skills/agents/${agentId}/skills`, {
      method: "POST",
      body: JSON.stringify(skillBinding)
    });
  },

  unbindSkillFromAgent(agentId, skillId) {
    return request(`/api/v1/skills/agents/${agentId}/skills/${skillId}`, {
      method: "DELETE"
    });
  },

  listAgentBindings(agentId) {
    return request(`/api/v1/skills/agents/${agentId}/skills`);
  },

  updateAgentSkillBinding(agentId, skillId, updates) {
    return request(`/api/v1/skills/agents/${agentId}/skills/${skillId}`, {
      method: "PATCH",
      body: JSON.stringify(updates)
    });
  },


  // ==================== Workflow APIs ====================

  validateWorkflow(workflowId) {
    return request(`/api/v1/workflows/${workflowId}/validate`, {
      method: "POST"
    });
  },

  runWorkflow(workflowId, payload) {
    return request(`/api/v1/workflows/${workflowId}/run`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  listWorkflowRuns(workflowId, query = {}) {
    return request(withQuery(`/api/v1/workflows/${workflowId}/runs`, query));
  },

  getWorkflowRun(workflowId, runId) {
    return request(`/api/v1/workflows/${workflowId}/runs/${runId}`);
  },
  listSkillBindings(skillId) {
    return request(`/api/v1/skills/${skillId}/agents`);
  }
};
