// frontend/src/components/Dashboard.js
import React, { useState, useEffect } from 'react';
import './Dashboard.css';
import HealthMatrix from './HealthMatrix';

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
      const response = await fetch('http://localhost:8000/users/progress', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      setProgress(data);
    } catch (error) {
      console.error('Error fetching progress:', error);
    }
  };

  const fetchTodayMeals = async () => {
    try {
      const response = await fetch('http://localhost:8000/meals/today', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      setMeals(data);
    } catch (error) {
      console.error('Error fetching meals:', error);
    }
  };

  const fetchTodayWorkouts = async () => {
    try {
      const response = await fetch('http://localhost:8000/workouts/today', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
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