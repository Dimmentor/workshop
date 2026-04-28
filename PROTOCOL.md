# Workshop Orchestrator — протокол взаимодействия

Этот сервис предоставляет OpenAI-совместимый (по форме) чат-эндпоинт и проксирует параметры в Ollama / `langchain_ollama.ChatOllama`.

## Эндпоинты

### Chat Completions

- **Метод**: `POST`
- **Путь**: `/v1/chat/completions`
- **Content-Type**: `application/json`

### Models (для совместимости с OpenAI/OpenWebUI)

- **Метод**: `GET`
- **Путь**: `/v1/models`

## Запрос: `/v1/chat/completions`

### Минимальный запрос

```json
{
  "model": "qwen3:27b",
  "messages": [
    { "role": "system", "content": "Ты эксперт по C#. Отвечай кратко и только кодом." },
    { "role": "user", "content": "Как объединить два словаря?" }
  ],
  "stream": false
}
```

### Поля запроса (все поддерживаемые)

> Примечание: схема запроса настроена с `extra=allow`, то есть сервис **не отклоняет**
> дополнительные поля. Но гарантированно участвуют в обработке только поля, описанные ниже.

#### 1) Обязательные

- **model** *(string)*: имя модели Ollama (например `"qwen3:27b"`).
- **messages** *(array)*: массив сообщений (см. ниже).

#### 2) Управление ответом

- **stream** *(bool, default=false)*:
  - `false` — вернуть один JSON-ответ.
  - `true` — вернуть SSE поток (см. ниже).

#### 3) Сообщения (`messages[]`)

Каждый элемент `messages[]` — объект:
- **role** *(string)*: `"system" | "user" | "assistant" | "tool" | "function"`
- **content** *(any | null)*: обычно строка, но допускается любой JSON.
- **name** *(string | null)*: опционально.

> `messages[]` также допускает дополнительные поля (extra=allow).

### Сохранение контекста/сессии (один из идентификаторов)

Чтобы продолжать один и тот же контекст между запросами, клиент может передавать **один из**:
- `thread_id`
- `conversation_id`
- `chat_id`
- `session_id`

Если не передать ничего — сервис создаст новый id и вернёт его в ответе (`thread_id`/`conversation_id`).

## Параметры модели (Ollama / ChatOllama)

### Рекомендуемый способ: `options` (passthrough в Ollama)

Это основной способ для бенчмарка: вы присылаете ровно те параметры, которые хотите сравнивать.

```json
{
  "model": "qwen3:27b",
  "messages": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "..." }
  ],
  "stream": false,
  "options": {
    "temperature": 0.2,
    "num_ctx": 2048,
    "top_p": 0.9,
    "top_k": 40,
    "num_predict": 256,
    "seed": 123,
    "stop": ["</s>"]
  }
}
```

### Дополнительно: поля `ChatOllama` (все опциональные)

Сервис принимает (все optional, default `null`) параметры `ChatOllama` и связанные поля.

#### 1) OpenAI-like поля (для совместимости)

- **temperature** *(number | null)*: будет использовано как Ollama `options.temperature`, если не передан `options`.
- **top_p** *(number | null)*: будет использовано как Ollama `options.top_p`, если не передан `options`.
- **max_tokens** *(integer | null)*: будет использовано как Ollama `options.num_predict`, если:
  - `options` не передан, и
  - `num_predict` не передан.

#### 2) Параметры reasoning/формата/клиента (ChatOllama init/kwargs)

- **reasoning** *(boolean | string | null)*: режим thinking/reasoning (передаётся как `reasoning`).
- **validate_model_on_init** *(boolean | null)*: проверка наличия модели на Ollama при инициализации.
- **format** *(any | null)*: `"json"` или JSON-schema (dict) для structured output.
- **keep_alive** *(integer | string | null)*: keep-alive модели в Ollama.
- **base_url** *(string | null)*: URL Ollama (если нужно переопределить базовый).
- **client_kwargs** *(object | null)*: kwargs для httpx-клиента (заголовки и т.п.).
- **async_client_kwargs** *(object | null)*: доп. kwargs для async-клиента.
- **sync_client_kwargs** *(object | null)*: доп. kwargs для sync-клиента.

#### 3) “Option-поля” Ollama (если `options` НЕ передан)

Все поля ниже принимаются как top-level и (если не передан `options`) будут собраны в `options`:

- **mirostat** *(integer | null)*
- **mirostat_eta** *(number | null)*
- **mirostat_tau** *(number | null)*
- **num_ctx** *(integer | null)*
- **num_gpu** *(integer | null)*
- **num_thread** *(integer | null)*
- **num_predict** *(integer | null)*
- **repeat_last_n** *(integer | null)*
- **repeat_penalty** *(number | null)*
- **temperature** *(number | null)*
- **seed** *(integer | null)*
- **stop** *(array[string] | null)*
- **tfs_z** *(number | null)*
- **top_k** *(integer | null)*
- **top_p** *(number | null)*

#### 4) `options` (passthrough)

- **options** *(object | null)*: если передан — будет прокинут в Ollama “как есть” и имеет приоритет над пунктом (3).

Важно:
- Если **передан `options`**, он **имеет приоритет** над отдельными option-полями.

## Прочие поля запроса (служебные)

Эти поля не относятся к LLM-параметрам, но принимаются эндпоинтом:

- **thread_id** *(string | null)*: идентификатор диалога/состояния графа.
- **conversation_id** *(string | null)*: алиас `thread_id` (для совместимости).
- **chat_id** *(string | null)*: идентификатор чата (некоторые клиенты его присылают).
- **session_id** *(string | null)*: ещё один алиас/ключ сессии (если другие id не переданы).
- **branch_path** *(string | null)*: подсказка workspace/ветки (если клиент передаёт состояние).
- **context** *(object | null)*: произвольный контекст; поддерживается `context.branch_path`.

## Ответ: `stream=false` (обычный JSON)

- **HTTP 200**
- Полезная нагрузка находится в `choices[0].message.content`.
- Идентификаторы диалога: `thread_id` и `conversation_id` дублируют идентификатор потока/сессии на стороне сервиса.

Пример (упрощённо):

```json
{
  "id": "....",
  "object": "chat.completion",
  "created": 1710000000,
  "model": "qwen3:27b",
  "choices": [
    {
      "index": 0,
      "message": { "role": "assistant", "content": "..." },
      "finish_reason": "stop"
    }
  ],
  "usage": { "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0 },
  "thread_id": "...",
  "conversation_id": "..."
}
```

## Ответ: `stream=true` (SSE поток)

Если `stream=true`, сервер отвечает **SSE** (`Content-Type: text/event-stream`).

- В потоке приходят события в формате OpenAI-подобных чанков: `object = "chat.completion.chunk"`.
- Основной текст ответа приходит инкрементально в `choices[0].delta.content`.
- Завершение потока: строка `data: [DONE]`.

Практика на стороне клиента:
- открыть HTTP соединение и читать поток построчно;
- для каждой строки вида `data: {json}` — парсить JSON и добавлять `choices[0].delta.content` в буфер;
- при `data: [DONE]` — считать ответ завершённым.

## Как сервис обрабатывает запрос (кратко)

1. Валидирует JSON (Pydantic схема запроса).
2. Конвертирует `messages` в внутренний формат, строит `initial_state`.
3. Кладёт LLM override-параметры запроса в `state["_llm"]`.
4. Запускает LangGraph workflow (`workflow.ainvoke(...)` или `workflow.astream_events(...)` для streaming).
5. Возвращает финальный текст в OpenAI-подобном формате.

## Ограничение параллелизма и очередь (backpressure)

Чтобы результаты **не деградировали из-за конкурентной нагрузки**, на уровне API введён лимит параллелизма:

- По умолчанию **1 запрос одновременно на пару (model, base_url)**.
- Если запросов несколько, они **ожидают в очереди**.
- Для `stream=true` слот удерживается **до завершения SSE**, чтобы стримы не конкурировали.

Настройки (через env / `.env`):
- `LLM_MAX_CONCURRENT_REQUESTS` *(int, default=1)* — сколько одновременных запросов разрешено.
- `LLM_QUEUE_TIMEOUT_SECONDS` *(float | null, default=null)* — максимальное ожидание в очереди.
  - если задано и время вышло — сервер вернёт **HTTP 429**.
  - если `null` — ожидание без таймаута.

## Рекомендации для бенчмарка

- Для честного сравнения параметров держите `LLM_MAX_CONCURRENT_REQUESTS=1`.
- Если запросы могут идти минутами:
  - используйте `stream=true` для получения токенов/прогресса сразу,
  - либо увеличьте таймауты HTTP-клиента при `stream=false`.

