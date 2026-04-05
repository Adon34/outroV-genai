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