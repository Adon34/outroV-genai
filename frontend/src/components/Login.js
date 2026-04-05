// frontend/src/components/Login.js
import React, { useState } from 'react';
import './Login.css';
import apiClient from '../services/api';   // <-- importa o cliente

const Login = ({ setToken }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    username: '',
    full_name: ''
  });
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      if (isLogin) {
        // Login usando o apiClient
        const data = await apiClient.login(formData.email, formData.password);
        setToken(data.access_token);
      } else {
        // Registro usando o apiClient
        await apiClient.register(formData);
        setIsLogin(true);
        setError('Registro realizado com sucesso! Faça login.');
      }
    } catch (error) {
      console.error('Erro:', error);
      const mensagem = error.response?.data?.detail || 'Erro de conexão com o servidor';
      setError(mensagem);
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h2>{isLogin ? 'Login' : 'Registro'}</h2>
        
        {error && <div className="error-message">{error}</div>}
        
        <form onSubmit={handleSubmit}>
          {!isLogin && (
            <>
              <div className="form-group">
                <label>Nome Completo</label>
                <input
                  type="text"
                  name="full_name"
                  value={formData.full_name}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="form-group">
                <label>Usuário</label>
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  required
                />
              </div>
            </>
          )}
          
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
            />
          </div>
          
          <div className="form-group">
            <label>Senha</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
            />
          </div>
          
          <button type="submit">
            {isLogin ? 'Entrar' : 'Registrar'}
          </button>
        </form>
        
        <p className="toggle-form">
          {isLogin ? 'Não tem conta? ' : 'Já tem conta? '}
          <button onClick={() => setIsLogin(!isLogin)}>
            {isLogin ? 'Registre-se' : 'Faça login'}
          </button>
        </p>
      </div>
    </div>
  );
};

export default Login;