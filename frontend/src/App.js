// frontend/src/App.js
import React, { useState, useEffect } from 'react';
import ChatInterface from './components/ChatInterface';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import apiClient from './services/api';
import './App.css';

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard' or 'chat'

  useEffect(() => {
    if (token) {
      fetchUser();
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const userData = await apiClient.getCurrentUser();
      setUser(userData);
    } catch (error) {
      console.error('Error fetching user:', error);
      logout();
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  const handleWorkoutCreated = (workoutData) => {
    // Atualizar dashboard quando treino for criado
    console.log('Workout created:', workoutData);
  };

  const handleProfileUpdated = (profileData) => {
    // Atualizar perfil do usuário
    fetchUser();
  };

  if (!token) {
    return <Login setToken={setToken} />;
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="logo-section">
            <h1>
              <span className="logo-icon">🌿</span> 
              Vireo
            </h1>
            <p className="tagline">Assistente de dieta e treino personalizado</p>
          </div>
          <div className="header-actions">
            <div className="user-info">
              <span className="user-avatar">👤</span>
              <span className="user-name">{user?.full_name || user?.username || 'Usuário'}</span>
            </div>
            <button onClick={logout} className="logout-btn" title="Sair">
              🚪 Sair
            </button>
          </div>
        </div>
      </header>

      {/* Navegação */}
      <nav className="main-nav">
        <button 
          className={`nav-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          📊 Dashboard
        </button>
        <button 
          className={`nav-btn ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          💬 Chat IA
        </button>
      </nav>

      {/* Conteúdo Principal */}
      <main className="app-main">
        {activeTab === 'dashboard' ? (
          <Dashboard 
            user={user} 
            token={token} 
            onUserUpdate={fetchUser}
            onWorkoutCreated={handleWorkoutCreated}
            onProfileUpdated={handleProfileUpdated}
          />
        ) : (
          <div className="chat-container">
            <ChatInterface 
              token={token} 
              userId={user?.id}
              onWorkoutCreated={handleWorkoutCreated}
              onProfileUpdated={handleProfileUpdated}
            />
          </div>
        )}
      </main>

      <style jsx>{`
        .app {
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          background: #ecfdf5;
        }

        /* Header */
        .app-header {
          background: linear-gradient(135deg, #059669 0%, #047857 100%);
          color: white;
          padding: 20px 32px;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .header-content {
          max-width: 1400px;
          margin: 0 auto;
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 16px;
        }

        .logo-section h1 {
          font-size: 28px;
          font-weight: 700;
          margin: 0;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .logo-icon {
          font-size: 32px;
        }

        .tagline {
          font-size: 14px;
          opacity: 0.9;
          margin-top: 4px;
        }

        .header-actions {
          display: flex;
          align-items: center;
          gap: 16px;
        }

        .user-info {
          display: flex;
          align-items: center;
          gap: 8px;
          background: rgba(255, 255, 255, 0.2);
          padding: 8px 16px;
          border-radius: 40px;
        }

        .user-avatar {
          font-size: 18px;
        }

        .user-name {
          font-weight: 500;
        }

        .logout-btn {
          background: rgba(255, 255, 255, 0.2);
          border: none;
          color: white;
          padding: 8px 16px;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s;
          font-size: 14px;
        }

        .logout-btn:hover {
          background: rgba(255, 255, 255, 0.3);
          transform: translateY(-1px);
        }

        /* Navegação */
        .main-nav {
          background: white;
          padding: 12px 32px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
          display: flex;
          gap: 12px;
        }

        .nav-btn {
          padding: 10px 24px;
          border: none;
          background: #f3f4f6;
          color: #4b5563;
          border-radius: 40px;
          cursor: pointer;
          font-weight: 500;
          transition: all 0.2s;
        }

        .nav-btn:hover {
          background: #d1fae5;
          color: #059669;
        }

        .nav-btn.active {
          background: linear-gradient(135deg, #059669, #10b981);
          color: white;
          box-shadow: 0 2px 8px rgba(5, 150, 105, 0.3);
        }

        /* Conteúdo Principal */
        .app-main {
          flex: 1;
          max-width: 1400px;
          margin: 0 auto;
          padding: 24px;
          width: 100%;
        }

        .chat-container {
          height: calc(100vh - 200px);
          min-height: 500px;
        }

        @media (max-width: 768px) {
          .app-header {
            padding: 16px 20px;
          }
          .logo-section h1 {
            font-size: 22px;
          }
          .tagline {
            font-size: 12px;
          }
          .main-nav {
            padding: 10px 16px;
          }
          .nav-btn {
            padding: 8px 16px;
            font-size: 14px;
          }
          .app-main {
            padding: 16px;
          }
          .chat-container {
            height: calc(100vh - 180px);
          }
        }
      `}</style>
    </div>
  );
}

export default App;