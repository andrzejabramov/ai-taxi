# Техническая спецификация: Сервис перевозки сотрудников

## 1. Обзор проекта

Сервис организации перевозок сотрудников легковым автотранспортом по заказам субъектов предпринимательской деятельности. Осуществляется на основании договора в письменной форме для нужд заказчика (согласно п. 2 ст. 20 ФЗ "Устав автомобильного транспорта и городского наземного электрического транспорта" № 259-ФЗ от 08.11.2007).

**Важно:** Данный сервис НЕ является сервисом такси. Перевозки осуществляются определённого круга лиц (сотрудников заказчика) по договору с субъектом предпрининимательской деятельности.

## 2. Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (nginx)                      │
│  - HTML/CSS/JS (vanilla, без фреймворков)                │
│  - Дашборд с картой и историей поездок                   │
│  - Чат с ИИ-агентом (текст + голос)                      │
└────────────────┬────────────────────────────────────────┘
                 │ HTTPS (443)
                 ▼
┌─────────────────────────────────────────────────────────┐
│              Nginx Reverse Proxy                         │
│  - SSL termination (Let's Encrypt)                       │
│  - Проксирование на backend (8002) и frontend (8003)     │
│  - Изоляция сервисов через Docker-сеть                   │
└────────────────┬────────────────────────────────────────┘
                 │ HTTP (внутренняя сеть)
                 ▼
┌─────────────────────────────────────────────────────────┐
│              Backend (FastAPI)                           │
│  - REST API для управления поездками                     │
│  - Интеграция с LLM (OpenRouter)                         │
│  - Интеграция с геосервисами (2GIS, Яндекс)              │
│  - Голосовой ввод (Yandex SpeechKit)                     │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│          PostgreSQL (хранимые процедуры)                 │
│  - Схема taxi с таблицами trips, routes, users           │
│  - Хранимые процедуры для бизнес-логики                  │
│  - Master-replica архитектура (готовность к масштаб.)    │
└─────────────────────────────────────────────────────────┘
```

## 3. Frontend

### Технологии

- HTML5 + CSS3 (BEM + CSS Modules)
- Vanilla JavaScript (ES6+)
- Leaflet.js для карт
- Web Speech API + Yandex SpeechKit для голоса

### Структура

```
frontend/
├── index.html              # Главная страница
├── styles/
│   ├── main.css           # Основные стили
│   ├── dashboard.css      # Стили дашборда
│   └── chat.css           # Стили чата
├── app.js                 # Инициализация приложения
├── dashboard.js           # Логика дашборда
├── map.js                 # Логика карты
├── chat.js                # Логика чата с LLM
├── speech.js              # Модуль голосового ввода
└── trips.js               # Логика работы с поездками
```

### Компоненты

1. **Дашборд** — два блока: карта + превью последних поездок
2. **Карта** — полноэкранная карта с маршрутами
3. **Таблица поездок** — история с фильтрацией
4. **Детали поездки** — карточка с треком и информацией
5. **Чат** — диалог с ИИ-агентом (справа внизу)
6. **Микрофон** — кнопка голосового ввода в чате

### Голосовой ввод

- **Web Speech API** — для браузеров с поддержкой (Chrome, Edge)
- **Yandex SpeechKit** — fallback для других браузеров
- **Режимы**:
  - Голосовой ввод адреса → переход на карту → поиск
  - Голосовой ввод команды → отправка в чат → ответ LLM

## 4. Backend

### Технологии

- FastAPI (Python 3.11+)
- asyncpg для работы с PostgreSQL
- Pydantic для валидации данных
- httpx для внешних API

### Структура

```
backend/
├── src/
│   ├── main.py            # Точка входа, lifespan
│   ├── settings.py        # Конфигурация (pydantic-settings)
│   ├── api/
│   │   ├── v1/
│   │   │   ├── trips.py   # Эндпоинты поездок
│   │   │   ├── routes.py  # Эндпоинты маршрутов
│   │   │   └── chat.py    # Эндпоинты чата
│   ├── db/
│   │   ├── pools.py       # Пулы подключений к БД
│   │   └── queries.py     # SQL-запросы
│   ├── services/
│   │   ├── llm.py         # Интеграция с OpenRouter
│   │   ├── geocoding.py   # 2GIS / Яндекс Геокодер
│   │   └── speech.py      # Yandex SpeechKit
│   └── models/
│       ├── trip.py        # Pydantic-модели поездок
│       └── chat.py        # Pydantic-модели чата
├── Dockerfile
└── requirements.txt
```

### API Endpoints

#### Поездки

- `GET /api/v1/trips/` — список поездок (с пагинацией)
- `GET /api/v1/trips/{id}` — детали поездки
- `POST /api/v1/trips/order` — создать заказ (расчёт логистики)
- `PATCH /api/v1/trips/{id}/status` — обновить статус

#### Маршруты

- `GET /api/v1/routes/{trip_id}` — геометрия маршрута
- `POST /api/v1/routes/calculate` — расчёт маршрута

#### Чат

- `POST /api/v1/chat/message` — отправить сообщение в LLM
- `GET /api/v1/chat/history` — история диалога

#### Голос

- `POST /api/v1/speech/transcribe` — транскрибация аудио

## 5. База данных

### Схема

```sql
-- Схема taxi
CREATE SCHEMA taxi;

-- Таблица поездок
CREATE TABLE taxi.trips (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    start_address TEXT,
    end_address TEXT,
    start_lat DECIMAL(10, 8),
    start_lon DECIMAL(11, 8),
    end_lat DECIMAL(10, 8),
    end_lon DECIMAL(11, 8),
    distance_m INTEGER,
    duration_s INTEGER,
    status VARCHAR(50) DEFAULT 'created',
    tariff VARCHAR(50),
    price DECIMAL(10, 2),
    car_model VARCHAR(100),
    driver_name VARCHAR(255),
    rating INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица маршрутов (геометрия)
CREATE TABLE taxi.routes (
    id SERIAL PRIMARY KEY,
    trip_id INTEGER REFERENCES taxi.trips(id),
    geometry JSONB,  -- Массив координат [[lat, lon], ...]
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица пользователей (заказчиков)
CREATE TABLE taxi.users (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(255) UNIQUE,
    company_name VARCHAR(255),
    contract_number VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Хранимые процедуры

**Почему хранимки, а не ORM?**

- Производительность: сложная логика выполняется на стороне БД
- Безопасность: бизнес-логика инкапсулирована в БД
- Транзакционность: атомарные операции
- Масштабируемость: легко добавить master-replica

**Примеры процедур:**

```sql
-- Создание поездки с расчётом маршрута
CREATE OR REPLACE FUNCTION taxi.create_trip(
    p_user_id VARCHAR,
    p_start_lat DECIMAL,
    p_start_lon DECIMAL,
    p_end_lat DECIMAL,
    p_end_lon DECIMAL,
    p_end_address TEXT,
    p_tariff VARCHAR
) RETURNS INTEGER AS $$
DECLARE
    v_trip_id INTEGER;
BEGIN
    INSERT INTO taxi.trips (user_id, start_lat, start_lon, end_lat, end_lon, end_address, tariff)
    VALUES (p_user_id, p_start_lat, p_start_lon, p_end_lat, p_end_lon, p_end_address, p_tariff)
    RETURNING id INTO v_trip_id;

    -- Вызов внешнего API для расчёта маршрута
    -- (реализовано в backend, здесь только вставка в routes)

    RETURN v_trip_id;
END;
$$ LANGUAGE plpgsql;

-- Обновление статуса поездки
CREATE OR REPLACE FUNCTION taxi.update_trip_status(
    p_trip_id INTEGER,
    p_status VARCHAR
) RETURNS VOID AS $$
BEGIN
    UPDATE taxi.trips
    SET status = p_status, updated_at = NOW()
    WHERE id = p_trip_id;
END;
$$ LANGUAGE plpgsql;
```

## 6. Модели данных

### Pydantic-модели (backend/src/models/)

```python
# trip.py
class TripCreate(BaseModel):
    user_id: str
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    end_address: str
    tariff: str

class TripResponse(BaseModel):
    id: int
    user_id: str
    start_address: str
    end_address: str
    distance_m: int
    duration_s: int
    status: str
    tariff: str
    price: Optional[float]
    car_model: Optional[str]
    driver_name: Optional[str]
    rating: Optional[int]
    created_at: datetime

# chat.py
class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime
```

## 7. База знаний

### Структура

```
knowledge_base/
├── architecture_chats/    # ChromaDB коллекция
│   ├── metadata.json      # Метаданные
│   └── vectors/           # Векторные представления
├── faq.json              # Часто задаваемые вопросы
├── tariff_guide.json     # Тарифы и условия
└── legal_docs/           # Юридические документы
    ├── contract_template.md
    └── regulations.md
```

### Использование

- **ChromaDB** — векторное хранилище для семантического поиска
- **Контекст для LLM** — база знаний передаётся в промпт для точных ответов
- **Обновление** — можно обновлять без пересборки приложения

## 8. Голосовой ввод

### Архитектура

```
Пользователь → Микрофон → Web Speech API / Yandex SpeechKit
                                    ↓
                            Транскрибация текста
                                    ↓
                    ┌───────────────┴───────────────┐
                    ↓                               ↓
              Это адрес?                      Это команда?
                    ↓                               ↓
            Переход на карту              Отправка в чат
            Поиск адреса                  Ответ LLM
```

### Реализация

```javascript
// speech.js
class SpeechModule {
  static init(buttonId, inputId) {
    // Инициализация Web Speech API
    this.recognition = new (
      window.SpeechRecognition || window.webkitSpeechRecognition
    )();
    this.recognition.lang = "ru-RU";
    this.recognition.continuous = false;

    // Обработка результатов
    this.recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      this.processResult(transcript);
    };
  }

  static processResult(text) {
    // Определение: адрес или команда
    if (this.isAddress(text)) {
      window.dispatchEvent(
        new CustomEvent("speech:result", {
          detail: { text, isAddress: true },
        }),
      );
    } else {
      window.dispatchEvent(
        new CustomEvent("speech:result", {
          detail: { text, isAddress: false },
        }),
      );
    }
  }
}
```

## 9. Инфраструктура

### Nginx конфигурация

```nginx
server {
    listen 443 ssl;
    server_name car.atotx.su;

    # SSL сертификаты (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/car.atotx.su/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/car.atotx.su/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Frontend
    location / {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API
    location /api/ {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}

server {
    listen 80;
    server_name car.atotx.su;
    return 301 https://$host$request_uri;
}
```

### SSL (Let's Encrypt)

- **Certbot** — автоматическое получение и обновление сертификатов
- **Команда**: `sudo certbot --nginx -d car.atotx.su`
- **Автообновление**: cron job каждые 90 дней

### Docker-сеть

```yaml
networks:
  taxi-network:
    name: taxi-network
    driver: bridge
```

Все сервисы (postgres, backend, frontend) в изолированной сети. Порты backend (8002) и postgres (5433) доступны только на localhost.

## 10. Деплой

### Локальная разработка

```bash
docker compose up -d --build
```

### Production (Яндекс Облако)

```bash
# На ВМ
cd /mnt/data/car-agent
git pull
docker compose down
docker compose up -d --build
```

### Мониторинг

```bash
# Логи
docker logs taxi-backend --tail=50
docker logs taxi-frontend --tail=20

# Статус
docker ps
ss -tlnp | grep -E "8002|8003"
```

## 11. Безопасность

- **CORS**: разрешены только запросы с `https://car.atotx.su`
- **HTTPS**: обязательный редирект с HTTP на HTTPS
- **Секреты**: хранятся в `.env` файлах (не в git)
- **БД**: доступна только на localhost (127.0.0.1:5433)
- **API ключи**: передаются через environment variables

## 12. Масштабирование

### Горизонтальное

- Добавить реплики backend (load balancer)
- PostgreSQL master-replica
- Redis для кэширования

### Вертикальное

- Увеличить ресурсы ВМ (CPU, RAM)
- Оптимизировать запросы к БД
- CDN для статики

## 13. Контакты

- **Репозиторий**: https://github.com/andrzejabramov/ai-taxi
- **Продакшн**: https://car.atotx.su
- **Разработчик**: Andrej Abramov
  EOF

````

## 2. commercial-proposal.md

```bash
cat > commercial-proposal.md << 'EOF'
# Коммерческое предложение: Сервис организации перевозок сотрудников

## 1. О сервисе

Мы предлагаем инновационный сервис организации перевозок сотрудников легковым автотранспортом по заказам субъектов предпринимательской деятельности.

**Важно:** Данный сервис НЕ является сервисом такси. Перевозки осуществляются в соответствии с п. 2 ст. 20 Федерального закона от 08.11.2007 № 259-ФЗ "Устав автомобильного транспорта и городского наземного электрического транспорта":

> "Перевозка пассажиров и багажа по заказам может осуществляться легковым такси, а также **легковым автомобилем, принадлежащего индивидуальному предпринимателю или юридическому лицу, при условии заключения с субъектом предпринимательской деятельности договора в письменной форме на перевозку сотрудников этого субъекта предпринимательской деятельности для нужд заказчика**."

## 2. Преимущества

### Для бизнеса
✅ **Легальность** — полное соответствие законодательству РФ
✅ **Экономия** — оптимизация логистики ИИ-агентом
✅ **Контроль** — прозрачная история всех поездок
✅ **Безналичный расчёт** — оплата с банковского счёта заказчика
✅ **Договор** — официальное оформление отношений

### Технологии
✅ **ИИ-агент** — автоматический расчёт оптимальных маршрутов
✅ **Голосовое управление** — можно набрать текст или проговорить команду
✅ **Реальное время** — учёт загруженности транспортной сети
✅ **По всей России** — перевозки по всей территории РФ

## 3. Как это работает

### Шаг 1: Заключение договора
С субъектом предпринимательской деятельности заключается договор в письменной форме на перевозку сотрудников для нужд заказчика.

### Шаг 2: Оформление заказа через ИИ-агента
Заказ создаётся через приложение ИИ-агент:
- **Голосом**: "Поездка из офиса на завод"
- **Текстом**: ввод адреса в чате
- **На карте**: клик по точке на карте

### Шаг 3: Расчёт логистики
ИИ-агент автоматически:
- Рассчитывает оптимальный маршрут
- Учитывает загруженность транспортной сети
- Определяет расстояние и время в пути
- Формирует стоимость поездки

### Шаг 4: Перевозка
Водитель выполняет перевозку сотрудника заказчика по указанному маршруту.

### Шаг 5: Отчётность
Все поездки фиксируются в системе с полной историей, геометрией маршрута и стоимостью.

## 4. Тарифы

| Тариф | Описание | Стоимость |
|-------|----------|-----------|
| Эконом | Легковой автомобиль эконом-класса | *заполнить* |
| Комфорт | Легковой автомобиль комфорт-класса | *заполнить* |
| Бизнес | Легковой автомобиль бизнес-класса | *заполнить* |
| Минивэн | Автомобиль повышенной вместимости | *заполнить* |
| Грузовой | Легковой автомобиль с грузовым отсеком | *заполнить* |
| Индивидуальный | Специальные условия по договору | *заполнить* |

*Детальные тарифы предоставляются после заключения договора.*

## 5. Оплата

Оплата производится **безналичным расчётом** с банковского счёта заказчика на основании выставленного счёта и акта выполненных работ.

## 6. География обслуживания

Перевозки осуществляются **по всей территории Российской Федерации**.

## 7. Попробуйте прямо сейчас!

Откройте приложение и создайте первый заказ:

👉 **[https://car.atotx.su](https://car.atotx.su)**

*Доступ предоставляется после заключения договора.*

## 8. Контакты

**Разработчик и техническая поддержка:**
Andrej Abramov
Email: *указать email*
Телефон: *указать телефон*

**Юридический адрес:**
*указать адрес*

---

*Данное коммерческое предложение не является публичной офертой. Условия сотрудничества определяются индивидуальным договором.*
EOF
````

## Коммит и пуш

```bash
git add specification.md commercial-proposal.md
git commit -m "docs: добавить техническую спецификацию и коммерческое предложение"
git push
```

## Что получилось

✅ **specification.md** — полная техническая документация:

- Архитектура (frontend, backend, БД)
- Хранимые процедуры вместо ORM
- Голосовой ввод (Web Speech API + Yandex SpeechKit)
- Nginx + SSL конфигурация
- Модели данных
- База знаний (ChromaDB)

✅ **commercial-proposal.md** — коммерческое предложение:

- Цитата из закона (не такси!)
- Преимущества для бизнеса
- Как работает ИИ-агент
- Таблица тарифов (3 столбца, 6 строк — заполнишь позже)
- Ссылка на приложение: https://car.atotx.su
- Безналичный расчёт
- География: вся РФ
