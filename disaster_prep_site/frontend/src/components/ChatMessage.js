import React from 'react';
import './ChatMessage.css';

function ChatMessage({ message }) {
  const { text, sender, sources } = message;
  
  let messageClass = 'message-bubble';
  if (sender === 'user') {
    messageClass += ' user-message';
  } else if (sender === 'ai') {
    messageClass += ' ai-message';
  } else if (sender === 'error') {
    messageClass += ' error-message';
  }

  const showSources = sender === 'ai' && sources && sources.length > 0;

  return (
    <div className={`chat-message-row ${sender === 'user' ? 'row-user' : 'row-ai'}`}>
      <div className={messageClass}>
        <div className="message-text">{text}</div>
        {showSources && (
          <div className="message-sources">
            <strong>情報源:</strong>
            <ul>
              {sources.map((source, index) => (
                <li key={index}>
                  {source.filename} (Page: {source.page})
                </li>
              ))}
            </ul>
          </div>
        )}
        {sender === 'error' && <div className="error-indicator">!</div>}
      </div>
    </div>
  );
}

export default ChatMessage;
