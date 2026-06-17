const API_BASE = "http://localhost:8000";

export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};

export const getDocuments = async () => {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error("Failed to fetch documents");
  return res.json();
};

export const deleteDocument = async (docId) => {
  const res = await fetch(`${API_BASE}/documents/${docId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete document");
  return res.json();
};

export const getSessions = async () => {
  const res = await fetch(`${API_BASE}/sessions`);
  if (!res.ok) throw new Error("Failed to fetch sessions");
  return res.json();
};

export const createSession = async (docId) => {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ doc_id: docId }),
  });
  if (!res.ok) throw new Error("Failed to create session");
  return res.json();
};

export const getHistory = async (sessionId) => {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/history`);
  if (!res.ok) throw new Error("Failed to fetch history");
  const data = await res.json();
  return data.messages || [];
};

export const deleteSession = async (sessionId) => {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete session");
  return res.json();
};

export const chatWithAgent = async (sessionId, question) => {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, question }),
  });
  if (!res.ok) throw new Error("Failed to chat");
  return res.json();
};
