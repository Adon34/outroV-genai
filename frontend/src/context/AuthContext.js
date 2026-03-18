// frontend/src/context/AuthContext.js
import React, { createContext, useState, useContext, useEffect } from 'react';
import api from '../services/api';

const AuthContext = createContext();

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadUser();
    }, []);

    const loadUser = async () => {
        const token = localStorage.getItem('token');
        if (token) {
            try {
                const userData = await api.getCurrentUser();
                setUser(userData);
            } catch (error) {
                console.error('Error loading user:', error);
                localStorage.clear();
            }
        }
        setLoading(false);
    };

    const login = async (email, password) => {
        try {
            setError(null);
            const data = await api.login(email, password);
            const userData = await api.getCurrentUser();
            setUser(userData);
            return { success: true };
        } catch (error) {
            setError(error.response?.data?.detail || 'Login failed');
            return { success: false, error: error.response?.data?.detail };
        }
    };

    const register = async (userData) => {
        try {
            setError(null);
            await api.register(userData);
            return { success: true };
        } catch (error) {
            setError(error.response?.data?.detail || 'Registration failed');
            return { success: false, error: error.response?.data?.detail };
        }
    };

    const logout = async () => {
        await api.logout();
        setUser(null);
    };

    const updateUser = (userData) => {
        setUser(userData);
    };

    const value = {
        user,
        loading,
        error,
        login,
        register,
        logout,
        updateUser
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};