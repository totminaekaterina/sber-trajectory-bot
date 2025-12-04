from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import os
from datetime import datetime
from pathlib import Path

app = FastAPI(title="Sber Quiz API")

# CORS для работы с Telegram Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Пути к файлам данных
DATA_DIR = Path("data")
QUESTIONS_FILE = DATA_DIR / "questions.json"
RESULTS_FILE = DATA_DIR / "users_results.json"

# Создаем директорию если не существует
DATA_DIR.mkdir(exist_ok=True)

# Инициализация пустого файла результатов
if not RESULTS_FILE.exists():
    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump({}, f)


# Модели данных
class SubmitRequest(BaseModel):
    telegram_user_id: str
    username: str
    answers: List[int]
    time_spent: int
    questions: List[int]


class UserResult(BaseModel):
    username: str
    completed: bool
    timestamp: str
    answers: List[int]
    questions: List[int]
    time_spent: int
    score: int


# Загрузка данных
def load_questions() -> Dict[str, Any]:
    """Загрузить вопросы из JSON файла"""
    try:
        with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Questions file not found")


def load_results() -> Dict[str, Any]:
    """Загрузить результаты пользователей"""
    try:
        with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_results(results: Dict[str, Any]):
    """Сохранить результаты в файл"""
    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def calculate_score(answers: List[int], questions: List[int], all_questions: Dict) -> int:
    """Подсчитать баллы пользователя"""
    score = 0

    # Объединяем все вопросы в один список
    all_qs = []
    for category in ['statistics', 'probability', 'ml']:
        all_qs.extend(all_questions[category])

    # Создаем словарь id -> вопрос для быстрого поиска
    questions_dict = {q['id']: q for q in all_qs}

    # Проверяем каждый ответ
    for i, question_id in enumerate(questions):
        if i < len(answers):
            question = questions_dict.get(question_id)
            if question and answers[i] == question['correct']:
                score += 1

    return score


# API Endpoints

@app.get("/")
async def root():
    return {
        "message": "Sber Quiz API",
        "version": "1.0.0",
        "endpoints": ["/questions", "/check-user/{user_id}", "/submit", "/admin/results"]
    }


@app.get("/questions")
async def get_questions():
    """Получить все вопросы (без правильных ответов)"""
    questions = load_questions()

    # Удаляем правильные ответы для безопасности
    clean_questions = {}
    for category, qs in questions.items():
        clean_questions[category] = [
            {k: v for k, v in q.items() if k != 'correct'}
            for q in qs
        ]

    return clean_questions


@app.get("/check-user/{user_id}")
async def check_user(user_id: str):
    """Проверить, проходил ли пользователь тест"""
    results = load_results()

    if user_id in results:
        return {
            "completed": True,
            "timestamp": results[user_id]["timestamp"]
        }

    return {"completed": False}


@app.post("/submit")
async def submit_quiz(data: SubmitRequest):
    """Сохранить результаты теста"""
    results = load_results()
    user_id = str(data.telegram_user_id)

    # Проверяем, не проходил ли пользователь тест ранее
    if user_id in results:
        raise HTTPException(
            status_code=400,
            detail="User has already completed the quiz"
        )

    # Загружаем вопросы для подсчета баллов
    questions = load_questions()
    score = calculate_score(data.answers, data.questions, questions)

    # Сохраняем результат
    results[user_id] = {
        "username": data.username,
        "completed": True,
        "timestamp": datetime.now().isoformat(),
        "answers": data.answers,
        "questions": data.questions,
        "time_spent": data.time_spent,
        "score": score
    }

    save_results(results)

    return {
        "success": True,
        "message": "Quiz results saved successfully"
    }


@app.get("/admin/results")
async def get_all_results():
    """Получить все результаты (для преподавателя)"""
    # TODO: Добавить аутентификацию для защиты этого endpoint
    results = load_results()

    # Сортируем по баллам
    sorted_results = sorted(
        results.items(),
        key=lambda x: x[1]['score'],
        reverse=True
    )

    return {
        "total_users": len(results),
        "results": [
            {
                "user_id": user_id,
                "username": data['username'],
                "score": data['score'],
                "time_spent": data['time_spent'],
                "timestamp": data['timestamp']
            }
            for user_id, data in sorted_results
        ]
    }


@app.get("/admin/statistics")
async def get_statistics():
    """Получить статистику по ответам"""
    results = load_results()
    questions = load_questions()

    if not results:
        return {"message": "No results yet"}

    # Подсчет статистики
    total_users = len(results)
    total_score = sum(r['score'] for r in results.values())
    avg_score = total_score / total_users if total_users > 0 else 0
    avg_time = sum(r['time_spent'] for r in results.values()) / total_users if total_users > 0 else 0

    return {
        "total_users": total_users,
        "average_score": round(avg_score, 2),
        "average_time_seconds": round(avg_time, 2),
        "max_score": 9,
        "completion_rate": f"{(avg_score / 9 * 100):.1f}%"
    }


# Запуск: uvicorn main:app --reload --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)