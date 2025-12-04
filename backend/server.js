const express = require('express');
const fs = require('fs');
const path = require('path');
const app = express();

const PORT = process.env.PORT || 8000;

// Статика для frontend (правильный путь)
app.use('/', express.static(path.join(__dirname, 'frontend')));

// API endpoint для вопросов
app.get('/data/questions', (req, res) => {
    const questionsPath = path.join(__dirname, 'data', 'questions.json');
    
    fs.readFile(questionsPath, 'utf8', (err, data) => {
        if (err) {
            console.error('Error reading questions.json:', err);
            return res.status(500).json({ error: 'Failed to load questions' });
        }
        res.json(JSON.parse(data));
    });
});

// API endpoint для результатов пользователей
app.get('/data/users_results', (req, res) => {
    const resultsPath = path.join(__dirname, 'backend', 'data', 'users_results.json');
    
    fs.readFile(resultsPath, 'utf8', (err, data) => {
        if (err) {
            console.error('Error reading users_results.json:', err);
            return res.status(500).json({ error: 'Failed to load results' });
        }
        res.json(JSON.parse(data));
    });
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on port ${PORT}`);
});
