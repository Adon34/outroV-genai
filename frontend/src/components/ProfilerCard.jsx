// frontend/src/components/ProfileCard.jsx
import React, { useState } from 'react';
import api from '../services/api';

const ProfileCard = ({ profile, onUpdate }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [formData, setFormData] = useState({
        weight: profile?.weight || '',
        body_fat: profile?.body_fat || '',
        age: profile?.age || ''
    });

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            await api.updateProfile(formData);
            setIsEditing(false);
            onUpdate();
        } catch (error) {
            console.error('Erro ao atualizar perfil:', error);
        }
    };

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: parseFloat(e.target.value) || ''
        });
    };

    return (
        <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold">👤 Meu Perfil</h2>
                <button
                    onClick={() => setIsEditing(!isEditing)}
                    className="text-blue-600 hover:text-blue-700"
                >
                    {isEditing ? 'Cancelar' : '✏️ Editar'}
                </button>
            </div>

            {isEditing ? (
                <form onSubmit={handleSubmit} className="space-y-3">
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Peso (kg)</label>
                        <input
                            type="number"
                            name="weight"
                            value={formData.weight}
                            onChange={handleChange}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                            step="0.1"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">% Gordura</label>
                        <input
                            type="number"
                            name="body_fat"
                            value={formData.body_fat}
                            onChange={handleChange}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                            step="0.5"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Idade</label>
                        <input
                            type="number"
                            name="age"
                            value={formData.age}
                            onChange={handleChange}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                        />
                    </div>
                    <button
                        type="submit"
                        className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition"
                    >
                        Salvar
                    </button>
                </form>
            ) : (
                <div className="space-y-2">
                    <div className="flex justify-between">
                        <span className="text-gray-600">Peso:</span>
                        <span className="font-semibold">{profile?.weight || 'N/A'} kg</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600">Altura:</span>
                        <span className="font-semibold">{profile?.height || 'N/A'} cm</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600">% Gordura:</span>
                        <span className="font-semibold">{profile?.body_fat || 'N/A'}%</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600">IMC:</span>
                        <span className="font-semibold">{profile?.bmi?.toFixed(1) || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600">Nível:</span>
                        <span className="font-semibold">{profile?.activity_level || 'N/A'}</span>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ProfileCard;