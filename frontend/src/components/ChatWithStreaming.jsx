// src/components/Chat/ChatWithStreaming.jsx
import React, { useState, useRef, useEffect } from 'react';
import api, { onAgentAction } from '../../services/api';

const ChatWithStreaming = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isStreaming, setIsStreaming] = useState(false);
    const [conversationId, setConversationId] = useState(null);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        // Escutar ações do agente
        const unsubscribe = onAgentAction((action) => {
            console.log('Ação do agente:', action);
            // Atualizar dashboard ou mostrar notificação
            if (action.action === 'workout_created') {
                // Mostrar notificação de treino criado
                showNotification('Treino criado com sucesso!');
            }
        });

        return () => unsubscribe();
    }, []);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSendMessage = async () => {
        if (!input.trim() || isStreaming) return;

        const userMessage = {
            id: Date.now(),
            role: 'user',
            content: input,
            timestamp: new Date()
        };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsStreaming(true);

        // Criar mensagem temporária do assistente
        const tempId = Date.now() + 1;
        setMessages(prev => [...prev, {
            id: tempId,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            isStreaming: true
        }]);

        let fullResponse = '';

        await api.sendMessageStream(
            input,
            conversationId,
            true,
            {
                onChunk: (chunk) => {
                    fullResponse += chunk;
                    setMessages(prev => prev.map(msg =>
                        msg.id === tempId
                            ? { ...msg, content: fullResponse }
                            : msg
                    ));
                },
                onAction: (action) => {
                    console.log('Ação recebida:', action);
                    if (action.conversation_id) {
                        setConversationId(action.conversation_id);
                    }
                },
                onComplete: () => {
                    setMessages(prev => prev.map(msg =>
                        msg.id === tempId
                            ? { ...msg, isStreaming: false }
                            : msg
                    ));
                    setIsStreaming(false);
                },
                onError: (error) => {
                    console.error('Stream error:', error);
                    setMessages(prev => prev.map(msg =>
                        msg.id === tempId
                            ? { ...msg, content: 'Erro ao processar mensagem. Tente novamente.', isStreaming: false }
                            : msg
                    ));
                    setIsStreaming(false);
                }
            }
        );
    };

    return (
        <div className="flex flex-col h-screen">
            {/* Header */}
            <div className="bg-white shadow p-4">
                <h1 className="text-xl font-bold">Assistente de Saúde</h1>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((msg) => (
                    <div
                        key={msg.id}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        <div
                            className={`max-w-[70%] rounded-lg p-3 ${
                                msg.role === 'user'
                                    ? 'bg-blue-500 text-white'
                                    : 'bg-gray-200 text-gray-800'
                            }`}
                        >
                            <p className="whitespace-pre-wrap">{msg.content}</p>
                            {msg.isStreaming && (
                                <span className="inline-block w-2 h-4 ml-1 bg-gray-500 animate-pulse">|</span>
                            )}
                            <span className="text-xs opacity-70 mt-1 block">
                                {msg.timestamp.toLocaleTimeString()}
                            </span>
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="border-t p-4 bg-white">
                <div className="flex gap-2 max-w-4xl mx-auto">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                        placeholder="Digite sua mensagem..."
                        className="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        disabled={isStreaming}
                    />
                    <button
                        onClick={handleSendMessage}
                        disabled={isStreaming || !input.trim()}
                        className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50"
                    >
                        {isStreaming ? 'Enviando...' : 'Enviar'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ChatWithStreaming;