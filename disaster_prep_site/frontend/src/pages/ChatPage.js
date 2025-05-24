import React, { useState, useEffect, useRef } from 'react';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import './ChatPage.css';

function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null); // For auto-scrolling

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const handleSendMessage = async (inputText) => {
    if (!inputText.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      text: inputText,
      sender: 'user',
      sources: [] // User messages don't have sources
    };
    setMessages(prevMessages => [...prevMessages, userMessage]);
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', { // Proxy should handle this
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: inputText }),
      });

      if (!response.ok) {
        let errData;
        try {
            errData = await response.json();
        } catch (e) {
            // If response is not JSON or if response.json() itself fails
            throw new Error(response.statusText || `HTTP error! status: ${response.status}`);
        }
        throw new Error(errData.error || `HTTP error! status: ${response.status}`);
      }

      const aiData = await response.json();
      const aiMessage = {
        id: Date.now() + 1, // Ensure unique ID
        text: aiData.answer,
        sender: 'ai',
        sources: aiData.sources || [],
      };
      setMessages(prevMessages => [...prevMessages, aiMessage]);

    } catch (error) {
      const errorMessageText = error.message || 'Failed to get response from AI.';
      // Check if the error message from backend is already prefixed, if not, add "Error: "
      const displayMessage = errorMessageText.toLowerCase().startsWith("error:") ? errorMessageText : `Error: ${errorMessageText}`;
      
      const errorMessage = {
        id: Date.now() + 1, // Ensure unique ID
        text: displayMessage,
        sender: 'error', 
        sources: []
      };
      setMessages(prevMessages => [...prevMessages, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-page">
      <div className="chat-messages-area">
        {messages.map(msg => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>
      <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
      {isLoading && <div className="typing-indicator">AIが思考中...</div>}
    </div>
  );
}

export default ChatPage;
