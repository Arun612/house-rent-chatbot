import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import ToastContainer from './components/ToastContainer';
import { getDocuments, getSessions } from './api';
import './index.css';

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [toasts, setToasts] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    refreshData();
  }, []);

  const refreshData = async () => {
    try {
      const docs = await getDocuments();
      setDocuments(docs);
      
      const sess = await getSessions();
      setSessions(sess);
    } catch (err) {
      showToast("Failed to load data from server", "error");
    }
  };

  const showToast = (message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };

  const activeSessionData = sessions.find(s => s.session_id === activeSession) || null;

  const handleSetActiveSession = (sessionId) => {
    setActiveSession(sessionId);
    setSidebarOpen(false); // auto-close sidebar on mobile when session is selected
  };

  return (
    <div className="app-shell">
      {/* Mobile overlay backdrop */}
      {sidebarOpen && (
        <div 
          className="sidebar-backdrop" 
          onClick={() => setSidebarOpen(false)} 
        />
      )}

      <Sidebar 
        documents={documents}
        sessions={sessions}
        activeSession={activeSession}
        setActiveSession={handleSetActiveSession}
        refreshData={refreshData}
        showToast={showToast}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <ChatArea 
        session={activeSessionData}
        documents={documents}
        showToast={showToast}
        onOpenSidebar={() => setSidebarOpen(true)}
      />
      <ToastContainer toasts={toasts} />
    </div>
  );
}
