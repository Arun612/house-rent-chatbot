import React, { useState, useEffect } from 'react';
import { UploadCloud, FileText, MessageSquare, Trash2, Home, Box, X } from 'lucide-react';
import { uploadDocument, deleteDocument, createSession, deleteSession } from '../api';

export default function Sidebar({
  documents,
  sessions,
  activeSession,
  setActiveSession,
  refreshData,
  showToast,
  isOpen,
  onClose
}) {
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleCreateSessionFromDoc = async (docId) => {
    try {
      const session = await createSession(docId);
      await refreshData();
      setActiveSession(session.session_id);
      showToast("New conversation started", "success");
    } catch (err) {
      showToast("Failed to start conversation", "error");
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.type !== "application/pdf") {
      showToast("Only PDF files are allowed", "error");
      return;
    }

    setIsUploading(true);
    setProgress(30);

    try {
      const doc = await uploadDocument(file);
      setProgress(80);
      
      if (doc.already_existed) {
        showToast(`ℹ️ "${doc.filename}" already indexed — reusing existing data`, 'info');
      } else {
        showToast(`✓ "${doc.filename}" indexed — ${doc.chunk_count} chunks`, 'success');
      }
      
      setProgress(100);
      
      // Auto-create a session
      const session = await createSession(doc.doc_id);
      await refreshData();
      setActiveSession(session.session_id);

    } catch (err) {
      showToast(err.message || "Upload failed", "error");
    } finally {
      setTimeout(() => {
        setIsUploading(false);
        setProgress(0);
      }, 1000);
      e.target.value = ''; // reset input
    }
  };

  const handleDeleteDoc = async (docId, e) => {
    e.stopPropagation();
    if (!confirm("Delete document and all vectors from Pinecone?")) return;
    try {
      await deleteDocument(docId);
      showToast("Document deleted", "success");
      // If active session belongs to this doc, reset it
      const activeSessData = sessions.find(s => s.session_id === activeSession);
      if (activeSessData && activeSessData.doc_id === docId) {
        setActiveSession(null);
      }
      refreshData();
    } catch (err) {
      showToast("Failed to delete document", "error");
    }
  };

  const handleDeleteSession = async (sessionId, e) => {
    e.stopPropagation();
    try {
      await deleteSession(sessionId);
      if (activeSession === sessionId) setActiveSession(null);
      refreshData();
      showToast("Session deleted", "success");
    } catch (err) {
      showToast("Failed to delete session", "error");
    }
  };

  return (
    <div className={`sidebar ${isOpen ? 'sidebar--open' : ''}`}>
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="logo-icon"><Home size={20} /></div>
        <div className="logo-text">RentChat</div>
        <button className="sidebar-close-btn" onClick={onClose} aria-label="Close sidebar">
          <X size={18} />
        </button>
      </div>

      {/* Upload Zone */}
      <div className="sidebar-section">
        <label className={`upload-zone ${isUploading ? 'drag-over' : ''}`}>
          <div className="upload-icon">
            <UploadCloud size={28} />
          </div>
          <div className="upload-label">Upload Rental PDF</div>
          <div className="upload-sub">Drag & drop or <span className="upload-link">browse</span></div>
          <input 
            type="file" 
            accept="application/pdf" 
            className="hidden" 
            onChange={handleFileUpload}
            disabled={isUploading}
          />
        </label>

        {isUploading && (
          <div className="upload-progress">
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progress}%` }}></div>
            </div>
            <div className="progress-text">Indexing to Pinecone...</div>
          </div>
        )}
      </div>

      {/* Documents */}
      <div className="sidebar-section sidebar-section--grow" style={{ maxHeight: '40%' }}>
        <div className="section-label">
          <Box size={12} /> Documents
          <span className="badge">{documents.length}</span>
        </div>
        <div className="item-list">
          {documents.length === 0 && (
            <div className="empty-hint">No documents uploaded yet</div>
          )}
          {documents.map(doc => (
            <div key={doc.doc_id} className="doc-item">
              <FileText className="doc-item-icon" size={16} />
              <div 
                className="doc-item-info" 
                style={{ cursor: 'pointer' }}
                onClick={() => handleCreateSessionFromDoc(doc.doc_id)}
              >
                <div className="doc-item-name" title={doc.filename}>{doc.filename}</div>
                <div className="doc-item-meta" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {doc.page_count} pages • Click to chat <MessageSquare size={10} />
                </div>
              </div>
              <button className="doc-item-del" onClick={(e) => handleDeleteDoc(doc.doc_id, e)} title="Delete Document">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Sessions */}
      <div className="sidebar-section sidebar-section--grow">
        <div className="section-label">
          <MessageSquare size={12} /> Conversations
          <span className="badge">{sessions.length}</span>
        </div>
        <div className="item-list">
          {sessions.length === 0 && (
            <div className="empty-hint">No active conversations</div>
          )}
          {sessions.map(sess => (
            <div 
              key={sess.session_id} 
              className={`sess-item ${activeSession === sess.session_id ? 'active' : ''}`}
              onClick={() => setActiveSession(sess.session_id)}
            >
              <div className="sess-item-dot"></div>
              <div className="sess-item-info">
                <div className="sess-item-name" title={sess.filename}>{sess.filename}</div>
                <div className="sess-item-meta">
                  {sess.message_count} msgs • {new Date(sess.created_at).toLocaleDateString()}
                </div>
              </div>
              <button className="sess-item-del" onClick={(e) => handleDeleteSession(sess.session_id, e)}>
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
