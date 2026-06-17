import React, { useState } from 'react';
import { ChevronRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export default function Message({ msg }) {
  const isHuman = msg.role === 'human';
  const [sourcesOpen, setSourcesOpen] = useState(false);

  return (
    <div className={`message ${isHuman ? 'message--human' : 'message--ai'}`}>
      <div className="message-meta">
        <div className="message-avatar">
          {isHuman ? 'U' : 'AI'}
        </div>
        <div className="message-time">
          {msg.timestamp && !isNaN(new Date(msg.timestamp)) 
            ? new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) 
            : ''}
        </div>
      </div>
      <div className="message-bubble">
        {isHuman ? (
          msg.content || ''
        ) : (
          <ReactMarkdown>{msg.content || ''}</ReactMarkdown>
        )}
      </div>

      {msg.sources && msg.sources.length > 0 && (
        <div className="message-sources">
          <div 
            className={`sources-toggle ${sourcesOpen ? 'open' : ''}`}
            onClick={() => setSourcesOpen(!sourcesOpen)}
          >
            <ChevronRight size={12} />
            {msg.sources.length} sources
          </div>
          <div className={`sources-list ${sourcesOpen ? 'visible' : ''}`}>
            {msg.sources.map((src, idx) => (
              <div key={idx} className="source-chip">
                <div className="source-chip-header">
                  Source {idx + 1} • Page {src.page}
                </div>
                <div className="source-chip-text">
                  "{src.content.substring(0, 150)}..."
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
