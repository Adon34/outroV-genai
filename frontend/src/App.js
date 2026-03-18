// frontend/src/App.js
import React, { useState, useEffect } from 'react';
import ChatInterface from './components/ChatInterface';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import './App.css';

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null);

  useEffect(() => {
    if (token) {
      fetchUser();
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const response = await fetch('http://localhost:8000/users/me', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      setUser(data);
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

  if (!token) {
    return <Login setToken={setToken} />;
  }

  return (
    <div className="App">
      <nav className="navbar">
        <h1>Diet & Training Assistant</h1>
        <div className="user-info">
          <span>Olá, {user?.full_name || user?.username}</span>
          <button onClick={logout}>Sair</button>
        </div>
      </nav>
      
      <div className="main-container">
        <Dashboard user={user} token={token} />
        <ChatInterface token={token} userId={user?.id} />
      </div>
    </div>
  );
}

export default App;