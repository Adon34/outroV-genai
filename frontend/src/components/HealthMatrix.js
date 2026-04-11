// frontend/src/components/HealthMatrix.js
import React, { useState, useEffect } from 'react';
import './HealthMatrix.css';
import apiClient from '../services/api';

const HealthMatrix = () => {
    const [healthData, setHealthData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchHealthData();
        // Refresh every 30 seconds
        const interval = setInterval(fetchHealthData, 30000);
        return () => clearInterval(interval);
    }, []);

    const fetchHealthData = async () => {
        try {
            setLoading(true);

            const data = await apiClient.get('/health/live');
            setHealthData(data);
            setError(null);
        } catch (err) {
            setError(err.message);
            console.error('Failed to fetch health data:', err);
        } finally {
            setLoading(false);
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'healthy': return '#10b981'; // green
            case 'degraded': return '#f59e0b'; // yellow
            case 'unhealthy': return '#ef4444'; // red
            default: return '#6b7280'; // gray
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'healthy': return '✓';
            case 'degraded': return '⚠';
            case 'unhealthy': return '✗';
            default: return '?';
        }
    };

    if (loading && !healthData) {
        return (
            <div className="health-matrix">
                <div className="health-header">
                    <h2>Matriz de Saúde por Componente</h2>
                </div>
                <div className="loading">Carregando dados de saúde...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="health-matrix">
                <div className="health-header">
                    <h2>Matriz de Saúde por Componente</h2>
                </div>
                <div className="error">
                    Erro ao carregar dados: {error}
                    <button onClick={fetchHealthData} className="retry-btn">
                        Tentar Novamente
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="health-matrix">
            <div className="health-header">
                <h2>Matriz de Saúde por Componente</h2>
                <div className="overall-status">
                    <span
                        className="status-indicator"
                        style={{ backgroundColor: getStatusColor(healthData?.status) }}
                    >
                        {getStatusIcon(healthData?.status)} {healthData?.status?.toUpperCase()}
                    </span>
                    <span className="last-updated">
                        Atualizado: {healthData?.timestamp ? new Date(healthData.timestamp).toLocaleString('pt-BR') : 'N/A'}
                    </span>
                </div>
            </div>

            <div className="components-grid">
                {healthData?.components && Object.entries(healthData.components).map(([component, health]) => (
                    <div key={component} className="component-card">
                        <div className="component-header">
                            <h3>{component.replace('_', ' ').toUpperCase()}</h3>
                            <span
                                className="component-status"
                                style={{ color: getStatusColor(health.status) }}
                            >
                                {getStatusIcon(health.status)} {health.status}
                            </span>
                        </div>

                        <div className="component-details">
                            {health.response_time_ms && (
                                <div className="metric">
                                    <span className="metric-label">Tempo de Resposta:</span>
                                    <span className="metric-value">{health.response_time_ms.toFixed(1)}ms</span>
                                </div>
                            )}

                            {health.details && Object.entries(health.details).map(([key, value]) => (
                                <div key={key} className="metric">
                                    <span className="metric-label">
                                        {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                                    </span>
                                    <span className="metric-value">
                                        {typeof value === 'number' ? value.toFixed(1) : value}
                                        {key.includes('percent') || key.includes('utilization') ? '%' : ''}
                                        {key.includes('mb') ? ' MB' : ''}
                                    </span>
                                </div>
                            ))}

                            {health.error_message && (
                                <div className="error-message">
                                    <strong>Erro:</strong> {health.error_message}
                                </div>
                            )}

                            {health.last_checked && (
                                <div className="last-checked">
                                    Verificado: {new Date(health.last_checked).toLocaleTimeString('pt-BR')}
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>

            <div className="health-footer">
                <button onClick={fetchHealthData} className="refresh-btn" disabled={loading}>
                    {loading ? 'Atualizando...' : 'Atualizar Agora'}
                </button>
            </div>
        </div>
    );
};

export default HealthMatrix;