// Telegram Web App SDK
const tg = window.Telegram.WebApp;
tg.expand();
tg.enableClosingConfirmation();

// Применяем тему Telegram
if (tg.colorScheme === 'dark') {
    document.body.classList.add('dark-theme');
}

// Конфигурация
const API_URL = 'http://localhost:8000/data'; // Замените на ваш backend URL
const QUIZ_TIME = 15 * 60; // 15 минут в секундах

// Состояние приложения
let currentQuestionIndex = 0;
let allQuestions = [];
let userAnswers = [];
let startTime = null;
let timerInterval = null;
let timeRemaining = QUIZ_TIME;

// Мотивационные фразы
const motivationPhrases = [
    'Отлично! Продолжай!',
    'Ты молодец! 💪',
    'Так держать! 🔥',
    'У тебя получится! ⭐',
    'Почти финиш! 🎯',
    'Сосредоточься! 🎓',
    'Всё получится! ✨'
];

// Элементы DOM
const screens = {
    loading: document.getElementById('loading-screen'),
    welcome: document.getElementById('welcome-screen'),
    quiz: document.getElementById('quiz-screen'),
    final: document.getElementById('final-screen'),
    error: document.getElementById('error-screen')
};

// Инициализация приложения
async function init() {
    console.log('Инициализация приложения...');

    // Имитация загрузки
    await sleep(1500);

    // Проверяем, прошел ли пользователь тест
    const userId = tg.initDataUnsafe?.user?.id || 'test_user_' + Math.random();

    try {
        const response = await fetch(`${API_URL}/check-user/${userId}`);
        const data = await response.json();

        if (data.completed) {
            showScreen('error');
            document.getElementById('error-message').textContent = 
                'Вы уже прошли этот тест. Повторное прохождение невозможно. 🔒';
            return;
        }
    } catch (error) {
        console.error('Ошибка проверки пользователя:', error);
        // Продолжаем работу даже если backend недоступен (для разработки)
    }

    showScreen('welcome');
}

// Показать экран
function showScreen(screenName) {
    Object.values(screens).forEach(screen => screen.classList.remove('active'));
    screens[screenName].classList.add('active');
}

// Начать тест
async function startQuiz() {
    try {
        // Загружаем вопросы
        const response = await fetch(`${API_URL}/questions`);
        const data = await response.json();

        // Объединяем и перемешиваем вопросы
        allQuestions = shuffleArray([
            ...data.statistics,
            ...data.probability,
            ...data.ml
        ]);

        startTime = Date.now();
        currentQuestionIndex = 0;
        userAnswers = [];

        showScreen('quiz');
        startTimer();
        displayQuestion();

    } catch (error) {
        console.error('Ошибка загрузки вопросов:', error);
        showScreen('error');
        document.getElementById('error-message').textContent = 
            'Не удалось загрузить вопросы. Проверьте подключение к интернету.';
    }
}

// Отображение вопроса
function displayQuestion() {
    const question = allQuestions[currentQuestionIndex];
    const progress = ((currentQuestionIndex + 1) / allQuestions.length) * 100;

    // Обновляем прогресс
    document.getElementById('progress-fill').style.width = progress + '%';
    document.getElementById('question-counter').textContent = 
        `${currentQuestionIndex + 1}/${allQuestions.length}`;

    // Определяем тему
    const topic = getTopicName(question.id);
    document.getElementById('current-topic').textContent = topic;

    // Отображаем вопрос
    document.getElementById('question-text').textContent = question.question;

    // Отображаем варианты ответов
    const container = document.getElementById('options-container');
    container.innerHTML = '';

    question.options.forEach((option, index) => {
        const btn = document.createElement('button');
        btn.className = 'option-btn';
        btn.textContent = option;
        btn.onclick = () => selectAnswer(index);
        container.appendChild(btn);
    });

    // Обновляем мотивацию
    updateMotivation();
}

// Определить тему по ID вопроса
function getTopicName(id) {
    if (id <= 3) return '📊 Статистика';
    if (id <= 6) return '🎲 Теория вероятностей';
    return '🤖 Machine Learning';
}

// Выбор ответа
function selectAnswer(answerIndex) {
    userAnswers.push(answerIndex);
    currentQuestionIndex++;

    if (currentQuestionIndex < allQuestions.length) {
        // Следующий вопрос
        displayQuestion();
    } else {
        // Тест завершен
        finishQuiz();
    }
}

// Таймер
function startTimer() {
    timerInterval = setInterval(() => {
        timeRemaining--;

        const minutes = Math.floor(timeRemaining / 60);
        const seconds = timeRemaining % 60;
        document.getElementById('timer').textContent = 
            `⏱️ ${minutes}:${seconds.toString().padStart(2, '0')}`;

        if (timeRemaining <= 0) {
            clearInterval(timerInterval);
            finishQuiz();
        }
    }, 1000);
}

// Завершение теста
async function finishQuiz() {
    clearInterval(timerInterval);

    const endTime = Date.now();
    const timeSpent = Math.floor((endTime - startTime) / 1000);
    const userId = tg.initDataUnsafe?.user?.id || 'test_user_' + Math.random();
    const username = tg.initDataUnsafe?.user?.username || 'Anonymous';

    // Отправляем результаты на backend
    try {
        await fetch(`${API_URL}/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_user_id: userId,
                username: username,
                answers: userAnswers,
                time_spent: timeSpent,
                questions: allQuestions.map(q => q.id)
            })
        });
    } catch (error) {
        console.error('Ошибка отправки результатов:', error);
    }

    // Показываем финальный экран
    showScreen('final');

    document.getElementById('questions-answered').textContent = 
        `${userAnswers.length}/${allQuestions.length}`;

    const minutes = Math.floor(timeSpent / 60);
    const seconds = timeSpent % 60;
    document.getElementById('time-spent').textContent = 
        `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

// Обновление мотивации
function updateMotivation() {
    const phrase = motivationPhrases[Math.floor(Math.random() * motivationPhrases.length)];
    document.getElementById('motivation-text').textContent = phrase;
}

// Перемешать массив (Fisher-Yates)
function shuffleArray(array) {
    const newArray = [...array];
    for (let i = newArray.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [newArray[i], newArray[j]] = [newArray[j], newArray[i]];
    }
    return newArray;
}

// Утилита: задержка
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Event Listeners
document.getElementById('start-btn').addEventListener('click', startQuiz);
document.getElementById('close-btn').addEventListener('click', () => tg.close());
document.getElementById('close-error-btn').addEventListener('click', () => tg.close());

// Запуск приложения
init();