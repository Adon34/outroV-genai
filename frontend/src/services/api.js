// frontend/src/services/api.js
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost/api';

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
            (error) => {
                return Promise.reject(error);
            }
        );

        // Response interceptor
        this.client.interceptors.response.use(
            (response) => response,
            async (error) => {
                const originalRequest = error.config;

                // Handle token refresh
                if (error.response?.status === 401 && !originalRequest._retry) {
                    originalRequest._retry = true;
                    
                    try {
                        const refreshToken = localStorage.getItem('refreshToken');
                        const response = await this.client.post('/auth/refresh', {
                            refresh_token: refreshToken
                        });
                        
                        localStorage.setItem('token', response.data.access_token);
                        originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`;
                        
                        return this.client(originalRequest);
                    } catch (refreshError) {
                        // Redirect to login
                        localStorage.clear();
                        window.location.href = '/login';
                        return Promise.reject(refreshError);
                    }
                }

                return Promise.reject(error);
            }
        );
    }

    // Auth endpoints
    async login(email, password) {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const response = await this.client.post('/auth/token', formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
        });
        
        if (response.data.access_token) {
            localStorage.setItem('token', response.data.access_token);
            localStorage.setItem('refreshToken', response.data.refresh_token);
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
        const response = await this.client.get('/auth/me');
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

    async getConversation(conversationId) {
        const response = await this.client.get(`/chat/conversations/${conversationId}`);
        return response.data;
    }

    async deleteConversation(conversationId) {
        const response = await this.client.delete(`/chat/conversations/${conversationId}`);
        return response.data;
    }

    // User endpoints
    async updateProfile(userData) {
        const response = await this.client.put('/users/profile', userData);
        return response.data;
    }

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
}

export default new ApiClient();