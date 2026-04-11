// frontend/src/services/api.js
import axios from 'axios';

const API_URL = '/api';

class ApiClient {
    constructor() {
        this.client = axios.create({
            baseURL: API_URL,
            timeout: 30000,
            headers: {
                'Content-Type': 'application/json',
            }
        });

        // Request interceptor
        this.client.interceptors.request.use(
            (config) => {
                const token = localStorage.getItem('token');
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );

        // Response interceptor
        this.client.interceptors.response.use(
            (response) => {
                // Dispara evento global para ações dos agentes
                if (response.data?.action && response.data.action !== 'chat') {
                    const event = new CustomEvent('agent-action', { 
                        detail: {
                            action: response.data.action,
                            actionData: response.data.action_data,
                            conversationId: response.data.conversation_id,
                            timestamp: new Date().toISOString(),
                            confidence: response.data.confidence || 0.8
                        }
                    });
                    window.dispatchEvent(event);
                }
                return response;
            },
            async (error) => {
                const originalRequest = error.config;
                
                // Evita loop infinito
                if (error.response?.status === 401 && !originalRequest._retry) {
                    originalRequest._retry = true;
                    
                    if (originalRequest.url?.includes('/auth/refresh')) {
                        localStorage.clear();
                        window.location.href = '/login';
                        return Promise.reject(error);
                    }
                    
                    try {
                        const refreshToken = localStorage.getItem('refreshToken');
                        if (!refreshToken) {
                            window.location.href = '/login';
                            return Promise.reject(error);
                        }
                        
                        const response = await this.client.post('/auth/refresh', {
                            refresh_token: refreshToken
                        });
                        
                        localStorage.setItem('token', response.data.access_token);
                        originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`;
                        return this.client(originalRequest);
                    } catch (refreshError) {
                        localStorage.clear();
                        window.location.href = '/login';
                        return Promise.reject(refreshError);
                    }
                }
                
                return Promise.reject(error);
            }
        );
    }

    // ============================================
    // MÉTODOS BASE
    // ============================================

    async get(url, config = {}) {
        const response = await this.client.get(url, config);
        return response.data;
    }

    async post(url, data, config = {}) {
        const response = await this.client.post(url, data, config);
        return response.data;
    }

    async put(url, data, config = {}) {
        const response = await this.client.put(url, data, config);
        return response.data;
    }

    async delete(url, config = {}) {
        const response = await this.client.delete(url, config);
        return response.data;
    }

    // ============================================
    // AUTENTICAÇÃO
    // ============================================

    async login(email, password) {
        const response = await this.client.post('/auth/login', {
            email: email,
            password: password
        });
        
        if (response.data.access_token) {
            localStorage.setItem('token', response.data.access_token);
            if (response.data.refresh_token) {
                localStorage.setItem('refreshToken', response.data.refresh_token);
            }
        }
        
        return response.data;
    }

    async register(userData) {
        const response = await this.client.post('/auth/register', userData);
        return response.data;
    }

    async logout() {
        try {
            await this.client.post('/auth/logout');
        } finally {
            localStorage.clear();
            window.dispatchEvent(new CustomEvent('user-logout'));
        }
    }

    async getCurrentUser() {
        const response = await this.client.get('/users/me');
        return response.data;
    }

    // ============================================
    // USER PROFILE
    // ============================================

    async getProfile() {
        const response = await this.client.get('/users/profile');
        return response.data;
    }

    async updateProfile(profileData) {
        const response = await this.client.put('/users/profile', profileData);
        window.dispatchEvent(new CustomEvent('profile-updated', { 
            detail: profileData 
        }));
        return response.data;
    }

    async updateBodyFat(bodyFatPercentage) {
        return this.updateProfile({ body_fat: bodyFatPercentage });
    }

    async updateWeight(weightKg) {
        return this.updateProfile({ weight: weightKg });
    }

    // ============================================
    // PROGRESS
    // ============================================

    async getProgress() {
        const response = await this.client.get('/users/progress');
        return response.data;
    }

    async getProgressHistory(days = 30) {
        const response = await this.client.get('/users/progress/history', {
            params: { days }
        });
        return response.data;
    }

    // ============================================
    // MEALS (REFEIÇÕES)
    // ============================================

    async getTodayMeals() {
        const response = await this.client.get('/meals/today');
        return response.data;
    }

    async addMeal(mealData) {
        const response = await this.client.post('/meals/', mealData);
        window.dispatchEvent(new CustomEvent('meal-added', { 
            detail: response.data 
        }));
        return response.data;
    }

    async getMealDetails(mealId) {
        const response = await this.client.get(`/meals/${mealId}`);
        return response.data;
    }

    async getMeals(filters = {}) {
        const params = new URLSearchParams();
        if (filters.date_from) params.append('date_from', filters.date_from);
        if (filters.date_to) params.append('date_to', filters.date_to);
        if (filters.meal_type) params.append('meal_type', filters.meal_type);
        if (filters.skip) params.append('skip', filters.skip);
        if (filters.limit) params.append('limit', filters.limit);
        
        const response = await this.client.get(`/meals/?${params.toString()}`);
        return response.data;
    }

    async updateMeal(mealId, mealData) {
        const response = await this.client.put(`/meals/${mealId}`, mealData);
        return response.data;
    }

    async deleteMeal(mealId) {
        const response = await this.client.delete(`/meals/${mealId}`);
        return response.data;
    }

    async getMealHistory(page = 1, limit = 20) {
        return this.getMeals({ skip: (page - 1) * limit, limit });
    }

    async getMealStats(targetDate = null) {
        const params = targetDate ? `?target_date=${targetDate}` : '';
        const response = await this.client.get(`/meals/stats/daily${params}`);
        return response.data;
    }

    // ============================================
    // WORKOUTS (TREINOS)
    // ============================================

    async getTodayWorkouts() {
        const response = await this.client.get('/workouts/today');
        return response.data;
    }

    async addWorkout(workoutData) {
        const response = await this.client.post('/workouts/', workoutData);
        window.dispatchEvent(new CustomEvent('workout-added', { 
            detail: response.data 
        }));
        return response.data;
    }

    async getWorkoutDetails(workoutId) {
        const response = await this.client.get(`/workouts/${workoutId}`);
        return response.data;
    }

    async getWorkouts(filters = {}) {
        const params = new URLSearchParams();
        if (filters.date_from) params.append('date_from', filters.date_from);
        if (filters.date_to) params.append('date_to', filters.date_to);
        if (filters.skip) params.append('skip', filters.skip);
        if (filters.limit) params.append('limit', filters.limit);
        
        const response = await this.client.get(`/workouts/?${params.toString()}`);
        return response.data;
    }

    async updateWorkout(workoutId, workoutData) {
        const response = await this.client.put(`/workouts/${workoutId}`, workoutData);
        return response.data;
    }

    async deleteWorkout(workoutId) {
        const response = await this.client.delete(`/workouts/${workoutId}`);
        return response.data;
    }

    async completeWorkout(workoutId) {
        const response = await this.client.post(`/workouts/${workoutId}/complete`);
        window.dispatchEvent(new CustomEvent('workout-completed', { 
            detail: { workoutId }
        }));
        return response.data;
    }

    async getWorkoutHistory(page = 1, limit = 20) {
        return this.getWorkouts({ skip: (page - 1) * limit, limit });
    }

    async getWorkoutStats(targetDate = null) {
        const params = targetDate ? `?target_date=${targetDate}` : '';
        const response = await this.client.get(`/workouts/stats/daily${params}`);
        return response.data;
    }

    async getWeeklyWorkouts() {
        const response = await this.client.get('/workouts/weekly');
        return response.data;
    }

    // ============================================
    // CHAT (COM SUPORTE A AGENTES E STREAMING)
    // ============================================




    async sendMessage(message, conversationId = null, autoCreate = true) {
        const response = await this.client.post('/chat/send', {
            message,
            conversation_id: conversationId,
            auto_create: autoCreate
        });
        return response.data;
    }

    // Streaming com suporte a agentes
    async sendMessageStream(message, conversationId = null, autoCreate = true, callbacks = {}) {
        const {
            onChunk = () => {},
            onAction = () => {},
            onComplete = () => {},
            onError = () => {}
        } = callbacks;

        try {
            const response = await fetch(`${API_URL}/chat/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({
                    message,
                    conversation_id: conversationId,
                    auto_create: autoCreate,
                    user_id: 1 // Será substituído pelo backend pelo token
                })
            });

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            if (!reader) {
                throw new Error('No reader available');
            }

            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            if (data.type === 'end') {
                                onComplete();
                            } else if (data.type === 'error') {
                                onError(data.error);
                            } else if (data.action) {
                                // Evento de ação do agente
                                onAction(data);
                                // Disparar evento global
                                window.dispatchEvent(new CustomEvent('agent-action', {
                                    detail: {
                                        action: data.action,
                                        actionData: data.action_data,
                                        timestamp: new Date().toISOString()
                                    }
                                }));
                            } else if (data.partial_response) {
                                onChunk(data.partial_response);
                            }
                        } catch (e) {
                            // Se não for JSON, é texto puro
                            if (line.startsWith('data: ')) {
                                onChunk(line.slice(6));
                            }
                        }
                    }
                }
            }
        } catch (error) {
            onError(error.message);
        }
    }


    async getConversations(skip = 0, limit = 20) {
        try {
            // Remover os parâmetros da URL
            const response = await this.client.get('/chat/conversations');
            // Garantir que retorna array
            return { conversations: response.data || [] };
        } catch (error) {
            console.error('Error fetching conversations:', error);
            return { conversations: [] };
        }
    }

    async getRecentActions(limit = 10) {
        try {
            // Remover os parâmetros da URL
            const response = await this.client.get('/chat/actions/recent');
            // Garantir que retorna array
            return { actions: response.data || [] };
        } catch (error) {
            console.error('Error fetching recent actions:', error);
            return { actions: [] };
        }
    }

    // Excluir uma conversa
    async deleteConversation(conversationId) {
        const response = await this.client.delete(`/chat/conversations/${conversationId}`);
        return response.data;
    }

    // Ações recentes do agente
    async getRecentActions(limit = 10) {
        try {
            // Usar params corretamente
            const response = await this.client.get('/chat/actions/recent', {
                params: { limit: parseInt(limit) }  // ← garantir que é número
            });
            return response.data;
        } catch (error) {
            console.error('Error fetching recent actions:', error);
            return { actions: [] };
        }
    }

    async extractProfileFromMessage(message) {
        const response = await this.client.post('/chat/extract-profile', { message });
        return response.data;
    }

    async getConversationState(threadId) {
        const response = await this.client.get(`/chat/conversation/${threadId}`);
        return response.data;
    }

    async resetConversation(threadId) {
        const response = await this.client.delete(`/chat/conversation/${threadId}`);
        return response.data;
    }

    // ============================================
    // WEB SOCKET (CHAT EM TEMPO REAL)
    // ============================================

    createWebSocketConnection(conversationId, token) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(
            `${protocol}//${window.location.host}/api/chat/ws/${conversationId}?token=${token}`
        );
        
        ws.onopen = () => {
            console.log('WebSocket connected');
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        return ws;
    }

    // WebSocket com streaming
    createWebSocketStream(conversationId, token, onMessage, onAction) {
        const ws = this.createWebSocketConnection(conversationId, token);
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'token') {
                onMessage?.(data.content);
            } else if (data.type === 'action') {
                onAction?.(data.action, data.actionData);
            } else if (data.answer) {
                onMessage?.(data.answer);
            }
            
            // Disparar evento global para ações
            if (data.action && data.action !== 'chat') {
                window.dispatchEvent(new CustomEvent('agent-action', {
                    detail: {
                        action: data.action,
                        actionData: data.action_data,
                        timestamp: new Date().toISOString()
                    }
                }));
            }
        };
        
        return ws;
    }

    // ============================================
    // HEALTH & METRICS
    // ============================================

    async getHealth() {
        const response = await this.client.get('/health');
        return response.data;
    }

    async getHealthLive() {
        const response = await this.client.get('/health/live');
        return response.data;
    }

    async getHealthReady() {
        const response = await this.client.get('/health/ready');
        return response.data;
    }

    async getDetailedHealth() {
        const response = await this.client.get('/health/detailed');
        return response.data;
    }

    async getMetrics() {
        const response = await this.client.get('/metrics');
        return response.data;
    }

    // ============================================
    // DASHBOARD - DADOS AGREGADOS
    // ============================================

    async getDashboardData() {
        const [todayMeals, todayWorkouts, recentActions, profile, dailyStats] = await Promise.all([
            this.getTodayMeals(),
            this.getTodayWorkouts(),
            this.getRecentActions(5),
            this.getProfile(),
            this.getMealStats()
        ]);

        const totalCalories = todayMeals.reduce((sum, meal) => sum + (meal.calories || 0), 0);
        const totalWorkoutDuration = todayWorkouts.reduce((sum, w) => sum + (w.duration || 0), 0);
        const totalCaloriesBurned = todayWorkouts.reduce((sum, w) => sum + (w.calories_burned || 0), 0);

        return {
            profile,
            today: {
                meals: todayMeals,
                workouts: todayWorkouts,
                totalCalories,
                totalCaloriesBurned,
                totalWorkoutDuration,
                caloriesBalance: totalCalories - totalCaloriesBurned,
                mealsCount: todayMeals.length,
                workoutsCount: todayWorkouts.length
            },
            recentActions: recentActions.actions || [],
            dailyStats
        };
    }
}

// ============================================
// EVENT LISTENERS HELPERS
// ============================================

// Event listener helper para ações dos agentes
export const onAgentAction = (callback) => {
    const handler = (event) => callback(event.detail);
    window.addEventListener('agent-action', handler);
    return () => window.removeEventListener('agent-action', handler);
};

// Helper para ações específicas
export const onWorkoutCreated = (callback) => {
    const handler = (event) => {
        if (event.detail.action === 'workout_created') {
            callback(event.detail.actionData);
        }
    };
    window.addEventListener('agent-action', handler);
    return () => window.removeEventListener('agent-action', handler);
};

export const onProfileUpdated = (callback) => {
    const handler = (event) => {
        if (event.detail.action === 'profile_updated') {
            callback(event.detail.actionData);
        }
    };
    window.addEventListener('agent-action', handler);
    return () => window.removeEventListener('agent-action', handler);
};

export const onMealAdded = (callback) => {
    const handler = (event) => {
        if (event.detail.action === 'meal_added') {
            callback(event.detail.actionData);
        }
    };
    window.addEventListener('agent-action', handler);
    return () => window.removeEventListener('agent-action', handler);
};

export const onChatResponse = (callback) => {
    const handler = (event) => {
        if (event.detail.action === 'chat') {
            callback(event.detail);
        }
    };
    window.addEventListener('agent-action', handler);
    return () => window.removeEventListener('agent-action', handler);
};

export default new ApiClient();

/*
import axios from 'axios';

const API_URL = '/api';

class ApiClient {
    constructor() {
        this.client = axios.create({
            baseURL: API_URL,
            timeout: 30000,
            headers: {
                'Content-Type': 'application/json',
            }
        });

        // Request interceptor
        this.client.interceptors.request.use(
            (config) => {
                const token = localStorage.getItem('token');
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );

        // Response interceptor
        this.client.interceptors.response.use(
            (response) => response,
            async (error) => {
                const originalRequest = error.config;
                
                // Evita loop infinito
                if (error.response?.status === 401 && !originalRequest._retry) {
                    originalRequest._retry = true;
                    
                    if (originalRequest.url?.includes('/auth/refresh')) {
                        localStorage.clear();
                        window.location.href = '/login';
                        return Promise.reject(error);
                    }
                    
                    try {
                        const refreshToken = localStorage.getItem('refreshToken');
                        if (!refreshToken) {
                            window.location.href = '/login';
                            return Promise.reject(error);
                        }
                        
                        const response = await this.client.post('/auth/refresh', {
                            refresh_token: refreshToken
                        });
                        
                        localStorage.setItem('token', response.data.access_token);
                        originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`;
                        return this.client(originalRequest);
                    } catch (refreshError) {
                        localStorage.clear();
                        window.location.href = '/login';
                        return Promise.reject(refreshError);
                    }
                }
                
                return Promise.reject(error);
            }
        );
    }

    // MÉTODO GET - Adicione se não existir
    async get(url, config = {}) {
        const response = await this.client.get(url, config);
        return response.data;
    }

    // MÉTODO POST
    async post(url, data, config = {}) {
        const response = await this.client.post(url, data, config);
        return response.data;
    }

    // MÉTODO PUT
    async put(url, data, config = {}) {
        const response = await this.client.put(url, data, config);
        return response.data;
    }

    // MÉTODO DELETE
    async delete(url, config = {}) {
        const response = await this.client.delete(url, config);
        return response.data;
    }

    // Auth endpoints
    async login(email, password) {
        const response = await this.client.post('/auth/login', {
            email: email,
            password: password
        });
        
        if (response.data.access_token) {
            localStorage.setItem('token', response.data.access_token);
        }
        
        return response.data;
    }

    async register(userData) {
        const response = await this.client.post('/auth/register', userData);
        return response.data;
    }

    async logout() {
        try {
            await this.client.post('/auth/logout');
        } finally {
            localStorage.clear();
        }
    }

    async getCurrentUser() {
        const response = await this.client.get('/users/me');
        return response.data;
    }

    // Progress endpoints
    async getProgress() {
        const response = await this.client.get('/users/progress');
        return response.data;
    }

    // Meals endpoints
    async getTodayMeals() {
        const response = await this.client.get('/meals/today');
        return response.data;
    }

    async addMeal(mealData) {
        const response = await this.client.post('/meals', mealData);
        return response.data;
    }

    // Workouts endpoints
    async getTodayWorkouts() {
        const response = await this.client.get('/workouts/today');
        return response.data;
    }

    async addWorkout(workoutData) {
        const response = await this.client.post('/workouts', workoutData);
        return response.data;
    }

    // Chat endpoints
    async sendMessage(message, conversationId = null) {
        const response = await this.client.post('/chat/send', {
            message,
            conversation_id: conversationId
        });
        return response.data;
    }

    async getConversations(page = 1, limit = 20) {
        const response = await this.client.get('/chat/conversations', {
            params: { skip: (page - 1) * limit, limit }
        });
        return response.data;
    }
}

export default new ApiClient();


*/