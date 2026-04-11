// frontend/src/components/Dashboard.js
import React, { useState, useEffect } from 'react';
import './Dashboard.css';
import HealthMatrix from './HealthMatrix';
import ChatInterface from './ChatInterface';
import apiClient, { 
  onAgentAction, 
  onWorkoutCreated, 
  onMealAdded, 
  onProfileUpdated 
} from '../services/api';

const Dashboard = ({ user, token, onUserUpdate }) => {
  const [progress, setProgress] = useState(null);
  const [meals, setMeals] = useState([]);
  const [workouts, setWorkouts] = useState([]);
  const [activeTab, setActiveTab] = useState('chat');
  const [currentUser, setCurrentUser] = useState(user);
  const [recentActions, setRecentActions] = useState([]);
  const [dailyStats, setDailyStats] = useState(null);
  const [weeklyWorkouts, setWeeklyWorkouts] = useState([]);
  const [mealStats, setMealStats] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [errorCount, setErrorCount] = useState({});

  // ============================================
  // INICIALIZAÇÃO E CARREGAMENTO DE DADOS
  // ============================================

  useEffect(() => {
    if (token) {
      loadAllData();
      
      // Event listeners para ações dos agentes
      const unsubscribeWorkout = onWorkoutCreated((workoutData) => {
        showNotification('Novo treino criado! 💪', 'success');
        loadWorkoutsData();
        setActiveTab('workouts');
      });

      const unsubscribeMeal = onMealAdded((mealData) => {
        showNotification('Refeição adicionada! 🍽️', 'success');
        loadMealsData();
        setActiveTab('nutrition');
      });

      const unsubscribeProfile = onProfileUpdated((profileData) => {
        showNotification('Perfil atualizado! 📊', 'info');
        loadProfileData();
        loadProgressData();
      });

      const unsubscribeGeneral = onAgentAction((action) => {
        addToRecentActions(action);
      });

      return () => {
        unsubscribeWorkout();
        unsubscribeMeal();
        unsubscribeProfile();
        unsubscribeGeneral();
      };
    }
  }, [token]);

  const loadAllData = async () => {
    setIsLoading(true);
    try {
      await Promise.allSettled([  // Usando allSettled para não parar em caso de erro
        loadProfileData(),
        loadProgressData(),
        loadMealsData(),
        loadWorkoutsData(),
        loadRecentActions(),
        loadDailyStats(),
        loadWeeklyWorkouts(),
        loadMealStats()
      ]);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadProfileData = async () => {
    try {
      const userData = await apiClient.getCurrentUser();
      setCurrentUser(userData);
      if (onUserUpdate) onUserUpdate(userData);
    } catch (error) {
      console.error('Error fetching profile:', error);
      setErrorCount(prev => ({ ...prev, profile: true }));
    }
  };

  const loadProgressData = async () => {
    try {
      const data = await apiClient.getProgress();
      setProgress(data);
    } catch (error) {
      console.error('Error fetching progress:', error);
      setProgress(null);
    }
  };

  const loadMealsData = async () => {
    try {
      const data = await apiClient.getTodayMeals();
      setMeals(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error fetching meals:', error);
      setMeals([]);
    }
  };

  const loadWorkoutsData = async () => {
    try {
      const data = await apiClient.getTodayWorkouts();
      setWorkouts(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error fetching workouts:', error);
      setWorkouts([]);
    }
  };

  const loadRecentActions = async () => {
    try {
      const data = await apiClient.getRecentActions(10);
      const actions = data?.actions || (Array.isArray(data) ? data : []);
      setRecentActions(actions);
    } catch (error) {
      console.error('Error fetching recent actions:', error);
      setRecentActions([]);
    }
  };

  const loadDailyStats = async () => {
    try {
      const stats = await apiClient.getMealStats();
      setDailyStats(stats);
    } catch (error) {
      console.error('Error fetching daily stats:', error);
      setDailyStats(null);
    }
  };

  const loadWeeklyWorkouts = async () => {
    try {
      const data = await apiClient.getWeeklyWorkouts();
      setWeeklyWorkouts(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error fetching weekly workouts:', error);
      setWeeklyWorkouts([]);
    }
  };

  const loadMealStats = async () => {
    try {
      const stats = await apiClient.getMealStats();
      setMealStats(stats);
    } catch (error) {
      console.error('Error fetching meal stats:', error);
      setMealStats(null);
    }
  };

  // ============================================
  // FUNÇÕES DE CÁLCULO
  // ============================================

  const calculateBMI = () => {
    if (currentUser?.weight && currentUser?.height) {
      const heightInMeters = currentUser.height / 100;
      const bmi = currentUser.weight / (heightInMeters * heightInMeters);
      return bmi.toFixed(1);
    }
    return 'N/A';
  };

  const getBMICategory = () => {
    const bmi = parseFloat(calculateBMI());
    if (isNaN(bmi)) return 'N/A';
    if (bmi < 18.5) return 'Abaixo do peso';
    if (bmi < 25) return 'Peso normal';
    if (bmi < 30) return 'Sobrepeso';
    return 'Obesidade';
  };

  const calculateDailyCalories = () => {
    if (!currentUser?.weight || !currentUser?.height || !currentUser?.age) return 1800;
    
    let bmr;
    if (currentUser.gender === 'male') {
      bmr = 88.36 + (13.4 * currentUser.weight) + (4.8 * currentUser.height) - (5.7 * currentUser.age);
    } else {
      bmr = 447.6 + (9.2 * currentUser.weight) + (3.1 * currentUser.height) - (4.3 * currentUser.age);
    }
    
    const activityFactors = {
      sedentary: 1.2,
      light: 1.375,
      moderate: 1.55,
      active: 1.725,
      very_active: 1.9
    };
    
    const tdee = bmr * (activityFactors[currentUser.activity_level] || 1.2);
    
    if (currentUser.fitness_goals?.includes('weight_loss')) {
      return Math.round(tdee - 500);
    } else if (currentUser.fitness_goals?.includes('muscle_gain')) {
      return Math.round(tdee + 300);
    }
    
    return Math.round(tdee);
  };

  const getTotalCalories = () => {
    return meals.reduce((sum, meal) => sum + (meal.calories || 0), 0);
  };

  const getTotalProtein = () => {
    return meals.reduce((sum, meal) => sum + (meal.protein || 0), 0);
  };

  const getTotalCarbs = () => {
    return meals.reduce((sum, meal) => sum + (meal.carbs || 0), 0);
  };

  const getTotalFats = () => {
    return meals.reduce((sum, meal) => sum + (meal.fats || 0), 0);
  };

  const getTotalWorkoutDuration = () => {
    return workouts.reduce((sum, w) => sum + (w.duration || 0), 0);
  };

  const getTotalCaloriesBurned = () => {
    return workouts.reduce((sum, w) => sum + (w.calories_burned || 0), 0);
  };

  const getCaloriesBalance = () => {
    return getTotalCalories() - getTotalCaloriesBurned();
  };

  // ============================================
  // FUNÇÕES DE INTERAÇÃO
  // ============================================

  const showNotification = (message, type = 'info') => {
    const id = Date.now();
    setNotifications(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 3000);
  };

  const addToRecentActions = (action) => {
    setRecentActions(prev => [action, ...prev].slice(0, 10));
  };

  const handleAddMeal = async () => {
    const mealData = {
      name: prompt('Nome da refeição:'),
      meal_type: prompt('Tipo (cafe, almoco, jantar, lanche):'),
      calories: parseFloat(prompt('Calorias:') || 0),
      protein: parseFloat(prompt('Proteínas (g):') || 0),
      carbs: parseFloat(prompt('Carboidratos (g):') || 0),
      fats: parseFloat(prompt('Gorduras (g):') || 0)
    };
    
    if (mealData.name && !isNaN(mealData.calories)) {
      try {
        await apiClient.addMeal(mealData);
        await loadMealsData();
        await loadDailyStats();
        showNotification('Refeição adicionada com sucesso! 🍽️', 'success');
      } catch (error) {
        console.error('Error adding meal:', error);
        showNotification('Erro ao adicionar refeição', 'error');
      }
    }
  };

  const handleCompleteWorkout = async (workoutId) => {
    try {
      await apiClient.completeWorkout(workoutId);
      await loadWorkoutsData();
      showNotification('Treino concluído! 🎉', 'success');
    } catch (error) {
      console.error('Error completing workout:', error);
      showNotification('Erro ao completar treino', 'error');
    }
  };

  const handleUpdateWeight = async () => {
    const value = prompt('Digite seu peso atual (kg):');
    if (value && !isNaN(parseFloat(value))) {
      try {
        await apiClient.updateWeight(parseFloat(value));
        await loadProfileData();
        await loadProgressData();
        showNotification('Peso atualizado com sucesso! ⚖️', 'success');
      } catch (error) {
        console.error('Error updating weight:', error);
        showNotification('Erro ao atualizar peso', 'error');
      }
    }
  };

  const handleUpdateBodyFat = async () => {
    const value = prompt('Digite seu percentual de gordura atual:');
    if (value && !isNaN(parseFloat(value))) {
      try {
        await apiClient.updateBodyFat(parseFloat(value));
        await loadProfileData();
        showNotification('Percentual de gordura atualizado! 📊', 'success');
      } catch (error) {
        console.error('Error updating body fat:', error);
        showNotification('Erro ao atualizar percentual de gordura', 'error');
      }
    }
  };

  // ============================================
  // RENDERIZAÇÃO
  // ============================================

  if (isLoading && !currentUser) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Carregando dashboard...</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      {/* Notificações */}
      <div className="notifications-container">
        {notifications.map(notif => (
          <div key={notif.id} className={`notification notification-${notif.type}`}>
            {notif.message}
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="dashboard-tabs">
        <button 
          className={activeTab === 'chat' ? 'active' : ''}
          onClick={() => setActiveTab('chat')}
        >
          💬 Chat IA
        </button>
        <button 
          className={activeTab === 'profile' ? 'active' : ''}
          onClick={() => setActiveTab('profile')}
        >
          👤 Perfil
        </button>
        <button 
          className={activeTab === 'nutrition' ? 'active' : ''}
          onClick={() => setActiveTab('nutrition')}
        >
          🍽️ Nutrição
        </button>
        <button 
          className={activeTab === 'workouts' ? 'active' : ''}
          onClick={() => setActiveTab('workouts')}
        >
          💪 Treinos
        </button>
        <button 
          className={activeTab === 'progress' ? 'active' : ''}
          onClick={() => setActiveTab('progress')}
        >
          📈 Progresso
        </button>
        <button 
          className={activeTab === 'health' ? 'active' : ''}
          onClick={() => setActiveTab('health')}
        >
          🏥 Saúde
        </button>
        <button 
          className={activeTab === 'analytics' ? 'active' : ''}
          onClick={() => setActiveTab('analytics')}
        >
          📊 Analytics
        </button>
      </div>

      <div className="dashboard-content">
        {/* TAB CHAT */}
        {activeTab === 'chat' && (
          <div className="chat-tab">
            <ChatInterface 
              onWorkoutCreated={loadWorkoutsData}
              onProfileUpdated={loadProfileData}
            />
          </div>
        )}

        {/* TAB PERFIL */}
        {activeTab === 'profile' && (
          <div className="profile-tab">
            <h3>👤 Meu Perfil</h3>
            
            <div className="profile-stats">
              <div className="stat-card">
                <span className="stat-label">IMC</span>
                <span className="stat-value">{calculateBMI()}</span>
                <span className="stat-sub">{getBMICategory()}</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Calorias Diárias</span>
                <span className="stat-value">{calculateDailyCalories()} kcal</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">% Gordura</span>
                <span className="stat-value">
                  {currentUser?.body_fat ? `${currentUser.body_fat}%` : 'N/A'}
                </span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Idade</span>
                <span className="stat-value">{currentUser?.age || 'N/A'} anos</span>
              </div>
            </div>

            <div className="profile-details">
              <h4>Informações Pessoais</h4>
              <div className="detail-item"><strong>Nome:</strong> {currentUser?.full_name || currentUser?.username}</div>
              <div className="detail-item"><strong>Email:</strong> {currentUser?.email}</div>
              <div className="detail-item"><strong>Peso:</strong> {currentUser?.weight || 'N/A'} kg</div>
              <div className="detail-item"><strong>Altura:</strong> {currentUser?.height || 'N/A'} cm</div>
              <div className="detail-item"><strong>Gênero:</strong> {currentUser?.gender === 'male' ? 'Masculino' : 'Feminino'}</div>
              <div className="detail-item"><strong>Nível de Atividade:</strong> {currentUser?.activity_level || 'N/A'}</div>
            </div>

            {currentUser?.fitness_goals?.length > 0 && (
              <div className="profile-goals">
                <h4>🎯 Objetivos</h4>
                <div className="goals-list">
                  {currentUser.fitness_goals.map((goal, index) => (
                    <span key={index} className="goal-tag">{goal}</span>
                  ))}
                </div>
              </div>
            )}

            <div className="quick-update">
              <h4>⚡ Atualização Rápida</h4>
              <div className="quick-update-buttons">
                <button onClick={handleUpdateWeight} className="quick-btn">⚖️ Atualizar Peso</button>
                <button onClick={handleUpdateBodyFat} className="quick-btn">📊 Atualizar % Gordura</button>
              </div>
            </div>
          </div>
        )}

        {/* TAB NUTRIÇÃO */}
        {activeTab === 'nutrition' && (
          <div className="nutrition-tab">
            <h3>🍽️ Refeições de Hoje</h3>
            
            <div className="nutrition-summary">
              <div className="summary-card">
                <span className="summary-label">Calorias</span>
                <span className="summary-value">{getTotalCalories()} / {calculateDailyCalories()} kcal</span>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${Math.min(100, (getTotalCalories() / calculateDailyCalories()) * 100)}%` }}></div>
                </div>
              </div>
              <div className="summary-card">
                <span className="summary-label">Proteínas</span>
                <span className="summary-value">{getTotalProtein()} g</span>
              </div>
              <div className="summary-card">
                <span className="summary-label">Carboidratos</span>
                <span className="summary-value">{getTotalCarbs()} g</span>
              </div>
              <div className="summary-card">
                <span className="summary-label">Gorduras</span>
                <span className="summary-value">{getTotalFats()} g</span>
              </div>
            </div>

            {meals.length > 0 ? (
              <div className="meals-list">
                {meals.map((meal, index) => (
                  <div key={index} className="meal-item">
                    <div className="meal-header">
                      <strong>{meal.meal_type}</strong>
                      <span>{meal.calories} kcal</span>
                    </div>
                    <p>{meal.name}</p>
                    <div className="meal-macros">
                      <span>🥩 P: {meal.protein}g</span>
                      <span>🍚 C: {meal.carbs}g</span>
                      <span>🧈 G: {meal.fats}g</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty-state">Nenhuma refeição registrada hoje</p>
            )}
            
            <button onClick={handleAddMeal} className="add-button">+ Adicionar Refeição</button>
          </div>
        )}

        {/* TAB TREINOS */}
        {activeTab === 'workouts' && (
          <div className="workouts-tab">
            <h3>💪 Treinos de Hoje</h3>
            
            <div className="workout-summary">
              <div className="summary-card">
                <span className="summary-label">Duração Total</span>
                <span className="summary-value">{getTotalWorkoutDuration()} min</span>
              </div>
              <div className="summary-card">
                <span className="summary-label">Calorias Queimadas</span>
                <span className="summary-value">{getTotalCaloriesBurned()} kcal</span>
              </div>
              <div className="summary-card">
                <span className="summary-label">Saldo Calórico</span>
                <span className={`summary-value ${getCaloriesBalance() > 0 ? 'text-red' : 'text-green'}`}>
                  {getCaloriesBalance()} kcal
                </span>
              </div>
            </div>

            {workouts.length > 0 ? (
              <div className="workouts-list">
                {workouts.map((workout, index) => (
                  <div key={index} className="workout-item">
                    <div className="workout-header">
                      <strong>{workout.name}</strong>
                      <span>{workout.duration} min • {workout.calories_burned} kcal</span>
                    </div>
                    {workout.description && <p>{workout.description}</p>}
                    <button onClick={() => handleCompleteWorkout(workout.id)} className="complete-btn">
                      ✅ Marcar como Concluído
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty-state">Nenhum treino registrado hoje. Peça ao chat para criar um treino!</p>
            )}
          </div>
        )}

        {/* TAB PROGRESSO */}
        {activeTab === 'progress' && (
          <div className="progress-tab">
            <h3>📈 Meu Progresso</h3>
            
            {recentActions.length > 0 && (
              <div className="recent-actions">
                <h4>📋 Últimas Ações da IA</h4>
                <div className="actions-list">
                  {recentActions.slice(0, 5).map((action, index) => (
                    <div key={index} className="action-item">
                      <span className="action-icon">
                        {action.action === 'workout_created' && '💪'}
                        {action.action === 'profile_updated' && '📊'}
                        {action.action === 'meal_added' && '🍽️'}
                      </span>
                      <div className="action-info">
                        <div className="action-type">
                          {action.action === 'workout_created' && 'Treino criado'}
                          {action.action === 'profile_updated' && 'Perfil atualizado'}
                          {action.action === 'meal_added' && 'Refeição adicionada'}
                        </div>
                        <div className="action-time">{new Date(action.timestamp).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB SAÚDE */}
        {activeTab === 'health' && (
          <div className="health-tab">
            <HealthMatrix />
          </div>
        )}

        {/* TAB ANALYTICS */}
        {activeTab === 'analytics' && (
          <div className="analytics-tab">
            <h3>📊 Analytics</h3>
            
            {dailyStats && (
              <div className="analytics-section">
                <h4>Estatísticas de Hoje</h4>
                <div className="stats-grid">
                  <div className="stat-item"><span>Calorias</span><strong>{dailyStats.total_calories || 0} kcal</strong></div>
                  <div className="stat-item"><span>Proteínas</span><strong>{dailyStats.total_protein || 0} g</strong></div>
                  <div className="stat-item"><span>Carboidratos</span><strong>{dailyStats.total_carbs || 0} g</strong></div>
                  <div className="stat-item"><span>Gorduras</span><strong>{dailyStats.total_fats || 0} g</strong></div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <style jsx>{`
        .dashboard { background: #ecfdf5; min-height: 100vh; }
        .dashboard-tabs { display: flex; flex-wrap: wrap; gap: 8px; background: white; padding: 12px 20px; border-radius: 16px; margin-bottom: 24px; }
        .dashboard-tabs button { padding: 10px 20px; border: none; background: #f3f4f6; color: #4b5563; border-radius: 40px; cursor: pointer; font-weight: 500; }
        .dashboard-tabs button:hover { background: #d1fae5; color: #059669; }
        .dashboard-tabs button.active { background: linear-gradient(135deg, #059669, #10b981); color: white; }
        .profile-stats, .nutrition-summary, .workout-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card, .profile-details, .profile-goals, .meal-item, .workout-item, .recent-actions, .analytics-section { background: white; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .stat-value { font-size: 32px; font-weight: bold; color: #059669; display: block; }
        .goal-tag { background: linear-gradient(135deg, #d1fae5, #a7f3d0); color: #064e3b; padding: 6px 12px; border-radius: 20px; font-size: 13px; display: inline-block; margin: 4px; }
        .quick-update { background: linear-gradient(135deg, #d1fae5, #a7f3d0); padding: 20px; border-radius: 16px; margin-top: 20px; }
        .quick-btn { background: #059669; color: white; border: none; padding: 10px 20px; border-radius: 40px; cursor: pointer; margin-right: 10px; }
        .add-button { background: #059669; color: white; border: none; padding: 12px 24px; border-radius: 40px; cursor: pointer; margin-top: 20px; }
        .complete-btn { background: #34d399; color: #064e3b; border: none; padding: 8px 16px; border-radius: 20px; cursor: pointer; margin-top: 12px; }
        .empty-state { text-align: center; padding: 40px; color: #6b7280; background: white; border-radius: 16px; }
        .progress-bar { width: 100%; height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden; margin-top: 8px; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #059669, #34d399); }
        .text-red { color: #ef4444; }
        .text-green { color: #10b981; }
        .action-item { display: flex; align-items: center; gap: 12px; padding: 12px; border-bottom: 1px solid #f3f4f6; }
        .action-icon { font-size: 24px; }
        .action-type { font-weight: 500; color: #059669; }
        .action-time { font-size: 11px; color: #9ca3af; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-top: 16px; }
        .stat-item { background: #f9fafb; padding: 16px; border-radius: 12px; text-align: center; }
        .stat-item strong { font-size: 20px; color: #059669; display: block; }
        .notification { position: fixed; bottom: 20px; right: 20px; padding: 12px 20px; border-radius: 8px; color: white; z-index: 1000; animation: slideIn 0.3s ease; }
        .notification-success { background: #10b981; }
        .notification-error { background: #ef4444; }
        .notification-info { background: #3b82f6; }
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .loading-container { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; }
        .spinner { width: 40px; height: 40px; border: 4px solid #e5e7eb; border-top-color: #059669; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default Dashboard;

// frontend/src/components/Dashboard.js

/*
import React, { useState, useEffect } from 'react';
import './Dashboard.css';
import HealthMatrix from './HealthMatrix';
import apiClient from '../services/api';  // <-- importa o cliente

const Dashboard = ({ user, token }) => {
  const [progress, setProgress] = useState(null);
  const [meals, setMeals] = useState([]);
  const [workouts, setWorkouts] = useState([]);
  const [activeTab, setActiveTab] = useState('profile');

  useEffect(() => {
    if (token) {
      fetchProgress();
      fetchTodayMeals();
      fetchTodayWorkouts();
    }
  }, [token]);

  const fetchProgress = async () => {
    try {
      const data = await apiClient.get('/users/progress');
      setProgress(data);
    } catch (error) {
      console.error('Error fetching progress:', error);
    }
  };

  const fetchTodayMeals = async () => {
    try {
      const data = await apiClient.get('/meals/today');
      setMeals(data);
    } catch (error) {
      console.error('Error fetching meals:', error);
    }
  };

  const fetchTodayWorkouts = async () => {
    try {
      const data = await apiClient.get('/workouts/today');
      setWorkouts(data);
    } catch (error) {
      console.error('Error fetching workouts:', error);
    }
  };

  const calculateBMI = () => {
    if (user?.weight && user?.height) {
      const heightInMeters = user.height / 100;
      return (user.weight / (heightInMeters * heightInMeters)).toFixed(1);
    }
    return 'N/A';
  };

  const calculateDailyCalories = () => {
    if (!user) return 'N/A';
    
    // Fórmula de Harris-Benedict (simplificada)
    let bmr;
    if (user.gender === 'male') {
      bmr = 88.36 + (13.4 * user.weight) + (4.8 * user.height) - (5.7 * user.age);
    } else {
      bmr = 447.6 + (9.2 * user.weight) + (3.1 * user.height) - (4.3 * user.age);
    }
    
    // Fator de atividade
    const activityFactors = {
      sedentary: 1.2,
      light: 1.375,
      moderate: 1.55,
      active: 1.725,
      very_active: 1.9
    };
    
    const tdee = bmr * (activityFactors[user.activity_level] || 1.2);
    
    // Ajuste para objetivos
    if (user.fitness_goals?.includes('weight_loss')) {
      return Math.round(tdee - 500);
    } else if (user.fitness_goals?.includes('muscle_gain')) {
      return Math.round(tdee + 300);
    }
    
    return Math.round(tdee);
  };

  return (
    <div className="dashboard">
      <div className="dashboard-tabs">
        <button 
          className={activeTab === 'profile' ? 'active' : ''}
          onClick={() => setActiveTab('profile')}
        >
          Perfil
        </button>
        <button 
          className={activeTab === 'nutrition' ? 'active' : ''}
          onClick={() => setActiveTab('nutrition')}
        >
          Nutrição
        </button>
        <button 
          className={activeTab === 'workouts' ? 'active' : ''}
          onClick={() => setActiveTab('workouts')}
        >
          Treinos
        </button>
        <button 
          className={activeTab === 'progress' ? 'active' : ''}
          onClick={() => setActiveTab('progress')}
        >
          Progresso
        </button>
        <button 
          className={activeTab === 'health' ? 'active' : ''}
          onClick={() => setActiveTab('health')}
        >
          Saúde Sistema
        </button>
      </div>

      <div className="dashboard-content">
        {activeTab === 'profile' && (
          <div className="profile-tab">
            <h3>Meu Perfil</h3>
            
            <div className="profile-stats">
              <div className="stat-card">
                <span className="stat-label">IMC</span>
                <span className="stat-value">{calculateBMI()}</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Calorias Diárias</span>
                <span className="stat-value">{calculateDailyCalories()} kcal</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Idade</span>
                <span className="stat-value">{user?.age} anos</span>
              </div>
            </div>

            <div className="profile-details">
              <h4>Detalhes Pessoais</h4>
              <div className="detail-item">
                <strong>Nome:</strong> {user?.full_name || user?.username}
              </div>
              <div className="detail-item">
                <strong>Email:</strong> {user?.email}
              </div>
              <div className="detail-item">
                <strong>Peso:</strong> {user?.weight} kg
              </div>
              <div className="detail-item">
                <strong>Altura:</strong> {user?.height} cm
              </div>
              <div className="detail-item">
                <strong>Gênero:</strong> {user?.gender === 'male' ? 'Masculino' : 'Feminino'}
              </div>
              <div className="detail-item">
                <strong>Nível de Atividade:</strong> {user?.activity_level}
              </div>
            </div>

            <div className="profile-goals">
              <h4>Objetivos</h4>
              <div className="goals-list">
                {user?.fitness_goals?.map((goal, index) => (
                  <span key={index} className="goal-tag">{goal}</span>
                ))}
              </div>
            </div>

            {user?.health_conditions?.length > 0 && (
              <div className="profile-health">
                <h4>Condições de Saúde</h4>
                <div className="conditions-list">
                  {user?.health_conditions?.map((condition, index) => (
                    <span key={index} className="condition-tag">{condition}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'nutrition' && (
          <div className="nutrition-tab">
            <h3>Refeições de Hoje</h3>
            {meals.length > 0 ? (
              <div className="meals-list">
                {meals.map((meal, index) => (
                  <div key={index} className="meal-item">
                    <div className="meal-header">
                      <strong>{meal.meal_type}</strong>
                      <span>{meal.calories} kcal</span>
                    </div>
                    <p>{meal.name}</p>
                    <div className="meal-macros">
                      <span>P: {meal.protein}g</span>
                      <span>C: {meal.carbs}g</span>
                      <span>G: {meal.fats}g</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty-state">Nenhuma refeição registrada hoje</p>
            )}
          </div>
        )}

        {activeTab === 'workouts' && (
          <div className="workouts-tab">
            <h3>Treinos de Hoje</h3>
            {workouts.length > 0 ? (
              <div className="workouts-list">
                {workouts.map((workout, index) => (
                  <div key={index} className="workout-item">
                    <div className="workout-header">
                      <strong>{workout.name}</strong>
                      <span>{workout.duration} min</span>
                    </div>
                    <p>{workout.description}</p>
                    {workout.exercises && (
                      <div className="exercises-list">
                        {workout.exercises.map((exercise, i) => (
                          <div key={i} className="exercise-item">
                            {exercise.name}: {exercise.sets}x{exercise.reps}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty-state">Nenhum treino registrado hoje</p>
            )}
          </div>
        )}

        {activeTab === 'progress' && (
          <div className="progress-tab">
            <h3>Meu Progresso</h3>
            {progress ? (
              <div className="progress-stats">
                <div className="stat-card">
                  <span className="stat-label">Peso Atual</span>
                  <span className="stat-value">{progress.weight} kg</span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Progresso</span>
                  <span className="stat-value">
                    {progress.weight_change > 0 ? '+' : ''}{progress.weight_change} kg
                  </span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Meta</span>
                  <span className="stat-value">{progress.goal_weight} kg</span>
                </div>
              </div>
            ) : (
              <p className="empty-state">Nenhum progresso registrado ainda</p>
            )}
          </div>
        )}

        {activeTab === 'health' && (
          <div className="health-tab">
            <HealthMatrix />
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;

*/