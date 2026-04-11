// frontend/src/components/ChatInterface.js
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useAgentChat } from '../hooks/useAgentChat';
import api from '../services/api';

// Componente de modal customizado para confirmação
const ConfirmDialog = ({ message, onConfirm, onCancel, isOpen }) => {
    if (!isOpen) return null;
    
    return (
        <div className="confirm-overlay">
            <div className="confirm-dialog">
                <p>{message}</p>
                <div className="confirm-buttons">
                    <button onClick={onCancel} className="confirm-btn cancel">Cancelar</button>
                    <button onClick={onConfirm} className="confirm-btn confirm">Confirmar</button>
                </div>
            </div>
            <style jsx>{`
                .confirm-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0,0,0,0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 2000;
                }
                .confirm-dialog {
                    background: white;
                    border-radius: 12px;
                    padding: 24px;
                    max-width: 400px;
                    text-align: center;
                }
                .confirm-buttons {
                    display: flex;
                    gap: 12px;
                    justify-content: center;
                    margin-top: 20px;
                }
                .confirm-btn {
                    padding: 8px 20px;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                }
                .confirm-btn.cancel {
                    background: #e5e7eb;
                    color: #4b5563;
                }
                .confirm-btn.confirm {
                    background: #3b82f6;
                    color: white;
                }
            `}</style>
        </div>
    );
};

const ChatInterface = ({ conversationId: externalConversationId, onWorkoutCreated, onProfileUpdated }) => {
    const [inputMessage, setInputMessage] = useState('');
    const [autoCreate, setAutoCreate] = useState(true);
    const [showHistory, setShowHistory] = useState(false);
    const [conversations, setConversations] = useState([]);
    const [currentConversationId, setCurrentConversationId] = useState(externalConversationId);
    const [isLoadingHistory, setIsLoadingHistory] = useState(false);
    const [showSuggestions, setShowSuggestions] = useState(true);
    const [isStreaming, setIsStreaming] = useState(false);
    
    // Estados para modais de confirmação
    const [confirmDialog, setConfirmDialog] = useState({ isOpen: false, message: '', onConfirm: null });
    
    const { messages, isLoading, sendMessage, lastAction, clearMessages, setMessages } = useAgentChat(currentConversationId);
    const messagesEndRef = useRef(null);
    const textareaRef = useRef(null);

    // Função customizada de confirmação
    const showConfirm = (message, onConfirm) => {
        setConfirmDialog({
            isOpen: true,
            message,
            onConfirm: () => {
                setConfirmDialog({ isOpen: false, message: '', onConfirm: null });
                onConfirm();
            }
        });
    };

    // Função de notificação
    const showNotification = (message, type = 'info') => {
        const toast = document.createElement('div');
        toast.className = `notification notification-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 12px 20px;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            border-radius: 8px;
            z-index: 1000;
            animation: slideIn 0.3s ease;
        `;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    };

    // Carregar conversas
    useEffect(() => {
        loadConversations();
        
        const savedConversationId = localStorage.getItem('lastConversationId');
        if (savedConversationId && !currentConversationId) {
            setCurrentConversationId(parseInt(savedConversationId));
        }
    }, []);

    useEffect(() => {
        if (currentConversationId) {
            localStorage.setItem('lastConversationId', currentConversationId);
        }
    }, [currentConversationId]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    useEffect(() => {
        if (lastAction) {
            switch (lastAction.type) {
                case 'workout_created':
                    if (onWorkoutCreated) onWorkoutCreated(lastAction.data);
                    showNotification('Treino criado com sucesso! 💪', 'success');
                    break;
                case 'profile_updated':
                    if (onProfileUpdated) onProfileUpdated(lastAction.data);
                    showNotification('Perfil atualizado com sucesso! 📊', 'info');
                    break;
                case 'meal_added':
                    showNotification('Refeição adicionada! 🍽️', 'success');
                    break;
                default:
                    break;
            }
        }
    }, [lastAction, onWorkoutCreated, onProfileUpdated]);

    const loadConversations = async () => {
        setIsLoadingHistory(true);
        try {
            const data = await api.getConversations();
            // O data agora tem { conversations: [] }
            const conversationsList = data.conversations || data || [];
            setConversations(conversationsList);
        } catch (error) {
            console.error('Error loading conversations:', error);
            setConversations([]);
        } finally {
            setIsLoadingHistory(false);
        }
    };

    const loadConversation = async (convId) => {
        if (isLoading) return;
        
        setCurrentConversationId(convId);
        setShowHistory(false);
        
        try {
            const data = await api.getConversationMessages(convId, 0, 100);
            const historyMessages = data.messages || [];
            
            const formattedMessages = historyMessages.map(msg => ({
                id: msg.id,
                role: msg.role,
                content: msg.content,
                timestamp: msg.created_at ? new Date(msg.created_at) : new Date(),
                action: msg.message_metadata?.action,
                actionData: msg.message_metadata?.action_data
            }));
            
            setMessages(formattedMessages);
        } catch (error) {
            console.error('Error loading conversation messages:', error);
            showNotification('Erro ao carregar conversa', 'error');
        }
    };

    const startNewConversation = () => {
        if (messages.length > 0) {
            showConfirm('Iniciar nova conversa? A conversa atual será salva.', () => {
                clearMessages();
                setCurrentConversationId(null);
                localStorage.removeItem('lastConversationId');
                setShowSuggestions(true);
                showNotification('Nova conversa iniciada!', 'info');
            });
        } else {
            clearMessages();
            setCurrentConversationId(null);
            setShowSuggestions(true);
        }
    };

    const deleteConversation = async (convId, event) => {
        event.stopPropagation();
        showConfirm('Tem certeza que deseja excluir esta conversa?', async () => {
            try {
                await api.deleteConversation(convId);
                await loadConversations();
                if (currentConversationId === convId) {
                    startNewConversation();
                }
                showNotification('Conversa excluída!', 'success');
            } catch (error) {
                console.error('Error deleting conversation:', error);
                showNotification('Erro ao excluir conversa', 'error');
            }
        });
    };

    const exportConversation = () => {
        if (messages.length === 0) {
            showNotification('Nenhuma mensagem para exportar', 'error');
            return;
        }
        
        const exportData = {
            conversation_id: currentConversationId,
            exported_at: new Date().toISOString(),
            messages: messages.map(msg => ({
                role: msg.role,
                content: msg.content,
                timestamp: msg.timestamp,
                action: msg.action
            }))
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `conversation_${currentConversationId || 'new'}_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        showNotification('Conversa exportada com sucesso!', 'success');
    };

    const handleSendMessage = async (e) => {
        e.preventDefault();
        if (!inputMessage.trim() || isLoading) return;

        const message = inputMessage;
        setInputMessage('');
        setShowSuggestions(false);
        setIsStreaming(true);
        
        try {
            await sendMessage(message, autoCreate);
        } catch (error) {
            console.error('Error sending message:', error);
            showNotification('Erro ao enviar mensagem', 'error');
        } finally {
            setIsStreaming(false);
        }
    };

    const handleExtractProfile = async () => {
        if (!inputMessage.trim()) {
            showNotification('Digite uma mensagem primeiro', 'error');
            return;
        }
        
        try {
            const result = await api.extractProfileFromMessage(inputMessage);
            if (result.success && result.updated_fields) {
                const fields = Object.entries(result.updated_fields)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join('\n');
                showNotification(`Perfil atualizado:\n${fields}`, 'success');
                if (onProfileUpdated) onProfileUpdated(result.updated_fields);
            } else if (result.needs_more_info) {
                showNotification(result.message || 'Preciso de mais informações', 'info');
            }
        } catch (error) {
            console.error('Erro ao extrair perfil:', error);
            showNotification('Erro ao extrair dados do perfil', 'error');
        }
    };

    const getActionIcon = (action) => {
        switch (action) {
            case 'workout_created': return '💪';
            case 'profile_updated': return '📊';
            case 'meal_added': return '🍽️';
            default: return '🤖';
        }
    };

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        
        if (date.toDateString() === today.toDateString()) {
            return `Hoje, ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        } else if (date.toDateString() === yesterday.toDateString()) {
            return `Ontem, ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        }
        return date.toLocaleDateString();
    };

    const suggestions = [
        { text: "💪 Criar treino para iniciantes", message: "Crie um treino para iniciantes" },
        { text: "🍽️ Sugerir dieta saudável", message: "Me sugira uma dieta saudável" },
        { text: "📊 Calcular meu IMC", message: "Como calcular meu IMC?" },
        { text: "🏃 Melhores exercícios para perder peso", message: "Quais os melhores exercícios para perder peso?" },
        { text: "🥗 Refeição pós-treino", message: "Me sugira uma refeição pós-treino" },
        { text: "💧 Dicas de hidratação", message: "Dicas de hidratação para treino" }
    ];

    return (
        <>
            <ConfirmDialog 
                isOpen={confirmDialog.isOpen}
                message={confirmDialog.message}
                onConfirm={confirmDialog.onConfirm}
                onCancel={() => setConfirmDialog({ isOpen: false, message: '', onConfirm: null })}
            />
            
            <div className="chat-interface">
                {/* Header - mesmo código de antes */}
                <div className="chat-header">
                    <div className="header-left">
                        <h2>💬 Assistente IA</h2>
                        {currentConversationId && (
                            <span className="conversation-badge">
                                #{currentConversationId}
                            </span>
                        )}
                    </div>
                    <div className="header-right">
                        <label className="auto-create-toggle">
                            <span>🤖 Modo autônomo</span>
                            <input
                                type="checkbox"
                                checked={autoCreate}
                                onChange={(e) => setAutoCreate(e.target.checked)}
                            />
                            <span className="toggle-slider"></span>
                        </label>
                        <button 
                            onClick={() => setShowHistory(!showHistory)} 
                            className="history-btn"
                            title="Histórico"
                        >
                            📋
                        </button>
                        <button 
                            onClick={exportConversation} 
                            className="export-btn"
                            title="Exportar conversa"
                            disabled={messages.length === 0}
                        >
                            📤
                        </button>
                        <button 
                            onClick={startNewConversation} 
                            className="new-chat-btn"
                            title="Nova conversa"
                        >
                            ✨
                        </button>
                    </div>
                </div>

                {/* Restante do componente - manter o mesmo código de antes */}
                {/* Sidebar de Histórico */}
                {showHistory && (
                    <div className="history-sidebar">
                        <div className="history-header">
                            <h3>📋 Conversas Anteriores</h3>
                            <button onClick={() => setShowHistory(false)}>✕</button>
                        </div>
                        <div className="history-list">
                            {isLoadingHistory ? (
                                <div className="loading-history">
                                    <div className="spinner-small"></div>
                                    <p>Carregando...</p>
                                </div>
                            ) : conversations.length === 0 ? (
                                <p className="empty-history">Nenhuma conversa anterior</p>
                            ) : (
                                conversations.map((conv) => (
                                    <div 
                                        key={conv.id} 
                                        className={`history-item ${currentConversationId === conv.id ? 'active' : ''}`}
                                        onClick={() => loadConversation(conv.id)}
                                    >
                                        <div className="history-item-content">
                                            <div className="history-title">
                                                {conv.title || `Conversa ${conv.id}`}
                                            </div>
                                            <div className="history-date">
                                                {formatDate(conv.created_at)}
                                            </div>
                                            <div className="history-preview">
                                                {conv.preview || `${conv.messages_count || 0} mensagens`}
                                            </div>
                                        </div>
                                        <button 
                                            className="delete-conv-btn"
                                            onClick={(e) => deleteConversation(conv.id, e)}
                                            title="Excluir conversa"
                                        >
                                            🗑️
                                        </button>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}

                {/* Messages - mesmo código de antes */}
                <div className="messages-container">
                    {messages.length === 0 && showSuggestions ? (
                        <div className="welcome-screen">
                            <div className="welcome-icon">🤖</div>
                            <h2>Olá! Eu sou seu assistente de saúde</h2>
                            <p>Posso ajudar você com treinos, dieta e acompanhamento de saúde</p>
                            
                            <div className="suggestions-grid">
                                <h4>Sugestões rápidas:</h4>
                                <div className="suggestions-list">
                                    {suggestions.map((suggestion, idx) => (
                                        <button
                                            key={idx}
                                            className="suggestion-btn"
                                            onClick={() => {
                                                setInputMessage(suggestion.message);
                                                setShowSuggestions(false);
                                                setTimeout(() => {
                                                    const formEvent = { preventDefault: () => {} };
                                                    handleSendMessage(formEvent);
                                                }, 100);
                                            }}
                                        >
                                            {suggestion.text}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="messages-list">
                            {messages.map((msg, idx) => (
                                <div
                                    key={msg.id || idx}
                                    className={`message ${msg.role === 'user' ? 'user-message' : 'assistant-message'}`}
                                >
                                    <div className="message-avatar">
                                        {msg.role === 'user' ? '👤' : getActionIcon(msg.action)}
                                    </div>
                                    <div className="message-content">
                                        {msg.role === 'assistant' && msg.action && (
                                            <div className="message-badge">
                                                {msg.action === 'workout_created' && '💪 Treino criado'}
                                                {msg.action === 'profile_updated' && '📊 Perfil atualizado'}
                                                {msg.action === 'meal_added' && '🍽️ Refeição adicionada'}
                                            </div>
                                        )}
                                        <div className="message-text">{msg.content}</div>
                                        <div className="message-time">
                                            {msg.timestamp?.toLocaleTimeString()}
                                        </div>
                                    </div>
                                </div>
                            ))}
                            
                            {isLoading && (
                                <div className="message assistant-message">
                                    <div className="message-avatar">🤖</div>
                                    <div className="message-content">
                                        <div className="typing-indicator">
                                            <span></span>
                                            <span></span>
                                            <span></span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <form onSubmit={handleSendMessage} className="input-area">
                    <div className="input-wrapper">
                        <textarea
                            ref={textareaRef}
                            value={inputMessage}
                            onChange={(e) => setInputMessage(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSendMessage(e);
                                }
                            }}
                            placeholder="Digite sua mensagem... (Enter para enviar)"
                            rows={1}
                            disabled={isLoading}
                            className="message-input"
                        />
                        <button
                            type="button"
                            onClick={handleExtractProfile}
                            className="extract-btn"
                            title="Extrair dados do perfil da mensagem"
                            disabled={!inputMessage.trim()}
                        >
                            📊
                        </button>
                        <button
                            type="submit"
                            disabled={isLoading || !inputMessage.trim()}
                            className="send-btn"
                        >
                            {isLoading ? '⏳' : '📤'}
                        </button>
                    </div>
                </form>

                <style jsx>{`
                    /* Estilos - mesmo código de antes */
                    .chat-interface {
                        display: flex;
                        flex-direction: column;
                        height: 100%;
                        background: #f9fafb;
                        position: relative;
                    }
                    .chat-header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 16px 20px;
                        background: white;
                        border-bottom: 1px solid #e5e7eb;
                        flex-wrap: wrap;
                        gap: 10px;
                    }
                    .header-left {
                        display: flex;
                        align-items: center;
                        gap: 12px;
                    }
                    .header-left h2 {
                        margin: 0;
                        font-size: 18px;
                        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                    }
                    .conversation-badge {
                        font-size: 11px;
                        padding: 4px 8px;
                        background: #e5e7eb;
                        border-radius: 20px;
                        color: #4b5563;
                        font-family: monospace;
                    }
                    .header-right {
                        display: flex;
                        align-items: center;
                        gap: 12px;
                    }
                    .auto-create-toggle {
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        font-size: 13px;
                        cursor: pointer;
                    }
                    .auto-create-toggle input {
                        display: none;
                    }
                    .toggle-slider {
                        width: 40px;
                        height: 20px;
                        background: #cbd5e1;
                        border-radius: 20px;
                        position: relative;
                        transition: 0.3s;
                    }
                    .toggle-slider:before {
                        content: "";
                        width: 16px;
                        height: 16px;
                        background: white;
                        border-radius: 50%;
                        position: absolute;
                        top: 2px;
                        left: 2px;
                        transition: 0.3s;
                    }
                    .auto-create-toggle input:checked + .toggle-slider {
                        background: #3b82f6;
                    }
                    .auto-create-toggle input:checked + .toggle-slider:before {
                        transform: translateX(20px);
                    }
                    .history-btn, .export-btn, .new-chat-btn {
                        padding: 6px 10px;
                        border: none;
                        border-radius: 8px;
                        cursor: pointer;
                        font-size: 16px;
                        transition: all 0.2s;
                    }
                    .history-btn { background: #f3f4f6; }
                    .export-btn { background: #f3f4f6; }
                    .new-chat-btn { background: #3b82f6; color: white; }
                    .export-btn:disabled {
                        opacity: 0.5;
                        cursor: not-allowed;
                    }
                    .history-btn:hover, .export-btn:hover:not(:disabled) {
                        background: #e5e7eb;
                    }
                    .new-chat-btn:hover { background: #2563eb; }
                    .history-sidebar {
                        position: absolute;
                        top: 70px;
                        left: 20px;
                        width: 320px;
                        max-height: calc(100% - 100px);
                        background: white;
                        border-radius: 12px;
                        box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1);
                        z-index: 20;
                        display: flex;
                        flex-direction: column;
                        overflow: hidden;
                    }
                    .history-header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 15px;
                        border-bottom: 1px solid #e5e7eb;
                    }
                    .history-header button {
                        background: none;
                        border: none;
                        font-size: 18px;
                        cursor: pointer;
                    }
                    .history-list {
                        flex: 1;
                        overflow-y: auto;
                        max-height: 400px;
                    }
                    .history-item {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 12px 15px;
                        border-bottom: 1px solid #f3f4f6;
                        cursor: pointer;
                        transition: background 0.2s;
                    }
                    .history-item:hover {
                        background: #f9fafb;
                    }
                    .history-item.active {
                        background: #e0e7ff;
                        border-left: 3px solid #3b82f6;
                    }
                    .history-item-content {
                        flex: 1;
                        overflow: hidden;
                    }
                    .history-title {
                        font-size: 14px;
                        font-weight: 500;
                        white-space: nowrap;
                        overflow: hidden;
                        text-overflow: ellipsis;
                    }
                    .history-date {
                        font-size: 11px;
                        color: #6b7280;
                        margin-top: 2px;
                    }
                    .history-preview {
                        font-size: 11px;
                        color: #9ca3af;
                        margin-top: 4px;
                        white-space: nowrap;
                        overflow: hidden;
                        text-overflow: ellipsis;
                    }
                    .delete-conv-btn {
                        background: none;
                        border: none;
                        font-size: 14px;
                        cursor: pointer;
                        opacity: 0.5;
                        transition: opacity 0.2s;
                    }
                    .delete-conv-btn:hover {
                        opacity: 1;
                    }
                    .messages-container {
                        flex: 1;
                        overflow-y: auto;
                        padding: 20px;
                    }
                    .welcome-screen {
                        text-align: center;
                        padding: 60px 20px;
                    }
                    .welcome-icon {
                        font-size: 64px;
                        margin-bottom: 20px;
                    }
                    .welcome-screen h2 {
                        margin: 0 0 10px;
                        font-size: 24px;
                    }
                    .suggestions-grid {
                        margin-top: 40px;
                    }
                    .suggestions-list {
                        display: flex;
                        flex-wrap: wrap;
                        gap: 10px;
                        justify-content: center;
                        margin-top: 15px;
                    }
                    .suggestion-btn {
                        padding: 8px 16px;
                        background: white;
                        border: 1px solid #e5e7eb;
                        border-radius: 20px;
                        cursor: pointer;
                        transition: all 0.2s;
                    }
                    .suggestion-btn:hover {
                        background: #f3f4f6;
                        border-color: #3b82f6;
                    }
                    .messages-list {
                        display: flex;
                        flex-direction: column;
                        gap: 16px;
                    }
                    .message {
                        display: flex;
                        gap: 12px;
                        animation: fadeIn 0.3s ease;
                    }
                    @keyframes fadeIn {
                        from { opacity: 0; transform: translateY(10px); }
                        to { opacity: 1; transform: translateY(0); }
                    }
                    .user-message { justify-content: flex-end; }
                    .assistant-message { justify-content: flex-start; }
                    .message-avatar {
                        width: 36px;
                        height: 36px;
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 18px;
                        flex-shrink: 0;
                    }
                    .user-message .message-avatar {
                        background: #3b82f6;
                        order: 1;
                    }
                    .assistant-message .message-avatar {
                        background: #10b981;
                    }
                    .message-content {
                        max-width: 70%;
                    }
                    .user-message .message-content {
                        order: 0;
                    }
                    .message-badge {
                        font-size: 11px;
                        padding: 4px 8px;
                        background: #f3f4f6;
                        border-radius: 6px;
                        margin-bottom: 6px;
                        display: inline-block;
                    }
                    .message-text {
                        padding: 10px 14px;
                        border-radius: 12px;
                        line-height: 1.4;
                        white-space: pre-wrap;
                        word-wrap: break-word;
                    }
                    .user-message .message-text {
                        background: #3b82f6;
                        color: white;
                    }
                    .assistant-message .message-text {
                        background: white;
                        color: #1f2937;
                        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                    }
                    .message-time {
                        font-size: 10px;
                        color: #9ca3af;
                        margin-top: 4px;
                        padding-left: 8px;
                    }
                    .typing-indicator {
                        display: flex;
                        gap: 4px;
                        padding: 12px 16px;
                        background: white;
                        border-radius: 12px;
                    }
                    .typing-indicator span {
                        width: 8px;
                        height: 8px;
                        background: #9ca3af;
                        border-radius: 50%;
                        animation: bounce 1.4s infinite;
                    }
                    .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
                    .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
                    @keyframes bounce {
                        0%, 60%, 100% { transform: translateY(0); }
                        30% { transform: translateY(-10px); }
                    }
                    .input-area {
                        padding: 16px 20px;
                        background: white;
                        border-top: 1px solid #e5e7eb;
                    }
                    .input-wrapper {
                        display: flex;
                        gap: 10px;
                        align-items: flex-end;
                    }
                    .message-input {
                        flex: 1;
                        padding: 10px 14px;
                        border: 1px solid #e5e7eb;
                        border-radius: 12px;
                        resize: none;
                        font-family: inherit;
                        font-size: 14px;
                        max-height: 100px;
                    }
                    .message-input:focus {
                        outline: none;
                        border-color: #3b82f6;
                    }
                    .extract-btn, .send-btn {
                        width: 44px;
                        height: 44px;
                        border: none;
                        border-radius: 12px;
                        cursor: pointer;
                        font-size: 18px;
                        transition: all 0.2s;
                    }
                    .extract-btn {
                        background: #8b5cf6;
                        color: white;
                    }
                    .extract-btn:hover:not(:disabled) {
                        background: #7c3aed;
                    }
                    .send-btn {
                        background: #3b82f6;
                        color: white;
                    }
                    .send-btn:hover:not(:disabled) {
                        background: #2563eb;
                    }
                    .extract-btn:disabled, .send-btn:disabled {
                        opacity: 0.5;
                        cursor: not-allowed;
                    }
                    @keyframes slideIn {
                        from { transform: translateX(100%); opacity: 0; }
                        to { transform: translateX(0); opacity: 1; }
                    }
                `}</style>
            </div>
        </>
    );
};

export default ChatInterface;

// frontend/src/components/ChatInterface.js

/*
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

*/