// frontend/src/components/Login.js
import React, { useState } from 'react';
import './Login.css';
import apiClient from '../services/api';

const Login = ({ setToken }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    username: '',
    full_name: ''
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    // Limpar mensagens ao digitar
    setError('');
    setSuccess('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setIsLoading(true);

    try {
      if (isLogin) {
        // Login usando o apiClient
        const data = await apiClient.login(formData.email, formData.password);
        setToken(data.access_token);
      } else {
        // Registro usando o apiClient
        await apiClient.register({
          email: formData.email,
          password: formData.password,
          name: formData.full_name || formData.username,
          username: formData.username
        });
        setSuccess('Registro realizado com sucesso! Faça login.');
        setIsLogin(true);
        // Limpar formulário
        setFormData({
          email: '',
          password: '',
          username: '',
          full_name: ''
        });
      }
    } catch (error) {
      console.error('Erro:', error);
      const mensagem = error.response?.data?.detail || 'Erro de conexão com o servidor';
      setError(mensagem);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <div className="logo">
            <span className="logo-icon">🌿</span>
            <span>Vireo</span>
          </div>
          <h2>{isLogin ? 'Bem-vindo de volta' : 'Criar conta'}</h2>
          <p>{isLogin ? 'Faça login para continuar' : 'Comece sua jornada de saúde'}</p>
        </div>

        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          {!isLogin && (
            <>
              <div className="form-group">
                <label>Nome completo</label>
                <div className="input-icon">
                  <span className="icon">👤</span>
                  <input
                    type="text"
                    name="full_name"
                    placeholder="Digite seu nome completo"
                    value={formData.full_name}
                    onChange={handleChange}
                    required
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Nome de usuário</label>
                <div className="input-icon">
                  <span className="icon">@</span>
                  <input
                    type="text"
                    name="username"
                    placeholder="Escolha um nome de usuário"
                    value={formData.username}
                    onChange={handleChange}
                    required
                  />
                </div>
              </div>
            </>
          )}

          <div className="form-group">
            <label>Email</label>
            <div className="input-icon">
              <span className="icon">📧</span>
              <input
                type="email"
                name="email"
                placeholder="seu@email.com"
                value={formData.email}
                onChange={handleChange}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label>Senha</label>
            <div className="input-icon">
              <span className="icon">🔒</span>
              <input
                type="password"
                name="password"
                placeholder="••••••••"
                value={formData.password}
                onChange={handleChange}
                required
              />
            </div>
          </div>

          <button 
            type="submit" 
            className="login-btn"
            disabled={isLoading}
          >
            {isLoading ? (
              <span className="btn-content">
                <span className="spinner-small"></span>
                {isLogin ? 'Entrando...' : 'Registrando...'}
              </span>
            ) : (
              isLogin ? 'Entrar' : 'Registrar'
            )}
          </button>

          <div className="toggle-auth">
            <button 
              type="button" 
              onClick={() => {
                setIsLogin(!isLogin);
                setError('');
                setSuccess('');
              }}
              className="toggle-btn"
            >
              {isLogin ? 'Criar nova conta' : 'Já tenho uma conta'}
            </button>
          </div>
        </form>
      </div>

      <style jsx>{`
        .login-container {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
          padding: 20px;
          position: relative;
          overflow: hidden;
        }

        /* Elementos decorativos */
        .login-container::before {
          content: "🌿";
          position: absolute;
          font-size: 300px;
          opacity: 0.05;
          bottom: -50px;
          left: -50px;
          pointer-events: none;
        }

        .login-container::after {
          content: "💪";
          position: absolute;
          font-size: 250px;
          opacity: 0.05;
          top: -50px;
          right: -50px;
          pointer-events: none;
        }

        .login-card {
          background: white;
          border-radius: 32px;
          padding: 48px 40px;
          width: 100%;
          max-width: 460px;
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
          animation: fadeInUp 0.5s ease;
          position: relative;
          z-index: 1;
        }

        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(30px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .login-header {
          text-align: center;
          margin-bottom: 32px;
        }

        .logo {
          font-size: 36px;
          font-weight: bold;
          background: linear-gradient(135deg, #059669, #10b981);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          margin-bottom: 16px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }

        .logo-icon {
          font-size: 40px;
          background: none;
          -webkit-text-fill-color: initial;
        }

        .login-header h2 {
          font-size: 28px;
          color: #1f2937;
          margin-bottom: 8px;
          font-weight: 700;
        }

        .login-header p {
          color: #6b7280;
          font-size: 14px;
        }

        .alert {
          padding: 12px 16px;
          border-radius: 12px;
          font-size: 14px;
          margin-bottom: 24px;
          animation: slideIn 0.3s ease;
        }

        .alert-error {
          background: #fee2e2;
          color: #dc2626;
          border-left: 4px solid #dc2626;
        }

        .alert-success {
          background: #d1fae5;
          color: #059669;
          border-left: 4px solid #059669;
        }

        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(-20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }

        .login-form {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .form-group {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .form-group label {
          font-size: 14px;
          font-weight: 500;
          color: #374151;
        }

        .input-icon {
          position: relative;
          display: flex;
          align-items: center;
        }

        .input-icon .icon {
          position: absolute;
          left: 14px;
          font-size: 18px;
          color: #9ca3af;
        }

        .input-icon input {
          width: 100%;
          padding: 14px 16px 14px 44px;
          border: 2px solid #e5e7eb;
          border-radius: 16px;
          font-size: 15px;
          transition: all 0.2s;
          background: white;
        }

        .input-icon input:focus {
          outline: none;
          border-color: #10b981;
          box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
        }

        .input-icon input:hover {
          border-color: #d1fae5;
        }

        .login-btn {
          background: linear-gradient(135deg, #059669, #10b981);
          color: white;
          border: none;
          padding: 14px;
          border-radius: 16px;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
          margin-top: 8px;
        }

        .login-btn:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 8px 20px rgba(5, 150, 105, 0.3);
        }

        .login-btn:active:not(:disabled) {
          transform: translateY(0);
        }

        .login-btn:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }

        .btn-content {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }

        .spinner-small {
          width: 18px;
          height: 18px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top-color: white;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }

        .toggle-auth {
          text-align: center;
          margin-top: 8px;
        }

        .toggle-btn {
          background: none;
          border: none;
          color: #059669;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          transition: all 0.2s;
        }

        .toggle-btn:hover {
          color: #047857;
          text-decoration: underline;
        }

        /* Responsividade */
        @media (max-width: 480px) {
          .login-card {
            padding: 32px 24px;
          }

          .login-header h2 {
            font-size: 24px;
          }

          .logo {
            font-size: 28px;
          }

          .logo-icon {
            font-size: 32px;
          }
        }
      `}</style>
    </div>
  );
};

export default Login;