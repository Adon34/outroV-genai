// frontend/src/components/ChatInterface.js
import React, { useState, useRef, useEffect } from 'react';
import './ChatInterface.css';
import apiClient from '../services/api';  // <-- importa o cliente

const ChatInterface = ({ token, userId }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [conversationId, setConversationId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      // Usando o apiClient que já tem o token via interceptor
      const data = await apiClient.sendMessage(inputMessage, conversationId);

      const assistantMessage = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);
      setConversationId(data.conversation_id);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Desculpe, ocorreu um erro. Tente novamente.',
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>Assistente Pessoal</h2>
        <p>Pergunte sobre dieta, treinos e nutrição</p>
      </div>
      
      <div className="messages-container">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <div className="message-content">
              <strong>{msg.role === 'user' ? 'Você' : 'Assistente'}:</strong>
              <p>{msg.content}</p>
              {msg.sources && msg.sources.length > 0 && (
                <small className="sources">
                  Fontes: {msg.sources.map(s => s.category).join(', ')}
                </small>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message assistant loading">
            <div className="message-content">
              <p>Digitando...</p>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="input-container">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Digite sua mensagem..."
          disabled={isLoading}
        />
        <button onClick={sendMessage} disabled={isLoading}>
          Enviar
        </button>
      </div>
    </div>
  );
};

export default ChatInterface;