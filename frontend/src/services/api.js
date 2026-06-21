import { API_BASE_URL } from "../config";
import { authState } from "../stores/auth";

function buildHeaders(extraHeaders = {}) {
  const headers = { "Content-Type": "application/json", ...extraHeaders };
  if (authState.token) {
    headers.Authorization = `Bearer ${authState.token}`;
  }
  return headers;
}

export async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: buildHeaders(options.headers || {})
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : {};

  if (!response.ok) {
    const detail = data?.detail || `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return data;
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
  probeMcp(payload) {
    return request("/api/v1/registry/mcp/probe", {
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
  }
};
