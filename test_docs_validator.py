import asyncio
import httpx
import json
import time
from typing import List, Dict


# Тест-кейсы с разными содержимыми .md файлов
TEST_CASES = [
    {
        "name": "Хорошая документация",
        "content": """# My Project

## Overview
This is a sample project demonstrating best practices.

## Architecture
The project consists of:
- Frontend (React)
- Backend (FastAPI)
- Database (PostgreSQL)

## Technologies
- Python 3.11
- React 18
- PostgreSQL 15
- Docker

## Installation
```bash
pip install -r requirements.txt
npm install
```

## Running the project
```bash
python main.py
npm start
```

## Environment Variables
- DATABASE_URL=postgresql://...
- API_KEY=your_key
"""
    },
    {
        "name": "Плохая документация (нет описания)",
        "content": """# Project

## Installation
pip install -r requirements.txt

## Run
python main.py
"""
    },
    {
        "name": "Документация без архитектуры",
        "content": """# My Project

## Overview
This project does something useful.

## Technologies
- Python
- FastAPI

## Installation
pip install requirements.txt

## Running
python main.py
"""
    },
    {
        "name": "Некорректный Markdown",
        "content": """# My Project
- Invalid markdown syntax
[broken link](missing)
- Another invalid item
"""
    },
    {
        "name": "Полная документация",
        "content": """# Awesome Project

## Overview
This is an awesome project that solves real-world problems.

## Architecture
```
├── src/
│   ├── api/
│   ├── services/
│   └── models/
├── tests/
└── docs/
```

The project follows a layered architecture with clear separation of concerns.

## Technologies
- Python 3.11
- FastAPI 0.100+
- SQLAlchemy 2.0
- PostgreSQL 15
- Redis 7.0
- Docker & Docker Compose

## Installation

### Prerequisites
- Python 3.11+
- Docker
- Docker Compose

### Setup
```bash
# Clone the repository
git clone https://github.com/user/project.git
cd project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your settings
```

## Running the Project

### Development
```bash
# Start PostgreSQL with Docker
docker-compose up -d postgres

# Run migrations
alembic upgrade head

# Start the server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
docker-compose up -d
```

## Configuration
See `.env.example` for all available configuration options.

## Troubleshooting
- Database connection issues: Check DATABASE_URL in .env
- Port already in use: Change PORT in .env
"""
    },
]


async def send_test_request(
    client: httpx.AsyncClient,
    test_case: Dict[str, str],
    session_id: str,
    index: int
) -> Dict:
    """Отправляет один тест-кейс на валидацию."""
    print(f"\n{'='*60}")
    print(f"Тест-кейс #{index + 1}: {test_case['name']}")
    print(f"{'='*60}")

    payload = {
        "model": "graph",
        "messages": [
            {
                "role": "user",
                "content": test_case["content"]
            }
        ],
        "stream": False,
        "session_id": f"{session_id}-test-{index}"
    }

    try:
        response = await client.post(
            "http://localhost:8000/v1/chat/completions",
            json=payload,
            timeout=300.0
        )
        response.raise_for_status()
        result = response.json()

        # Выводим результат
        if result.get("choices") and len(result["choices"]) > 0:
            content = result["choices"][0].get("message", {}).get("content", "")
            print(f"\nРезультат валидации:\n{content}")
            
            # Извлекаем trace_id для трейсинга
            trace_id = response.headers.get("X-Trace-Id")
            if trace_id:
                print(f"\nTrace ID: {trace_id}")
                print(f"Phoenix UI: http://localhost:6006")

        return {
            "name": test_case["name"],
            "success": True,
            "trace_id": response.headers.get("X-Trace-Id"),
            "content": result.get("choices", [{}])[0].get("message", {}).get("content", "")
        }

    except httpx.HTTPError as e:
        print(f"\n❌ Ошибка запроса: {e}")
        return {
            "name": test_case["name"],
            "success": False,
            "error": str(e)
        }


async def run_tests():
    """Запускает все тест-кейсы."""
    session_id = f"test-session-{int(time.time())}"
    
    print(f"Запуск тестов для DocsValidatorNode")
    print(f"Session ID: {session_id}")
    print(f"Всего тест-кейсов: {len(TEST_CASES)}")
    print(f"Сервер должен быть запущен на http://localhost:8000")
    print(f"Phoenix UI: http://localhost:6006")

    async with httpx.AsyncClient() as client:
        # Проверяем, что сервер доступен
        try:
            health_response = await client.get("http://localhost:8000/v1/models", timeout=5.0)
            print("✅ Сервер доступен")
        except httpx.HTTPError:
            print("❌ Сервер недоступен. Убедитесь, что сервер запущен на http://localhost:8000")
            return

        results = []
        
        for index, test_case in enumerate(TEST_CASES):
            result = await send_test_request(client, test_case, session_id, index)
            results.append(result)
            
            # Пауза между запросами для лучшего трейсинга
            if index < len(TEST_CASES) - 1:
                print(f"\n⏳ Пауза 1с перед следующим тестом...")
                await asyncio.sleep(1)

    # Итоговый отчет
    print(f"\n{'='*60}")
    print("ИТОГОВЫЙ ОТЧЕТ")
    print(f"{'='*60}")
    
    successful = sum(1 for r in results if r["success"])
    print(f"Успешно: {successful}/{len(results)}")
    
    print("\nДетали:")
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['name']}")
        if result.get("trace_id"):
            print(f"   Trace ID: {result['trace_id']}")
    
    # Сохраняем результаты в файл
    with open(f"test_results_{session_id}.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nРезультаты сохранены в: test_results_{session_id}.json")


if __name__ == "__main__":
    print("Запуск тестирования DocsValidatorNode...")
    print("Убедитесь, что:")
    print("1. Сервер запущен на http://localhost:8000")
    print("2. Phoenix UI доступен на http://localhost:6006")
    print("3. Ollama запущен и модель доступна")
    print()
    
    input("Нажмите Enter для продолжения")
    
    asyncio.run(run_tests())
