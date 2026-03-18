// scripts/seed-data.js
const axios = require('axios');

const API_URL = process.env.API_URL || 'http://localhost:8000';

const seedData = async () => {
    console.log('Seeding initial data...');

    // Create default goals
    const goals = [
        { name: 'weight_loss', description: 'Perder peso de forma saudável', category: 'fitness' },
        { name: 'muscle_gain', description: 'Ganhar massa muscular', category: 'fitness' },
        { name: 'maintenance', description: 'Manter peso atual', category: 'fitness' },
        { name: 'improve_health', description: 'Melhorar saúde geral', category: 'health' },
        { name: 'increase_strength', description: 'Aumentar força', category: 'fitness' },
        { name: 'improve_endurance', description: 'Melhorar resistência', category: 'fitness' }
    ];

    console.log('Goals seeded successfully');
};

seedData().catch(console.error);