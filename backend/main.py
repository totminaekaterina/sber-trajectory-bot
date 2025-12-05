from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import os
from datetime import datetime
from pathlib import Path
import gspread  # ← ДОБАВИТЬ
from oauth2client.service_account import ServiceAccountCredentials  # ← ДОБАВИТЬ


app = FastAPI(title="Sber Quiz API")


# CORS для работы с Telegram Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Пути к файлам данных
DATA_DIR = Path("data")
QUESTIONS_FILE = DATA_DIR / "questions.json"

# Создаем директорию если не существует
DATA_DIR.mkdir(exist_ok=True)


# Настройка Google Sheets
SCOPE = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

CREDENTIALS = json.loads(os.environ.get('GOOGLE_CREDENTIALS', '{}'))
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID', '')


def get_sheet():
    """Получить доступ к Google Таблице"""
    creds = ServiceAccountCredentials.from_json_keyfile_dict(CREDENTIALS, SCOPE)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1


def init_sheet():
    """Инициализировать заголовки таблицы"""
    try:
        sheet = get_sheet()
        if not sheet.row_values(1):
            headers = [
                'User ID', 'Username', 'Score', 'Time Spent (sec)', 
                'Timestamp', 'Answers', 'Questions'
            ]
            sheet.append_row(headers)
    except Exception as e:
        print(f"Ошибка инициализации таблицы: {e}")


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


def calculate_score(answers: List[int], questions: List[int], all_questions: Dict) -> int:  # ← ИСПРАВЛЕНО
    """Подсчитать баллы пользователя"""
    score = 0
    all_qs = []
    for category in ['statistics', 'probability', 'ml']:
        all_qs.extend(all_questions[category])  # ← ИСПРАВЛЕНО (было QUESTIONS_FILE)
    
    questions_dict = {q['id']: q for q in all_qs}
    
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
        "version": "2.0.0",  # ← Обновлено
        "storage": "Google Sheets",
        "endpoints": ["/questions", "/check-user/{user_id}", "/submit", "/admin/results"]
    }


@app.get("/questions")
async def get_questions():
    """Получить все вопросы (без правильных ответов)"""
    questions = load_questions()  # ← ИСПРАВЛЕНО (было QUESTIONS_FILE)
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
    try:
        sheet = get_sheet()
        user_ids = sheet.col_values(1)[1:]  # Пропускаем заголовок
        
        if user_id in user_ids:
            return {"completed": True}
        return {"completed": False}
    except Exception as e:
        print(f"Ошибка проверки пользователя: {e}")
        return {"completed": False}


@app.post("/submit")
async def submit_quiz(data: SubmitRequest):
    """Сохранить результаты теста в Google Sheets"""
    try:
        sheet = get_sheet()
        user_id = str(data.telegram_user_id)
        
        # Проверяем, не проходил ли тест
        user_ids = sheet.col_values(1)[1:]
        if user_id in user_ids:
            raise HTTPException(
                status_code=400,
                detail="User has already completed the quiz"
            )
        
        # Загружаем вопросы и подсчитываем баллы
        questions = load_questions()  # ← ДОБАВЛЕНО
        score = calculate_score(data.answers, data.questions, questions)  # ← ИСПРАВЛЕНО
        
        # Добавляем строку в таблицу
        row = [
            user_id,
            data.username,
            score,
            data.time_spent,
            datetime.now().isoformat(),
            str(data.answers),
            str(data.questions)
        ]
        
        sheet.append_row(row)
        
        return {
            "success": True,
            "message": "Results saved to Google Sheets",
            "score": score
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/results")
async def get_all_results():
    """Получить все результаты из Google Sheets"""
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        
        # Сортируем по баллам
        sorted_records = sorted(records, key=lambda x: x.get('Score', 0), reverse=True)
        
        return {
            "total_users": len(records),
            "results": sorted_records
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/statistics")
async def get_statistics():
    """Получить статистику из Google Sheets"""  # ← ИСПРАВЛЕНО
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        
        if not records:
            return {"message": "No results yet"}
        
        total_users = len(records)
        total_score = sum(r.get('Score', 0) for r in records)
        avg_score = total_score / total_users if total_users > 0 else 0
        avg_time = sum(r.get('Time Spent (sec)', 0) for r in records) / total_users if total_users > 0 else 0
        
        return {
            "total_users": total_users,
            "average_score": round(avg_score, 2),
            "average_time_seconds": round(avg_time, 2),
            "max_score": 9,
            "completion_rate": f"{(avg_score / 9 * 100):.1f}%"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Инициализация при старте
@app.on_event("startup")
async def startup_event():
    init_sheet()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
