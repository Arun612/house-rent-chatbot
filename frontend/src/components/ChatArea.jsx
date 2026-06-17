import React, { useState, useEffect, useRef } from 'react';
import { Send, FileText, Zap } from 'lucide-react';
import Message from './Message';
import { getHistory, chatWithAgent } from '../api';

export default function ChatArea({ session, showToast }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (session) {
      loadHistory();
    } else {
      setMessages([]);
    }
  }, [session]);

  const loadHistory = async () => {
    try {
      const hist = await getHistory(session.session_id);
      setMessages(hist);
      scrollToBottom();
    } catch (err) {
      showToast("Failed to load chat history", "error");
    }
  };

  const scrollToBottom = () => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  const handleSend = async () => {
    if (!input.trim() || !session || isTyping) return;
    
    const userMsg = { role: 'human', content: input.trim(), timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);
    scrollToBottom();

    try {
      const result = await chatWithAgent(session.session_id, userMsg.content);
      const aiMsg = { 
        role: 'ai', 
        content: result.answer, 
        sources: result.sources,
        timestamp: new Date().toISOString() 
      };
      setMessages(prev => [...prev, aiMsg]);
      scrollToBottom();
    } catch (err) {
      showToast("Failed to send message", "error");
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!session) {
    return (
      <div className="chat-area">
        <div className="chat-header">
          <div className="chat-header-info">
            <div className="chat-doc-icon"><Zap size={20} /></div>
            <div>
              <div className="chat-doc-name">Ready to assist</div>
              <div className="chat-session-label">Select a conversation or upload a PDF</div>
            </div>
          </div>
        </div>
        <div className="messages-wrapper" style={{ justifyContent: 'center' }}>
          <div className="welcome-state">
            <div className="welcome-icon"><FileText size={42} /></div>
            <h2>Welcome to RentChat</h2>
            <p>Upload a rental agreement, lease, or any property document. I will read it and answer your questions instantly based strictly on the text.</p>
            <div className="welcome-tips">
              <div className="tip"><span>💡</span> "What is the security deposit amount?"</div>
              <div className="tip"><span>💡</span> "Are pets allowed?"</div>
              <div className="tip"><span>💡</span> "Who pays for utilities?"</div>
              <div className="tip"><span>💡</span> "What happens if I break the lease early?"</div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-area">
      <div className="chat-header">
        <div className="chat-header-info">
          <div className="chat-doc-icon"><FileText size={20} /></div>
          <div>
            <div className="chat-doc-name">{session.filename}</div>
            <div className="chat-session-label">Session: {session.session_id}</div>
          </div>
        </div>
      </div>

      <div className="messages-wrapper">
        <div className="messages-list">
          {messages.length === 0 && (
            <div className="welcome-state" style={{ marginTop: '20px' }}>
              <h2>Ask anything about this document</h2>
              <p>Try asking about rent, deposits, maintenance rules, or notice periods.</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <Message key={i} msg={msg} />
          ))}
          {isTyping && (
            <div className="typing-indicator">
              <div className="typing-bubble">
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="input-bar">
        <div className="input-wrapper">
          <textarea
            className="question-input"
            rows="1"
            placeholder="Ask a question about the document..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isTyping}
          />
          <button 
            className="send-btn" 
            onClick={handleSend}
            disabled={isTyping || !input.trim()}
          >
            <Send size={18} />
          </button>
        </div>
        <div className="input-hint">RentChat AI can make mistakes. Always verify important details.</div>
      </div>
    </div>
  );
}
