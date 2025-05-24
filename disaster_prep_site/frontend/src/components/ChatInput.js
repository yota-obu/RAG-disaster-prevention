import React, { useState } from 'react';
import './ChatInput.css';

function ChatInput({ onSendMessage, isLoading }) {
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;
    onSendMessage(inputValue);
    setInputValue('');
  };

  return (
    <form onSubmit={handleSubmit} className="chat-input-form">
      <input
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder="防災に関する質問を入力してください..."
        disabled={isLoading}
        aria-label="Chat input"
      />
      <button type="submit" disabled={isLoading}>
        送信
      </button>
    </form>
  );
}

export default ChatInput;
