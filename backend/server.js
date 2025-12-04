const express = require('express');
const path = require('path');
const app = express();

const PORT = process.env.PORT || 3000;

// Статика для frontend
app.use('/sber_trajectory_bot', express.static(path.join(__dirname, '../frontend')));

// API endpoints
app.get('/sber_trajectory_bot/api/questions', (req, res) => {
    // Ваша логика
    res.json({ questions: [] });
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on port ${PORT}`);
});
