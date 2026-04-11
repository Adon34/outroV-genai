// frontend/src/hooks/useAgentChat.js
import { useState, useEffect, useCallback } from 'react';
import api, { onWorkoutCreated, onProfileUpdated, onMealAdded } from '../services/api';

export const useAgentChat = (conversationId = null) => {
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [currentConversationId, setCurrentConversationId] = useState(conversationId);
    const [lastAction, setLastAction] = useState(null);

    // Escuta ações dos agentes
    useEffect(() => {
        const unsubscribeWorkout = onWorkoutCreated((workoutData) => {
            setLastAction({
                type: 'workout_created',
                data: workoutData,
                timestamp: new Date()
            });
        });

        const unsubscribeProfile = onProfileUpdated((profileData) => {
            setLastAction({
                type: 'profile_updated',
                data: profileData,
                timestamp: new Date()
            });
        });

        const unsubscribeMeal = onMealAdded((mealData) => {
            setLastAction({
                type: 'meal_added',
                data: mealData,
                timestamp: new Date()
            });
        });

        return () => {
            unsubscribeWorkout();
            unsubscribeProfile();
            unsubscribeMeal();
        };
    }, []);

    const sendMessage = useCallback(async (message, autoCreate = true) => {
        setIsLoading(true);
        try {
            // Adiciona mensagem do usuário localmente
            const userMessage = {
                role: 'user',
                content: message,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, userMessage]);

            // Envia para API
            const response = await api.sendMessage(message, currentConversationId, autoCreate);
            
            // Atualiza conversationId se for nova
            if (!currentConversationId && response.conversation_id) {
                setCurrentConversationId(response.conversation_id);
            }

            // Adiciona resposta do assistente
            const assistantMessage = {
                role: 'assistant',
                content: response.answer,
                action: response.action,
                actionData: response.action_data,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, assistantMessage]);

            return response;
        } catch (error) {
            console.error('Erro ao enviar mensagem:', error);
            // Adiciona mensagem de erro
            const errorMessage = {
                role: 'assistant',
                content: 'Desculpe, ocorreu um erro. Tente novamente.',
                isError: true,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, errorMessage]);
            throw error;
        } finally {
            setIsLoading(false);
        }
    }, [currentConversationId]);

    const clearMessages = useCallback(() => {
        setMessages([]);
        setLastAction(null);
    }, []);

    return {
        messages,
        isLoading,
        currentConversationId,
        lastAction,
        sendMessage,
        clearMessages
    };
};