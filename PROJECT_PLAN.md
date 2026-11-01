# PROJECT VERSE — технический проектный план

**Документ:** архитектура, модель данных, миграции, этапы, интеграции, ограничения и тестирование
**Основание:** `SPEC.md` (1135 строк, VERSE ALTERNATIVE / ТЗ на настольное приложение для битмейкера)
**Референс:** Verse by 1vremennobeats 5.9.0
**Дата подготовки:** 2026-11-01
**Статус кода:** этапы 0 (Bootstrap) и 1 (CRM Core) реализованы. Обновления по факту — в разделах 5 и 6.

---

## Содержание

1. [Текущее состояние проекта](#1-текущее-состояние-проекта)
2. [Архитектура приложения](#2-архитектура-приложения)
3. [Структура директорий](#3-структура-директорий)
4. [Модель данных PostgreSQL](#4-модель-данных-postgresql)
5. [Список миграций](#5-список-миграций)
6. [План реализации по этапам](#6-план-реализации-по-этапам)
7. [Внешние API и интеграции](#7-внешние-api-и-интеграции)
8. [Технические ограничения и неопределённости](#8-технические-ограничения-и-неопределённости)
9. [План тестирования](#9-план-тестирования)
10. [Приложения](#10-приложения)

---

# 1. Текущее состояние проекта

## 1.1. Что есть в репозитории

Каталог `/Users/ilap/Desktop/projectVerse` содержит **только**:

| Файл | Размер | Назначение |
|---|---|---|
| `SPEC.md` | 45 770 байт | Техническое задание |
| `.DS_Store` | 6 148 байт | Служебный файл macOS, в репозитории не нужен |
| `PROJECT_PLAN.md` | этот файл | Проектная документация |

- Git инициализирован, ветка `main`, **коммитов нет** (`fatal: your current branch 'main' does not have any commits yet`).
- Исходного кода, конфигурации, зависимостей, миграций, тестов — **нет**.
- `.gitignore` отсутствует.

**Вывод:** проект разрабатывается с нуля. Любые существующие модули, которые «нельзя переписывать» (правило SPEC §24), отсутствуют — ограничение не применяется, но и оправдания для дублирующих архитектур нет.

## 1.2. Проверенное состояние среды

Проверено командами `sw_vers`, `uname`, `sysctl`, `which`, `pip install --dry-run`, `curl` к PyPI и документации вендоров.

| Параметр | Значение | Следствие для плана |
|---|---|---|
| ОС | macOS 15.7.9 (24G830), arm64 | PySide6 6.12 требует macOS ≥ 14 — совместимо |
| RAM | 8 ГБ | Один процесс, без тяжёлых фоновых сервисов |
| Диск | 228 ГБ, свободно ~65 ГБ | Достаточно для Docker-образа PostgreSQL и зависимостей |
| Python | **3.14.4** (`/Library/Frameworks/Python.framework`), других версий нет | Зависимости проверены именно на 3.14 (см. ниже) |
| `pip` | 26.0.1 | Установка в venv |
| Homebrew | 6.0.17 | Резервный способ поставить PostgreSQL 17 / Python 3.12 |
| Docker CLI | 29.7.2, **демон не запущен** | PostgreSQL поднимается после старта Docker Desktop |
| PostgreSQL локально | отсутствует | Нельзя рассчитывать на системный `psql` |
| FFmpeg | отсутствует | Нужен на этапе 7 (аудио) |
| Node.js | v26.3.1 | Проекту не нужен |
| Keychain CLI | `/usr/bin/security` доступен | Секреты можно хранить в Keychain |
| Xcode CLT | `/Library/Developer/CommandLineTools` | Компиляция колёс при необходимости |
| Locale | `LANG=""`, `LC_CTYPE=C` | Обязательно явно задавать локаль для сортировки кириллицы и поиска |
| Часовой пояс | `Asia/Yekaterinburg` (+05) | В БД хранить UTC, отображать локально |

**Проверка разрешимости зависимостей** (`python3 -m pip install --dry-run --only-binary=:all:`):

```
PySide6 6.12.0, PySide6_Essentials 6.12.0, shiboken6 6.12.0
SQLAlchemy 2.1.6, alembic 1.20.1, psycopg 3.3.6, psycopg-binary 3.3.6
pydantic 2.14.2, pydantic-settings 2.16.2, pydantic_core 2.50.2
httpx 0.28.1, respx 0.23.1, keyring 25.7.0
pytest 9.2.0, pytest-asyncio 1.4.1, pytest-qt 4.5.0
```

Разрешение прошло без сборки из исходников — под macOS arm64 доступны бинарные колёса (`cp314`, PySide6 — `cp310-abi3-macosx_14_0_universal2`).

**Важно:** полный `PySide6` тянет `PySide6-Addons`, `PySide6-WebEngine`, `PySide6-Pdf` (сотни мегабайт). Для приложения достаточно `PySide6-Essentials` (QtCore/QtGui/QtWidgets/QtNetwork/QtSql). В план закладывается **`PySide6-Essentials`**.

## 1.3. Что уже проверено по внешним API

Кратко (детали — в разделе 7):

- **Spotify**: часть возможностей, на которые опирается SPEC §5, закрыта для новых приложений с 27.11.2024; «ежемесячные слушатели» в API отсутствуют.
- **Instagram**: инициировать переписку через API нельзя, только отвечать в окне ~24 ч; публичного поиска пользователей нет.
- **WhatsApp Cloud API**: платформа существует и работоспособна как продукт Meta, но требует бизнес-верификации.
- **DeepSeek API**: `deepseek-flash` поддерживает изображения (Vision) — анализ скриншотов технически возможен.
- **Discord, iMessage, macOS Contacts, аудиосходство, Instagram business discovery** — не подтверждены, вынесены в спайки.

## 1.4. Чем этот план отличается от SPEC

SPEC задаёт требования; здесь они превращаются в решения. Три места, где план осознанно уточняет ТЗ (все — с обоснованием, см. разделы 2 и 6):

1. **Этап 3 «Кампании» совмещён с первым реальным каналом (email).** Без канала кампании были бы «кнопкой без функции», что прямо запрещено SPEC §23.
2. **Instagram Discovery проектируется как import-centric** до подтверждения доступных источников данных.
3. **Модуль Beat Placements не обещает автоматический обход стримингов** — публичного API «где использован мой бит» не существует; сначала спайк, потом формулировка реальной функции.

---

# 2. Архитектура приложения

## 2.1. Общая форма

Настольное приложение, **один процесс**, слоистая архитектура (layered monolith) без микросервисов и без сетевого сервера. Единственная точка правды — локальный PostgreSQL.

```
┌──────────────────────────────────────────────────────────────┐
│  UI (PySide6, GUI-поток)                                      │
│  MainWindow · Views · Widgets · QAbstractTableModel           │
│  Никакого I/O, никакого SQL                                   │
└───────────────▲──────────────────────────────┬───────────────┘
                │ сигналы / Future             │ команды
┌───────────────┴──────────────────────────────▼───────────────┐
│  Runtime (отдельный поток с asyncio event loop)               │
│  submit(coro) → concurrent.futures.Future                     │
│  реестр задач, отмена, таймауты, повторные попытки            │
└───────────────▲──────────────────────────────┬───────────────┘
                │                              │
┌───────────────┴──────────────┐  ┌────────────▼───────────────┐
│  Services (use-cases)        │  │  Jobs / Scheduler           │
│  contacts, deals, campaigns, │  │  периодический тик,          │
│  discovery, automations…     │  │  пропущенные запуски         │
└───────────────▲──────────────┘  └────────────┬───────────────┘
                │                              │
┌───────────────┴──────────────┐  ┌────────────▼───────────────┐
│  Repositories + Domain       │  │  Adapters (внешний мир)     │
│  SQLAlchemy 2.x async        │  │  email, instagram, spotify, │
│  PostgreSQL (psycopg 3)      │  │  whatsapp, discord, ai…     │
└──────────────────────────────┘  └────────────────────────────┘
```

**Жёсткое правило:** пакет `verse.core` (db, domain, services, adapters, jobs) **не импортирует PySide6**. Это даёт headless-тестирование, возможность запускать сценарии из CLI/Telegram-бота и исключает «логику в виджетах» — главную причину появления фиктивных интерфейсов.

## 2.2. Принятые архитектурные решения (ADR)

### ADR-1. Qt-независимое ядро
**Решение:** вся бизнес-логика — в `verse.core`; UI — тонкий слой.
**Причина:** тестируемость, повторное использование из Telegram-бота и планировщика, соблюдение SPEC §21 (тесты без GUI).
**Цена:** необходимость явно описывать DTO между UI и ядром (Pydantic-схемы в `domain/dto`).

### ADR-2. asyncio в выделенном потоке, без `qasync`
**Решение:** один `asyncio` event loop живёт в отдельном потоке (`Runtime`). GUI-поток вызывает `runtime.submit(coro) -> Future` и получает результат через механизм, который перебрасывает вызов в поток Qt (`QMetaObject.invokeMethod` / сигнал-мост).
**Причина:** asyncio есть в стеке SPEC; `qasync` добавляет зависимость и хрупкость при завершении приложения.
**Правило:** ни одна корутина не трогает виджеты; ни один виджет не ждёт сеть.

### ADR-3. SQLAlchemy 2.x async + psycopg 3
**Решение:** рантайм использует `create_async_engine("postgresql+psycopg://…")`; Alembic использует синхронный URL того же драйвера.
**Причина:** один драйвер на оба режима, нативные async-сессии, отсутствие `to_thread`-мостов.
**Правило:** сессия = единица работы (одна команда/один шаг задания). Долгоживущих сессий и «сессии в ViewModel» нет.

### ADR-4. Один PostgreSQL, никаких альтернативных хранилищ
**Решение:** все бизнес-данные — в PostgreSQL. SQLite не используется даже в тестах.
**Причина:** SPEC §1 (единая БД), §19; PG-специфика (partial unique index, `tsvector`, `jsonb`, `FOR UPDATE`) — часть модели данных.
**Следствие:** тесты интеграции требуют живой PostgreSQL; при недоступной БД тесты **падают**, а не пропускаются молча.

### ADR-5. Секреты только в Keychain
**Решение:** таблица `integration_credentials` хранит `keychain_ref` (имя записи) и метаданные, но не секрет. В логи и `audit_log` секреты не попадают — есть фильтр редактирования.
**Причина:** SPEC §2, §17, §18.

### ADR-6. Идемпотентность — свойством схемы
**Решение:** дубликаты предотвращаются уникальными индексами, а не только проверками в коде:

| Что защищаем | Механизм |
|---|---|
| Повторно найденный профиль | `artist_profiles UNIQUE (platform, platform_id)` |
| Повторный импорт контакта | `contact_channels UNIQUE (channel_type, normalized_value)` (partial) |
| Повторная отправка в кампании | `message_attempts.idempotency_key UNIQUE` |
| Повторная обработка события автоматизации | `automation_events.dedupe_key UNIQUE` |
| Повторный запуск задания по расписанию | `task_runs UNIQUE (scheduled_task_id, planned_at)` |
| Повторный результат discovery | `discovery_results UNIQUE (job_id, profile_id)` |

**Причина:** SPEC §4.5, §7.4, §9.4, §20 («защита от дубликатов»).

### ADR-7. Честный интерфейс
**Решение:** раздел навигации появляется только тогда, когда за ним есть работающая функция. Нереализованные модули в навигации **скрыты**; есть экран «Roadmap» со списком запланированных модулей и их статусом.
**Причина:** SPEC §1 («не создавать фиктивные функции»), §23.
**Следствие:** в этапе 1 в сайдбаре присутствуют Dashboard, CRM, Logs, Settings, Roadmap — остальное добавляется по мере готовности.

### ADR-8. Изоляция сбоев по каналам
**Решение:** ошибка адаптера фиксируется на уровне получателя и попытки (`message_attempts.error_*`), кампания продолжает обрабатывать остальных; ошибка одного канала не блокирует CRM.
**Причина:** SPEC §20.

### ADR-9. Время и часовые пояса
**Решение:** в БД — `timestamptz` (UTC); у `scheduled_tasks` — колонка `timezone` (IANA); расчёт «следующего запуска» — в зоне задачи; пропущенные запуски записываются как `missed`, никогда как `succeeded`.
**Причина:** SPEC §11 («если компьютер выключен, приложение не должно делать вид, что задача выполнилась»).

### ADR-10. Мягкое удаление по умолчанию
**Решение:** `contacts`, `campaigns`, `beats`, `artist_profiles` имеют `deleted_at`. Финальное удаление — отдельное явное действие с подтверждением, каскады описаны в модели.
**Причина:** SPEC §6.5 (корзина, восстановление), §18 (резервное копирование), §24 («не удалять пользовательские данные»).

## 2.3. Потоки данных (три главных сценария)

**A. Пользователь создаёт контакт вручную**
`View` → `Runtime.submit(ContactService.create(dto))` → валидация Pydantic → репозиторий в транзакции → при конфликте уникальности канала `DuplicateChannelError` → UI показывает карточку существующего контакта с предложением ручного слияния → запись в `audit_log`.

**B. Кампания отправляет сообщение**
`CampaignService.start()` → задача в реестре Runtime → выборка порции получателей (`FOR UPDATE SKIP LOCKED`) → `Adapter.send_message()` → запись `message_attempts` со своим `idempotency_key` → при повторном запуске попытка с тем же ключом не создаётся → статус `accepted` не выдаётся за `delivered` (см. SPEC §7.5) → при сетевой ошибке backoff и счётчик попыток.

**C. Планировщик и пропущенные запуски**
`Scheduler` тикает раз в 30 с → выбирает `scheduled_tasks` с `next_run_at <= now()` → для каждого `planned_at` создаёт `task_runs` (уникальность по паре) → при старте приложения все окна, которые прошли во время простоя, создаются как `missed` с `planned_at` → пользователь видит их на экране Schedule и решает, добивать или пропустить.

## 2.4. Технологические компоненты

| Слой | Технология | Роль |
|---|---|---|
| UI | PySide6-Essentials 6.12 | Окна, таблицы, формы, навигация |
| Модели таблиц | `QAbstractTableModel` + серверная пагинация | Списки без загрузки всех строк в память |
| Рантайм | `asyncio` (поток) + `concurrent.futures` | Фоновые операции, отмена |
| БД | PostgreSQL 17 (Docker) | Единое хранилище |
| ORM | SQLAlchemy 2.1 (async) | Модели, репозитории, транзакции |
| Миграции | Alembic 1.20 | Версионирование схемы |
| Валидация | Pydantic 2.14 + pydantic-settings | DTO, конфигурация |
| HTTP | httpx (async) | Все внешние вызовы |
| Секреты | keyring (macOS Keychain) | Токены и пароли |
| Логи | stdlib logging + JSON-форматтер + фильтр редактирования | Диагностика |
| Тесты | pytest, pytest-asyncio, pytest-qt, respx | См. раздел 9 |
| Аудио (позже) | FFmpeg, Chromaprint | Этап 7 |

## 2.5. Что приложение сознательно не делает

- Не содержит встроенного веб-сервера и не открывает порты в интернет (Telegram — long polling).
- Не хранит секреты в БД и в файлах конфигурации.
- Не обходит CAPTCHA, авторизацию и ограничения платформ (SPEC §4.8, §8).
- Не считает нажатие кнопки «Отправить» фактом доставки.
- Не показывает «демонстрационные» данные в рабочем интерфейсе.

---

# 3. Структура директорий

```
projectVerse/
├── SPEC.md                     # ТЗ (не изменяется)
├── PROJECT_PLAN.md             # этот документ
├── README.md                   # быстрый старт: 5 команд до запуска
├── .gitignore                  # .venv, __pycache__, .env, data/, *.db
├── .env.example                # шаблон переменных окружения
├── pyproject.toml              # зависимости (pinned), настройки pytest/ruff
├── docker-compose.yml          # postgres:17, порт 5433, volume verse_pgdata
├── Makefile                    # db-up, db-down, migrate, seed, run, test
├── alembic.ini
│
├── src/verse/
│   ├── __init__.py
│   ├── __main__.py             # python -m verse → app.main()
│   ├── app.py                  # composition root: config → engine → runtime → MainWindow
│   ├── config.py               # Settings (pydantic-settings, .env)
│   ├── runtime.py              # asyncio loop в потоке, submit(), shutdown(), реестр задач
│   ├── errors.py               # иерархия доменных исключений
│   ├── clock.py                # Clock-протокол (инъекция времени для тестов)
│   │
│   ├── db/
│   │   ├── base.py             # DeclarativeBase, naming_convention, TimestampMixin, UuidPk
│   │   ├── session.py          # create_async_engine, async_sessionmaker, unit_of_work()
│   │   └── models/
│   │       ├── crm.py          # contacts, channels, statuses, notes, reminders, interactions
│   │       ├── money.py        # deals, payments, deal_items
│   │       ├── campaigns.py    # templates, variants, campaigns, recipients, attempts, follow-ups
│   │       ├── automations.py  # automations, runs, events, scheduled_tasks, task_runs
│   │       ├── discovery.py    # sources, jobs, cursors, profiles, results, library
│   │       ├── beats.py        # beats, packs, series, placements
│   │       ├── integrations.py # connected_accounts, credentials, telegram users
│   │       ├── ai.py           # conversations, messages, actions
│   │       └── system.py       # app_settings, audit_log, backups, data_transfers
│   │
│   ├── domain/
│   │   ├── enums.py            # ChannelType, CampaignState, AttemptState…
│   │   ├── dto.py              # Pydantic-схемы обмена UI ↔ ядро
│   │   ├── normalize.py        # нормализация телефонов/хэндлов/email
│   │   ├── templating.py       # {Name}, {Username} + чистка «висящей» пунктуации
│   │   ├── money.py            # Decimal-арифметика, запрет смешивания валют
│   │   └── merge.py            # правила слияния контактов
│   │
│   ├── services/
│   │   ├── contacts.py, channels.py, statuses.py, deals.py, interactions.py
│   │   ├── transfer.py         # импорт/экспорт CSV/XLSX/TXT + маппинг колонок
│   │   ├── campaigns.py, templates.py, followups.py
│   │   ├── discovery.py, library.py
│   │   ├── automations.py, beatseries.py, schedule.py
│   │   ├── beats.py, placements.py
│   │   ├── ai.py, telegram.py, backup.py, stats.py
│   │
│   ├── adapters/
│   │   ├── base.py             # ChannelAdapter (Protocol) + AdapterResult + capabilities
│   │   ├── email_smtp.py       # SMTP + IMAP, DSN-разбор
│   │   ├── imessage_osascript.py
│   │   ├── whatsapp_cloud.py
│   │   ├── discord_bot.py
│   │   ├── instagram_graph.py
│   │   ├── spotify_api.py
│   │   ├── telegram_bot.py
│   │   ├── ai_llm.py           # DeepSeek (OpenAI-совместимый)
│   │   └── audio_fingerprint.py
│   │
│   ├── jobs/
│   │   ├── scheduler.py        # тик, misfire-политики, часовые пояса
│   │   ├── retry.py            # backoff, лимиты, отмена
│   │   └── progress.py         # курсоры, пауза/резюме
│   │
│   ├── security/
│   │   ├── keychain.py         # keyring-обёртка, единая точка доступа
│   │   └── redaction.py        # фильтр логов: токены, пароли, телефоны
│   │
│   └── ui/
│       ├── main_window.py      # сайдбар + QStackedWidget + статус-бар
│       ├── bridge.py           # Future → Qt-сигнал (маршалинг в GUI-поток)
│       ├── theme.py
│       ├── views/
│       │   ├── dashboard.py, crm.py, contact_card.py, campaigns.py,
│       │   ├── discovery_ig.py, discovery_sp.py, library.py,
│       │   ├── automations.py, schedule.py, beats.py, placements.py,
│       │   ├── ai.py, stats.py, logs.py, settings.py, roadmap.py
│       └── widgets/
│           ├── data_table.py   # QAbstractTableModel + пагинация + сортировка
│           ├── filter_bar.py, badges.py, toast.py, empty_state.py,
│           └── import_wizard.py, merge_dialog.py
│
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/               # см. раздел 5
│
├── tests/
│   ├── conftest.py             # engine, тестовая БД, фабрики, fake-clock
│   ├── factories.py
│   ├── unit/                   # чистая логика
│   ├── integration/            # репозитории и сервисы на реальном PG
│   ├── adapters/               # контракт адаптеров + respx
│   ├── migrations/             # upgrade/downgrade
│   └── ui/                     # pytest-qt, offscreen
│
├── docs/
│   ├── ACCEPTANCE.md           # ручные чек-листы по этапам
│   ├── SPIKES.md               # журнал технических проверок
│   └── DECISIONS.md            # короткие ADR по мере роста проекта
│
└── data/                       # runtime-данные вне репозитория (в .gitignore)
    ├── exports/
    ├── backups/
    └── logs/
```

**Правила размещения:**
- Всё изменяемое состояние приложения — в `~/Library/Application Support/ProjectVerse/` (БД живёт в Docker-volume, экспорты/резервные копии/логи — по умолчанию здесь). Пути настраиваемые.
- `data/` в корне репозитория — только для локальной разработки, в git не попадает.

---

# 4. Модель данных PostgreSQL

## 4.1. Общие соглашения

| Правило | Значение |
|---|---|
| Первичный ключ | `uuid`, генерируется приложением (time-ordered UUID v7-подобный; при отсутствии библиотеки — `uuid4` + `created_at` для сортировки) |
| Время | `timestamptz`, в БД UTC, в приложении — зона пользователя |
| Деньги | `numeric(12,2)` + отдельная колонка `currency char(3)`; **суммирование разных валют запрещено** на уровне сервиса |
| Перечисления | `varchar` + `CHECK (col IN (...))` вместо нативного PG ENUM — дешёвые миграции, простой откат |
| Мягкое удаление | `deleted_at timestamptz NULL`, частичные уникальные индексы с `WHERE deleted_at IS NULL` |
| Уникальность | там, где нужна нечувствительность к регистру — `lower(...)`-индекс или нормализованное поле |
| Имена констрейнтов | `pk_`, `fk_`, `uq_`, `ck_`, `ix_` через `naming_convention` в `MetaData` (стабильный autogenerate) |
| Комментарии | у каждой таблицы и нетривиальной колонки — `COMMENT ON` |
| Аудит | `created_at`/`updated_at` во всех изменяемых сущностях; `updated_at` обновляется приложением |

**Перечисления (CHECK):**
`channel_type` = `instagram | spotify | youtube | soundcloud | discord | phone | whatsapp | imessage | email | telegram | other`
`campaign_state` = `draft | queued | running | paused | completed | failed | cancelled`
`recipient_state` = `pending | scheduled | sent | delivered | failed | skipped | suppressed`
`attempt_state` = `planned | attempted | accepted | confirmed | delivered | failed | skipped`
`run_state` = `planned | running | succeeded | failed | missed | cancelled`
`task_kind` = `discovery | campaign | automation | beat_series | placements | backup`
`direction` = `in | out`
`category` = `artist | producer | media | other | unknown`
`review_state` = `unreviewed | confirmed | rejected`
`deal_stage` = `open | won | lost`

## 4.2. CRM

### `contacts`
Основная карточка. Один контакт — много каналов.

| Колонка | Тип | Ограничения |
|---|---|---|
| `id` | uuid | PK |
| `display_name` | text | NOT NULL, длина 1..300 |
| `real_name` | text | NULL |
| `stage_name` | text | NULL (сценический псевдоним) |
| `source` | varchar | NOT NULL, CHECK: `manual, instagram, spotify, import, referral, campaign, other` |
| `source_ref` | text | NULL (ссылка на источник обнаружения) |
| `genres` | text | NULL — жанры (заменили отдельную таблицу тегов на этапе 1) |
| `references` | text | NULL — референсы |
| `notes` | text | NULL |
| `custom` | jsonb | NOT NULL DEFAULT `'{}'` — «непонятные» колонки импорта |
| `do_not_contact` | boolean | NOT NULL DEFAULT false |
| `do_not_contact_reason` | text | NULL |
| `last_contact_at` | timestamptz | NULL |
| `next_action_at` | timestamptz | NULL |
| `created_at` / `updated_at` | timestamptz | NOT NULL |
| `deleted_at` | timestamptz | NULL |
| `search_vector` | tsvector | generated: `to_tsvector('simple', coalesce(display_name,'') || ' ' || coalesce(stage_name,'') || ' ' || coalesce(notes,''))` |

Индексы (реализовано): `(deleted_at)`, `(next_action_at)`, GIN-триграммы по `display_name`, `stage_name`, `notes`.
Поиск выполняется через `ILIKE` по триграммным индексам — для кириллицы это работает
предсказуемее, чем `tsvector` без словаря; `tsvector` отложен до появления ранжирования.

### `contact_channels`
Каждый способ связи. Уникальность — по нормализованному значению.

| Колонка | Тип | Ограничения |
|---|---|---|
| `id` | uuid | PK |
| `contact_id` | uuid | FK → `contacts` ON DELETE CASCADE |
| `channel_type` | varchar | NOT NULL, CHECK по списку |
| `raw_value` | text | NOT NULL — как введено |
| `normalized_value` | text | NOT NULL — email в lower, телефон в E.164, хэндл без `@`, URL нормализован |
| `url` | text | NULL |
| `label` | text | NULL (рабочий/личный/менеджер) |
| `is_primary` | boolean | NOT NULL DEFAULT false |
| `connected_account_id` | uuid | FK → `connected_accounts` ON DELETE SET NULL |
| `is_verified` | boolean | NOT NULL DEFAULT false |
| `meta` | jsonb | NOT NULL DEFAULT `'{}'` |
| `created_at` / `updated_at` / `deleted_at` | timestamptz | |

Ограничения:
- `uq_contact_channels_value` — UNIQUE `(channel_type, normalized_value)` **WHERE** `deleted_at IS NULL` → защита от дубликатов (SPEC §6.6).
- `uq_contact_channels_primary` — UNIQUE `(contact_id)` **WHERE** `is_primary` AND `deleted_at IS NULL` → ровно один основной канал.
- `ck_contact_channels_value_not_blank`.

### `status_groups`
Пользовательские группы статусов (Воронка, Заинтересованность, …).

Колонки: `id`, `name`, `slug UNIQUE`, `color`, `allows_multiple boolean NOT NULL DEFAULT false`, `sort_order`, `is_system boolean`, `created_at`, `updated_at`.
Seed-данные: группа «Воронка» (`allows_multiple = false`), группа «Заинтересованность» (`allows_multiple = true`).

### `statuses`
Колонки: `id`, `group_id FK → status_groups ON DELETE CASCADE`, `name`, `slug`, `color`, `sort_order`, `is_terminal`, `is_default`, `created_at`.
UNIQUE `(group_id, slug)`. Seed: New, Contacted, Replied, Interested, Sent Beats, Negotiation, Client, Rejected; Cold, Warm, Hot.

### `contact_statuses`
Колонки: `contact_id FK CASCADE`, `status_id FK CASCADE`, `group_id FK CASCADE` (денормализация для проверки «один статус в группе»), `assigned_at`, `note`.
PK `(contact_id, status_id)`. Индексы `(status_id)`, `(group_id, contact_id)`.
Правило «в группе с `allows_multiple = false` одновременно только один статус» проверяется в сервисе внутри транзакции с блокировкой контакта (`SELECT … FOR UPDATE`); полный уникальный индекс невозможен, поэтому дополнительно — проверка на уровне БД через триггер `trg_contact_statuses_single` (опционально, включается миграцией `0002`, если решим усилить).

### `contact_notes`
`id`, `contact_id FK CASCADE`, `body text NOT NULL`, `author_kind varchar CHECK ('user','ai','system')`, `created_at`, `updated_at`.

### `contact_reminders`
`id`, `contact_id FK CASCADE`, `title`, `due_at`, `done_at`, `state varchar CHECK ('pending','done','cancelled','missed')`, `channel_type`, `notes`, `created_at`.

### `interactions`
Единая история взаимодействий по всем каналам (SPEC §6.1, §7.5, §17).

`id`, `contact_id FK CASCADE`, `channel_type`, `direction CHECK ('in','out')`, `occurred_at`, `subject`, `body`, `external_id text NULL`, `campaign_id FK SET NULL`, `message_attempt_id FK SET NULL`, `meta jsonb`, `created_at`.
UNIQUE `(channel_type, external_id)` WHERE `external_id IS NOT NULL` — повторная синхронизация истории не создаёт дублей.

### `tags` / `contact_tags`
`tags`: `id`, `name`, `slug UNIQUE`, `color`, `created_at`.
`contact_tags`: PK `(contact_id, tag_id)`, оба FK CASCADE.

### `exclusions`
Список исключений для discovery (SPEC §4.6).
`id`, `kind varchar CHECK ('instagram_username','spotify_id','email','domain','phone','url')`, `normalized_value`, `reason`, `created_at`.
UNIQUE `(kind, normalized_value)`.

## 4.3. Деньги и сделки

### `deals`
`id`, `contact_id FK CASCADE`, `title`, `stage varchar CHECK ('open','won','lost') NOT NULL DEFAULT 'open'`, `source varchar`, `amount_expected numeric(12,2)`, `currency char(3)`, `campaign_id FK SET NULL`, `notes`, `closed_at`, `created_at`, `updated_at`, `deleted_at`.

### `payments`
`id`, `deal_id FK CASCADE`, `amount numeric(12,2) NOT NULL CHECK (amount >= 0)`, `currency char(3) NOT NULL`, `paid_at timestamptz NOT NULL`, `method varchar`, `external_ref text`, `notes`, `created_at`.
Индекс `(paid_at)`, `(deal_id)`.

### `deal_items`
Позиции сделки — история продаж битов (SPEC §13).
`id`, `deal_id FK CASCADE`, `beat_id FK SET NULL`, `pack_id FK SET NULL`, `title_snapshot text NOT NULL`, `amount numeric(12,2)`, `currency char(3)`.

**Правило расчёта:** фактический доход = сумма `payments`; потенциальный = сумма `deals.amount_expected` по сделкам `open`. Они никогда не складываются в одну цифру (SPEC §6.7).

## 4.4. Кампании и шаблоны

### `message_templates` / `template_variants`
Шаблон-контейнер + несколько вариантов текста, из которых получателю достаётся один (SPEC §7.3).

`message_templates`: `id`, `name`, `category`, `channel_type NULL`, `is_archived`, `created_at`, `updated_at`.
`template_variants`: `id`, `template_id FK CASCADE`, `name`, `subject text NULL`, `body text NOT NULL`, `variables jsonb` (обнаруженные `{Name}` и т.п.), `attachments jsonb`, `sort_order`, `weight int DEFAULT 1`. UNIQUE `(template_id, name)`.

### `campaigns`
`id`, `name`, `channel_type NOT NULL`, `template_id FK SET NULL`, `connected_account_id FK SET NULL`, `state varchar NOT NULL DEFAULT 'draft'`, `settings jsonb` (задержки, лимиты, расписание), `schedule jsonb`, `stats jsonb` (счётчики по состояниям), `created_at`, `started_at`, `finished_at`, `paused_at`, `last_error`.

### `campaign_recipients`
`id`, `campaign_id FK CASCADE`, `contact_id FK CASCADE`, `variant_id FK SET NULL`, `state varchar NOT NULL DEFAULT 'pending'`, `scheduled_at`, `sent_at`, `last_error`, `created_at`, `updated_at`.
UNIQUE `(campaign_id, contact_id)` — один и тот же контакт не попадает в кампанию дважды.

### `message_attempts`
`id`, `recipient_id FK CASCADE`, `attempt_no int NOT NULL`, `state varchar NOT NULL DEFAULT 'planned'`, `idempotency_key text NOT NULL UNIQUE`, `started_at`, `finished_at`, `provider_message_id`, `error_code`, `error_message`, `request jsonb`, `response jsonb`.
UNIQUE `(recipient_id, attempt_no)`.

**Разделение состояний (SPEC §7.5):** `accepted` (API вернул успех) ≠ `confirmed` (провайдер подтвердил приём) ≠ `delivered` (есть подтверждение доставки). Кнопка «Отправить» создаёт `planned`, но не `delivered`.

### `follow_up_sequences` / `_steps` / `_enrollments`
`follow_up_sequences`: `id`, `name`, `state`, `created_at`.
`follow_up_steps`: `id`, `sequence_id FK CASCADE`, `position int`, `delay_days int`, `template_variant_id FK SET NULL`, `conditions jsonb`. UNIQUE `(sequence_id, position)`.
`follow_up_enrollments`: `id`, `sequence_id FK CASCADE`, `contact_id FK CASCADE`, `current_position`, `state`, `next_run_at`, `started_at`, `completed_at`. UNIQUE `(sequence_id, contact_id)` — одна последовательность на контакт (SPEC §7.4: повторный запуск не дублирует отправки).

## 4.5. Автоматизации и планировщик

### `automations`
`id`, `name`, `trigger_type varchar` (status_changed, status_expired, reminder_due, contact_imported, campaign_finished, sale_confirmed, manual), `trigger_config jsonb`, `conditions jsonb`, `actions jsonb`, `scheduled_task_id FK SET NULL`, `state`, `created_at`, `updated_at`.

### `automation_runs`
`id`, `automation_id FK CASCADE`, `contact_id FK SET NULL`, `state`, `started_at`, `finished_at`, `result jsonb`, `error`.
**Правило SPEC §9.4:** если действие не удалось, `state != succeeded`.

### `automation_events`
`id bigserial`, `automation_id FK CASCADE`, `dedupe_key text NOT NULL UNIQUE`, `contact_id FK SET NULL`, `occurred_at`, `processed_at`.
`dedupe_key` = `sha256(automation_id + trigger + entity + окно)` — защита от повторного выполнения одного события.

### `scheduled_tasks`
`id`, `name`, `task_kind varchar`, `payload jsonb`, `schedule_kind varchar CHECK ('once','interval','daily','weekly','cron')`, `schedule_config jsonb`, `timezone text NOT NULL`, `start_at`, `end_at`, `next_run_at`, `last_run_at`, `state`, `misfire_policy varchar CHECK ('skip','run_once','catch_up')`, `created_at`, `updated_at`.
Индекс `(next_run_at) WHERE state = 'active'`.

### `task_runs`
`id`, `scheduled_task_id FK CASCADE`, `planned_at timestamptz NOT NULL`, `started_at`, `finished_at`, `state varchar NOT NULL`, `result jsonb`, `error`.
UNIQUE `(scheduled_task_id, planned_at)` — один плановый момент = один запуск.

## 4.6. Discovery и библиотека артистов

### `artist_sources`
`id`, `platform varchar CHECK ('instagram','spotify','manual')`, `kind varchar` (page, profile, hashtag, playlist, media, label, list), `value`, `url`, `enabled boolean DEFAULT true`, `last_checked_at`, `meta jsonb`, `created_at`, `updated_at`.
UNIQUE `(platform, kind, value)`.

### `discovery_jobs`
`id`, `name`, `platform`, `strategies jsonb` (выбранные типы поиска), `filters jsonb`, `state varchar` (draft/queued/running/paused/completed/failed/cancelled), `stats jsonb`, `started_at`, `finished_at`, `last_progress_at`, `error`, `created_at`, `updated_at`.

### `discovery_job_sources`
Точка возобновления (SPEC §4.5 — «продолжать с последней сохранённой позиции»).
`id`, `job_id FK CASCADE`, `source_id FK SET NULL`, `cursor jsonb` (например, `{"last_media_id": "…", "page": 3}`), `items_processed int DEFAULT 0`, `last_error`, `updated_at`.
UNIQUE `(job_id, source_id)`.

### `artist_profiles`
`id`, `platform`, `platform_id`, `username`, `url`, `display_name`, `bio`, `followers_count int NULL`, `email`, `phone`, `music_links jsonb`, `category varchar CHECK`, `confidence numeric(3,2)`, `classification_reason text`, `classified_at`, `classifier_model`, `review_state varchar DEFAULT 'unreviewed'`, `first_seen_at`, `last_checked_at`, `raw jsonb`, `created_at`, `updated_at`, `deleted_at`.
UNIQUE `(platform, platform_id)` WHERE `platform_id IS NOT NULL`; UNIQUE `(platform, lower(username))`.

**Поля классификации строго по SPEC §4.4:** категория, уверенность, основание, дата, модель, статус проверки. Отсутствующие данные — `NULL`, не выдуманные значения (SPEC §5.2).

### `discovery_results`
`id`, `job_id FK CASCADE`, `profile_id FK CASCADE`, `source_id FK SET NULL`, `discovered_at`, `state varchar CHECK ('new','imported','excluded','rejected')`.
UNIQUE `(job_id, profile_id)`.

### `artist_library_entries`
`id`, `profile_id FK CASCADE UNIQUE`, `crm_contact_id FK SET NULL`, `notes`, `tags jsonb`, `added_at`.
Библиотека живёт локально и не требует обращения к внешнему API (SPEC §5.4).

## 4.7. Биты

### `beats`
`id`, `title`, `file_path`, `preview_url`, `genre`, `subgenre`, `references text`, `bpm numeric(5,2)` CHECK `bpm > 0 AND bpm < 400`, `musical_key`, `mood`, `description`, `drums`, `bass`, `created_date date`, `price numeric(12,2)`, `currency`, `license_terms text`, `availability varchar CHECK ('available','leased','sold_exclusive','archived')`, `tags jsonb`, `created_at`, `updated_at`, `deleted_at`.

### `beat_packs` / `beat_pack_items`
`beat_packs`: `id`, `name`, `description`, `created_at`.
`beat_pack_items`: PK `(pack_id, beat_id)`, `position int`.

### `beat_series` / `_steps` / `_enrollments`
`beat_series`: `id`, `name`, `channel_type`, `settings jsonb`, `stop_conditions jsonb`, `state`, `created_at`.
`beat_series_steps`: `id`, `series_id FK CASCADE`, `step_no int`, `delay_days int`, `pack_id FK SET NULL`, `template_variant_id FK SET NULL`, `message_override text`. UNIQUE `(series_id, step_no)`.
**Лимит 30 этапов — валидация сервиса, не ограничение схемы** (SPEC §10).
`beat_series_enrollments`: `id`, `series_id FK CASCADE`, `contact_id FK CASCADE`, `current_step`, `state`, `next_run_at`. UNIQUE `(series_id, contact_id)`.

### `beat_placements`
`id`, `beat_id FK CASCADE`, `release_title`, `release_url`, `platform`, `artist_name`, `found_at`, `similarity_score numeric(4,3)`, `algorithm varchar`, `state varchar CHECK ('pending','confirmed','rejected')`, `reviewed_at`, `notes`, `audio_ref`.
Автоматический результат — всегда `pending`, никогда не «доказательство использования» (SPEC §14).

## 4.8. Интеграции

### `connected_accounts`
`id`, `channel_type`, `display_name`, `external_id`, `credential_id FK SET NULL`, `state varchar CHECK ('disconnected','connected','error','expired')`, `last_check_at`, `meta jsonb`, `created_at`, `updated_at`.
UNIQUE `(channel_type, external_id)`.

### `integration_credentials`
`id`, `provider`, `keychain_ref text NOT NULL`, `meta jsonb`, `created_at`, `updated_at`.
UNIQUE `(provider, keychain_ref)`. **Секрета в таблице нет.**

### `telegram_allowed_users`
`telegram_user_id bigint PK`, `label`, `role varchar CHECK ('owner','operator')`, `created_at`, `revoked_at`.
Доступ к боту ограничен этим списком (SPEC §15).

## 4.9. AI

### `ai_conversations`
`id`, `mode varchar CHECK ('help','deals')`, `contact_id FK SET NULL`, `title`, `created_at`, `deleted_at`.

### `ai_messages`
`id`, `conversation_id FK CASCADE`, `role varchar CHECK ('user','assistant','system')`, `content text`, `attachments jsonb` (ссылки на скриншоты), `model`, `token_usage jsonb`, `created_at`.

### `ai_actions`
Типизированные команды с подтверждением (SPEC §12.3).
`id`, `conversation_id FK CASCADE`, `command_name text NOT NULL` (whitelist в коде), `payload jsonb`, `state varchar CHECK ('proposed','approved','rejected','executed','failed')`, `approved_at`, `executed_at`, `result jsonb`, `error`.
Свободный SQL и произвольный код невозможны: `command_name` валидируется по реестру.

## 4.10. Системные

### `app_settings`
`key text PK`, `value jsonb NOT NULL`, `updated_at`.

### `audit_log`
`id bigserial PK`, `occurred_at timestamptz NOT NULL`, `level varchar` (debug/info/warning/error), `category varchar` (job, campaign, send, import, export, crm, automation, ai, integration, backup, security), `event_type varchar`, `entity_type`, `entity_id uuid`, `job_id uuid`, `result varchar` (started/succeeded/failed/cancelled/missed), `message text`, `details jsonb`.
Индексы: `(occurred_at DESC)`, `(category, occurred_at DESC)`, GIN `details`.
Секреты не пишутся (SPEC §17) — гарантируется фильтром `security/redaction.py`.

### `backup_records`
`id`, `path`, `size_bytes bigint`, `sha256 char(64)`, `kind varchar CHECK ('manual','auto')`, `state varchar CHECK ('created','verified','failed')`, `created_at`, `verified_at`, `error`.

### `data_transfers`
`id`, `direction varchar CHECK ('import','export')`, `format varchar CHECK ('csv','xlsx','txt','json')`, `entity varchar`, `file_path`, `mapping jsonb`, `stats jsonb`, `state`, `error`, `created_at`, `finished_at`.
Сохраняет результаты импорта/экспорта и маппинг колонок для повторного использования.

## 4.11. Сводка связей и каскадов

| Родитель | Ребёнок | При удалении |
|---|---|---|
| contacts | contact_channels, contact_statuses, contact_notes, contact_reminders, interactions, contact_tags, deals | CASCADE |
| deals | payments, deal_items | CASCADE |
| campaigns | campaign_recipients → message_attempts | CASCADE |
| follow_up_sequences | steps, enrollments | CASCADE |
| automations | automation_runs, automation_events | CASCADE |
| scheduled_tasks | task_runs | CASCADE |
| beat_series | steps, enrollments | CASCADE |
| beat_packs | beat_pack_items | CASCADE |
| beats | beat_pack_items, deal_items, beat_series_steps | CASCADE / SET NULL |
| artist_profiles | discovery_results, artist_library_entries | CASCADE |
| discovery_jobs | discovery_job_sources, discovery_results | CASCADE |
| ai_conversations | ai_messages, ai_actions | CASCADE |

**Ограничение:** `beat_placements.beat_id` → `RESTRICT` (нельзя удалить бит с историей размещений; допускается только мягкое удаление).

## 4.12. Оценка объёма

| Сущность | Реалистичный объём на одного пользователя |
|---|---|
| contacts | 5 000 – 100 000 |
| contact_channels | ×1.5–3 от контактов |
| interactions | 100 000 – 2 000 000 |
| artist_profiles | 10 000 – 500 000 |
| discovery_results | ×1–3 от профилей |
| message_attempts | 10 000 – 500 000 |

Модель рассчитана на эти объёмы при индексах из раздела 5; пагинация в UI обязательна.

---

# 5. Список миграций

Формат: `NNNN_название` — содержимое — обратимость — этап, на котором вводится.

### `0001_bootstrap` — расширения
- `CREATE EXTENSION IF NOT EXISTS pg_trgm` (нужен для поиска по подстроке).
- **Downgrade:** `DROP EXTENSION IF EXISTS pg_trgm`.
- **Реализовано.**

### `0002_crm_core` — схема CRM
- Таблицы: `app_settings`, `audit_log`, `contacts`, `contact_channels`, `status_groups`,
  `statuses`, `contact_statuses`, `contact_notes`, `contact_reminders`, `interactions`,
  `deals`, `payments`, `exclusions`, `data_transfers`.
- Частичные уникальные индексы: `contact_channels (channel_type, normalized_value)
  WHERE deleted_at IS NULL` и `(contact_id) WHERE is_primary AND deleted_at IS NULL`.
- GIN-триграммы: `contacts.display_name/stage_name/notes`, `contact_channels.normalized_value`.
- **Downgrade:** полный откат (проверяется тестом).
- **Реализовано** (сгенерировано autogenerate, затем вычитано вручную).

### `0003_enum_checks` — CHECK-ограничения перечислений
- Alembic не создаёт CHECK для `Enum(native_enum=False)` — добавлены явно для
  `contacts.source`, `contact_channels.channel_type`, `contact_notes.author_kind`,
  `contact_reminders.state/channel_type`, `interactions.direction/channel_type`,
  `deals.stage/source`, `audit_log.level/result`, `data_transfers.direction/format/state`.
- **Downgrade:** удаление ограничений.
- **Реализовано.**

### `0004_seed_statuses` — стартовые справочники
- Две группы («Воронка», «Заинтересованность») и 11 статусов с фиксированными UUID.
- `ON CONFLICT` + фиксированные UUID ⇒ повторный накат не создаёт дублей.
- **Downgrade:** удаление ровно этих UUID.
- **Реализовано.**

### Следующие (по этапам 2–8)
`0005_campaigns`, `0006_automations_schedule`, `0007_discovery`, `0008_beats`,
`0009_integrations`, `0010_ai`, `0011_backups` — по мере реализации этапов.

**Правила для всех миграций:**
1. Ни одна миграция не удаляет и не переписывает пользовательские данные (SPEC §24).
2. `downgrade` реализуется всегда, кроме случаев, где он уничтожил бы данные — такие случаи не допускаются в этой схеме.
3. Тест на каждую ревизию: `upgrade head` на пустой БД, затем `downgrade -1` и `upgrade head` повторно.
4. Autogenerate используется как черновик, но итоговый файл всегда редактируется вручную (имена констрейнтов, комментарии, seed).

---

# 6. План реализации по этапам

Общая рамка SPEC §22 сохранена; добавлен «Этап 0» (инфраструктура) и уточнён состав этапа 3.

Каждый этап закрывается по протоколу SPEC §24: тесты → исправления → проверка интерфейса → документы → список «сделано / не сделано» → предложение следующего этапа. Переход к следующему этапу запрещён, пока текущий не запускается.

## Этап 0. Bootstrap — фундамент ✅ реализован

**Цель:** запускаемое приложение с пустым, но настоящим каркасом.

| # | Работа | Результат |
|---|---|---|
| 0.1 | Репозиторий: `.gitignore`, `README.md`, `pyproject.toml` с pinned-зависимостями, venv на Python 3.14.4 | `pip install -e .` работает |
| 0.2 | `docker-compose.yml`: `postgres:17` (arm64), порт 5433, volume, healthcheck | `make db-up` поднимает БД |
| 0.3 | `config.py` на `pydantic-settings`: `DATABASE_URL`, `APP_ENV`, пути данных, `LOG_LEVEL` | `.env.example` и валидация при старте |
| 0.4 | Alembic + `0001_bootstrap` | `make migrate` накатывает схему |
| 0.5 | `db/base.py`, `db/session.py` (async engine, unit-of-work), `clock.py`, `errors.py` | Интеграционный тест «подключение + простая таблица» |
| 0.6 | `runtime.py`: asyncio-поток, `submit()`, отмена, корректное завершение | Тест: задача выполняется вне GUI-потока |
| 0.7 | `security/redaction.py` + настройка логирования (файл + консоль) | Тест: токен не попадает в лог |
| 0.8 | `ui/main_window.py`: сайдбар, `QStackedWidget`, статус-бар; `views/roadmap.py` (честный список модулей со статусами) | Приложение открывается |
| 0.9 | Экран «Здоровье системы»: версия Python/Qt/PostgreSQL, статус миграций | Видно реальное состояние, не заглушка |
| 0.10 | Скелет тестов: `conftest.py`, тестовая БД, CI-less команда `make test` | ≥ 8 зелёных тестов |

**Приёмка этапа 0 (выполнено):**
- `make db-up && make migrate && make run` → окно с навигацией, в статус-баре
  `PostgreSQL: подключено · 17.11 · миграция 0004_seed_statuses`.
- Без БД приложение запускается и показывает причину в статус-баре, а не падает.
- `make test` (43 теста) и `make test-ui` (9 тестов) — зелёные.
- В навигации только работающие разделы: Dashboard, CRM, Журнал, Настройки, Roadmap.

## Этап 1. CRM Core — основной рабочий модуль ✅ реализован

**Цель:** полноценная CRM, заменяющая повседневную работу битмейкера.

| Блок | Состав |
|---|---|
| Контакты | создание/редактирование карточки, мягкое удаление, восстановление, финальное удаление, DNC |
| Каналы | 11 типов, нормализация, уникальность, основной канал, привязка к отправляющему аккаунту |
| Статусы | группы и статусы (seed + создание пользователем), цвета, мультивыбор по `allows_multiple`, фильтр по статусам |
| Заметки и напоминания | заметки с автором, напоминания с датой и статусом |
| Взаимодействия | ручное добавление истории, просмотр таймлайна по контакту |
| Сделки и деньги | сделка, платежи, потенциальная сумма, доход по источникам, разделение «факт/потенциал» |
| Таблица CRM | серверная пагинация, поиск (имя/username/email/телефон/заметки), фильтры, сортировка, массовый выбор |
| Массовые действия | смена статусов, заметки, дата следующего контакта, основной канал, привязка к аккаунту, корзина, экспорт |
| Слияние | ручное слияние дублей с сохранением сообщений, сделок, заметок и источников |
| Импорт | CSV/XLSX/TXT, мастер маппинга колонок, предпросмотр, отчёт, повторный импорт без дублей |
| Экспорт | CRM целиком и выбранные записи, сделки отдельно |
| Dashboard | реальные счётчики (контакты, статусы, доход, ближайшие действия) |

**Приёмка этапа 1 (выполнено):** сценарии SPEC §21 №1–6, 10, 17 покрыты тестами;
повторный импорт того же CSV даёт `created=0, unchanged=N`; удаление контакта в корзину
убирает его из активного списка; все экраны работают на реальных данных.

**Отклонения от плана на этапе 1 (осознанные):**
- Отдельная таблица тегов заменена полями `contacts.genres` и `contacts.references` —
  теги нужны в основном для discovery, вернёмся к ним на этапе 2.
- `tsvector`-колонка заменена триграммными индексами (см. §4.2).
- `deal_items` (позиции сделки) отложены до этапа 7 вместе с каталогом битов.
- XLSX-импорт отложен: на этапе 1 работает CSV (импорт XLSX — отдельная задача).

## Этап 2. Библиотека артистов и Discovery

- **Artist Library** — локальная библиотека, полностью рабочая без внешних API (SPEC §5.4).
- **Spotify Discovery** — только реально доступные операции: поиск артиста по имени, по URL, извлечение артистов из плейлиста, сохранение в библиотеку. Related artists и monthly listeners не обещаем (см. 7.1).
- **Instagram Discovery** — сначала import-centric: ручные списки, CSV, проверка известных профилей; затем спайк по доступным источникам.
- Курсоры, пауза/резюме, исключения, экспорт — как в SPEC §4.5–4.7.
- AI-классификация с очередью повторной обработки при недоступности API (SPEC §4.4).

## Этап 3. Кампании + email (объединение SPEC-этапов 3 и 4.1)

- Библиотека шаблонов, варианты текста, переменные `{Name}`, `{Username}`, `{Phone}` с корректной чисткой пунктуации.
- Кампании: состояния, получатели, пауза/возобновление/остановка/повтор неудачных, экспорт результатов.
- `message_attempts` с идемпотентностью; разделение «принято API» и «доставлено».
- Follow-up: отдельные списки, исключение ответивших, DNC и уже получивших последовательность.
- **Email-адаптер** (SMTP + IMAP): единственный канал, который вводится вместе с кампаниями, чтобы модуль был рабочим, а не демонстрационным.
- Ручная отметка «ответил», поскольку не все каналы отдают входящие (SPEC §7.6).

## Этап 4. Остальные каналы — по одному, со спайком

Для каждого канала обязателен спайк с письменным go/no-go в `docs/SPIKES.md` до написания UI:

1. **iMessage** (macOS): AppleScript/`osascript` + TCC-разрешения; чтение истории — при Full Disk Access. Если отправка нестабильна — только ручной режим + фиксация факта.
2. **WhatsApp**: Cloud API при наличии бизнес-аккаунта; иначе — только ручное открытие чата с ручным подтверждением, без статуса «доставлено».
3. **Discord**: бот + разрешённые серверы/каналы; DM — после подтверждения правил.
4. **Instagram**: только ответы в окне диалога; холодный аутрич через API невозможен.

## Этап 5. Автоматизации, планировщик, Beat Series

Триггеры/условия/действия из SPEC §9, дедупликация событий, ограниченные повторы; планировщик с часовыми поясами и `missed`-запусками; серии битов с настраиваемым лимитом этапов.

## Этап 6. AI-ассистент

Режимы Help и Deals, до четырёх скриншотов, привязка контакта, типизированные команды с подтверждением, локальная история, редактирование персональных данных перед отправкой.

## Этап 7. Каталог битов и размещения

Каталог с метаданными, извлечение BPM (FFmpeg + библиотека анализа), поиск и фильтры; размещения — после спайка по аудиосходству, результат всегда «кандидат».

## Этап 8. Telegram и резервное копирование

Long polling, allowlist, подтверждение опасных действий; резервные копии (`pg_dump` + настройки + шаблоны), проверка целостности (sha256), восстановление с подтверждением.

## Этап 9. Стабилизация

Прогон всех пользовательских сценариев, производительность, упаковка `.app`, инструкция по установке.

## Сводная таблица этапов

| Этап | Содержание | Ключевой риск |
|---|---|---|
| 0 | Bootstrap | Docker-демон выключен; настройка окружения |
| 1 | CRM Core | Объём; качество импорта |
| 2 | Library + Discovery | Instagram недоступен официально |
| 3 | Campaigns + Email | SMTP-провайдеры, лимиты |
| 4 | Прочие каналы | Политики платформ, TCC |
| 5 | Automations + Schedule | Пропущенные запуски, дубли |
| 6 | AI | Качество ответов, приватность |
| 7 | Beats + Placements | Аудиосходство |
| 8 | Telegram + Backup | Безопасность доступа |
| 9 | Финализация | Упаковка, нотаризация |

---

# 7. Внешние API и интеграции

Формат: **заявлено в SPEC → проверено → реально возможно → требования → ограничение → альтернатива.**
Статус проверки: ✅ проверено по документации · ⚠️ частично · ❌ заблокировано · ⏳ спайк не проведён.

## 7.1. Spotify Web API — ⚠️ частично

**Заявлено (SPEC §5):** поиск по имени, жанру, URL; извлечение артистов из плейлиста; похожие артисты; ежемесячные слушатели; города слушателей; жанры.

**Проверено:**
- Поиск, объект артиста, треки плейлиста — доступны.
- **Related Artists, Recommendations, Audio Features, Audio Analysis, Featured/Category Playlists закрыты для новых приложений с 27.11.2024.** Существующие extended-mode приложения не затронуты — новое приложение попадает под ограничение ([Spotify blog](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)).
- В объекте артиста поля `followers`, `genres`, `popularity` помечены **Deprecated**; «monthly listeners» в API **отсутствует** ([reference](https://developer.spotify.com/documentation/web-api/reference/get-an-artist)).

**Реально возможно:** поиск артистов, данные профиля (id, name, images, external_urls), треки плейлиста, сохранение в локальную библиотеку.

**Требования:** приложение в Spotify Developer Dashboard, OAuth 2.0 Authorization Code, `client_id`/`client_secret` в Keychain. Development Mode ограничивает число пользователей — для персонального использования достаточно.

**Ограничения, которые попадут в UI:** «похожие артисты», «ежемесячные слушатели», «города слушателей» — помечаются как недоступные. Поля в БД остаются `NULL`. Никаких оценочных значений вместо реальных (SPEC §5.2).

**Альтернатива:** статистика только по тем артистам, которых пользователь вводит вручную; жанры — из собственных заметок и AI-классификации.

## 7.2. Instagram — ❌ для discovery, ✅ для ответов

**Заявлено (SPEC §4, §8.1):** поиск артистов, анализ публикаций/Reels/отметок/подписчиков/хештегов, отправка DM и кампании.

**Проверено:**
- Отправка сообщений: диалог **начинает только пользователь**; приложение может лишь отвечать, окно по умолчанию ~24 ч; нужен professional-аккаунт; требуется app review на permission для сообщений ([docs](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api)).
- Публичного поиска пользователей, списков подписчиков/подписок и произвольной выдачи по хештегам в Instagram Platform нет. Страницы документации по hashtag search и business discovery в текущей версии отдают 404 (проверено).

**Реально возможно:** приём входящих, ответы в окне диалога, публикация контента, ограниченная бизнес-статистика.

**Ограничение:** **холодный Instagram-аутрич через API невозможен.** Массовый поиск средствами официального API невозможен.

**Альтернатива, заложенная в дизайн:**
1. Ручные списки известных профилей + проверка их существования.
2. Импорт CSV/экспортов, которые пользователь получил легально.
3. Ручная отметка «написал в Instagram» с фиксацией факта в `interactions`.
4. Скрейпинг, обход CAPTCHA и сессионные трюки **не реализуются** (SPEC §4.8).

## 7.3. Email (SMTP + IMAP) — ✅ реализуемо

**Возможно:** подключение аккаунта, тема/текст/вложения, отправка beat packs, разбиение пакетов по лимиту провайдера, журнал ошибок.

**Проверка статуса доставки:** SMTP-ответ `250` = принято сервером, но **не доставлено**. Реальная доставка требует разбора DSN/bounce через IMAP — это закладывается как опциональная синхронизация (`interactions` + `message_attempts.confirmed`).

**Требования:** ящик с доступом по SMTP/IMAP; для Gmail — app password и лимиты; пароль только в Keychain.

**Ограничение:** гарантированная доставка не подтверждается без bounce-анализа; массовые рассылки упираются в лимиты провайдера и репутацию домена.

## 7.4. iMessage — ⏳ спайк

**Что нужно проверить:** отправка через `osascript`/AppleScript к Messages.app, необходимые TCC-разрешения (Automation), чтение истории (`~/Library/Messages/chat.db`, Full Disk Access), поведение SMS-фолбэка через iPhone.

**Ограничение:** нет официального API; разрешения выдаются только пользователем; возможны изменения между версиями macOS. SPEC §8.3 требует честно заявить об ограничениях, если отправка через iPhone не тестировалась.

**Критерий go:** стабильная отправка ≥ 50 сообщений подряд на macOS 15.7 без ручных подтверждений. Иначе — режим «составить и открыть чат» с ручной отметкой.

## 7.5. WhatsApp — ⚠️ частично

**Проверено:** WhatsApp Business Platform (Cloud API) реально существует и поддерживает текст, медиа, интерактив, звонки, группы ([docs](https://developers.facebook.com/docs/whatsapp/cloud-api/overview)).

**Требования:** бизнес-аккаунт Meta, выделенный номер, верификация бизнеса, шаблоны для исходящих вне окна обслуживания (детали шаблонов и окна требуют подтверждения — документация отдалась частично).

**Ограничение:** для персонального битмейкера без юридического лица порог входа может оказаться избыточным.

**Альтернатива:** ручное открытие чата `wa.me/<phone>` + ручная отметка об отправке. Открытие чата **не считается** отправкой (SPEC §8.4).

## 7.6. Discord — ⏳ спайк

**Что нужно проверить:** возможность отправки в канал сервера, где присутствует бот; условия DM для пользователя, не состоящего с ботом в общем сервере.

**Вероятный сценарий:** бот в сервере пользователя, каналы `channels` доступны, отправка в канал — реальна; личные сообщения — только при общем сервере.

**Ограничение:** обход прав доступа и требований Discord к автоматизации запрещён (SPEC §8.5).

## 7.7. Telegram Bot API — ✅ стандарт

**Возможно:** long polling (без публичного вебхука), CRM-просмотр, поиск, заметки, напоминания, запуск/пауза заданий, статистика, уведомления.

**Требования:** токен от `@BotFather`, allowlist по `telegram_allowed_users`, подтверждение опасных действий.

**Ограничение:** бот не должен быть доступен никому, кроме владельца; локальный сервер в интернет не выставляется (SPEC §15).

## 7.8. LLM API (DeepSeek) — ✅ проверено

**Проверено:** API OpenAI-совместим, base URL `https://api.deepseek.com`, модели `deepseek-flash` и `deepseek-v4-pro`; **Vision поддерживает `deepseek-flash`**, `deepseek-v4-pro` — нет ([pricing](https://api-docs.deepseek.com/quick_start/pricing)).

**Следствие:** режим Deals (до 4 скриншотов) реализуем на `deepseek-flash`.

**Требования:** API-ключ в Keychain; лимиты и стоимость; редактирование персональных данных и секретов перед отправкой.

**Ограничение:** качество распознавания скриншотов зависит от модели; при недоступности API приложение продолжает работать, ассистент показывает понятную ошибку.

## 7.9. macOS Contacts — ⏳ спайк

**Что проверить:** `CNContactStore` через pyobjc (колёса `cp314` есть) + TCC-разрешение на контакты; альтернатива — импорт `.vcf` без разрешений.

**Ограничение:** разрешение выдаётся пользователем вручную; отказ должен обрабатываться понятным сообщением (SPEC §6.8).

## 7.10. Аудиосходство и мониторинг размещений — ⏳, вероятно невозможно в полном виде

**Заявлено (SPEC §14):** находить релизы, где использован бит пользователя.

**Проверено:** публичного API «где использован мой трек» не существует. Доступные кандидаты решают **обратную** задачу (идентификация неизвестного фрагмента по базе) либо требуют корпоративного контракта.

**Возможные направления для спайка:**
- Локальное сравнение по фингерпринтам (Chromaprint/AcoustID, audfprint) против собственной библиотеки пользователя — обнаруживает совпадения только внутри загруженного набора.
- Сервисы идентификации (ACRCloud/AudD) — идентификация известного трека по клипу, а не поиск по каталогу стримингов.
- Content ID дистрибьютора — единственный реальный канал обнаружения использования, но вне нашего приложения.

**До завершения спайка модуль не заявляется как работающий.** В UI — только ручная фиксация найденных размещений и локальное сравнение, если спайк его подтвердит.

## 7.11. FFmpeg — ⏳ требуется установка

Не установлен. Нужен на этапе 7 для извлечения длительности, BPM, превью. Устанавливается через Homebrew; до этого функции аудио остаются помеченными как недоступные.

## 7.12. Сводная матрица

| Интеграция | Статус | Что даём пользователю | Чего не будет |
|---|---|---|---|
| Spotify Web API | ⚠️ | поиск, профиль, плейлисты, библиотека | related artists, monthly listeners, audio features |
| Instagram Messaging | ✅ (ответы) | приём и ответы в окне | холодные DM, массовый аутрич |
| Instagram Discovery | ❌ | ручные списки, CSV, проверка профилей | скрейпинг, поиск подписчиков |
| Email | ✅ | полноценная кампания | гарантия доставки без bounce-анализа |
| iMessage | ⏳ | после спайка | обещания до спайка |
| WhatsApp | ⚠️ | Cloud API или ручной режим | отправка без бизнес-верификации |
| Discord | ⏳ | каналы сервера | обход прав |
| Telegram Bot | ✅ | удалённое управление | публичный доступ |
| DeepSeek (AI) | ✅ | Help, Deals, скриншоты | vision на `deepseek-v4-pro` |
| macOS Contacts | ⏳ | импорт или `.vcf` | доступ без TCC |
| Аудиосходство | ⏳ | кандидаты после спайка | «доказательство использования» |
| FFmpeg | ⏳ | аудиоанализ после установки | до установки |

---

# 8. Технические ограничения и неопределённости

## 8.1. Ограничения среды (проверены)

| # | Ограничение | Влияние | Решение |
|---|---|---|---|
| E1 | Docker-демон не запущен | БД не поднимется до старта Docker Desktop | `make db-up` проверяет доступность демона и печатает инструкцию; в README — шаг «запустить Docker Desktop» |
| E2 | Локального PostgreSQL нет | Нельзя рассчитывать на `psql` | Всё через Docker; резерв — `brew install postgresql@17` |
| E3 | 8 ГБ RAM | Нельзя держать WebEngine и тяжёлые воркеры | `PySide6-Essentials`; пагинация; аудиоанализ — отдельным процессом/по требованию |
| E4 | Python только 3.14.4 | Возможны редкие несовместимости библиотек | Зависимости проверены (`pip --dry-run`); резерв — `python@3.12` из Homebrew |
| E5 | FFmpeg не установлен | Нет аудиофункций | Этап 7 начинается с установки и проверки |
| E6 | `LC_CTYPE=C` | Сортировка и регистр кириллицы | Явная установка локали и `COLLATE "ru-RU-x-icu"`/`C.UTF-8` в индексах |
| E7 | TCC-разрешения (Automation, Full Disk Access, Contacts) | iMessage/Contacts могут не работать | Спайк; понятный экран «разрешение не выдано»; фолбэки |
| E8 | Keychain может требовать разблокировки | Фоновые задачи при заблокированном экране | Секреты читаются при старте задачи; ошибка фиксируется, задача переносится |
| E9 | Verse 5.9.0 установлен в `/Applications` | Соблазн копировать поведение | Используется только как продуктовая референция; reverse-engineering не планируется |

## 8.2. Внешние ограничения

| # | Ограничение | Следствие |
|---|---|---|
| X1 | Instagram: нет публичного поиска, нет холодных DM | Discovery — только из разрешённых источников |
| X2 | Spotify: related artists/recommendations/audio features закрыты | Раздел «похожие артисты» не реализуется |
| X3 | Spotify: monthly listeners отсутствуют | Поле остаётся пустым, UI показывает «недоступно» |
| X4 | WhatsApp: бизнес-верификация | Канал может остаться ручным |
| X5 | Discord: правила DM | Возможна отправка только в каналы сервера |
| X6 | Нет API «где использован бит» | Placements — ручной/локальный сценарий |
| X7 | Rate limits у всех API | Обязательный backoff, лимиты на кампанию |
| X8 | Изменение условий платформ | Адаптеры изолированы, отключение канала не ломает CRM |

## 8.3. Реестр технических рисков

| Риск | Вероятность | Влияние | Мера |
|---|---|---|---|
| PySide6 и Python 3.14: скрытая несовместимость | Низкая | Высокое | Проверка на этапе 0 (окно + таблица + диалог); резерв — Python 3.12 |
| Async SQLAlchemy усложняет отладку | Средняя | Среднее | Unit-of-work, запрет сессий в UI, тесты репозиториев на реальном PG |
| Async-event-loop и завершение приложения | Средняя | Среднее | Явный `shutdown()` в этапе 0 + тест |
| Импорт «грязных» CSV ломает данные | Высокая | Среднее | Мастер маппинга, предпросмотр, dry-run, отчёт об ошибках, `custom jsonb` |
| Производительность поиска при 100k контактов | Средняя | Среднее | `tsvector` + триграммы + пагинация; тест на 10k |
| Смешивание валют в отчётах | Средняя | Высокое | Раздельные суммы по валютам, тесты |
| Секреты в логах | Средняя | Высокое | Фильтр редактирования + тесты |
| Гонки планировщика (двойной запуск) | Средняя | Высокое | Уникальность `(task, planned_at)`, `FOR UPDATE SKIP LOCKED` |
| Пропущенные задачи выдаются за выполненные | Средняя | Высокое | Состояние `missed`, тест с «выключенным» временем |
| Долгая миграция на реальных данных | Низкая | Среднее | Индексы после загрузки, миграции не удаляют данные |

## 8.4. Открытые вопросы (требуют ответа пользователя)

| # | Вопрос | Влияние | Значение по умолчанию |
|---|---|---|---|
| Q1 | Язык интерфейса: русский или английский? | Все экраны | **Русский** (ТЗ на русском), код и БД — английские |
| Q2 | Есть ли API-ключ DeepSeek для AI-функций? | Этап 6 | Ключ вводится в Settings |
| Q3 | Есть ли почтовый ящик с SMTP/IMAP для кампаний? | Этап 3 | Настраивается через Settings |
| Q4 | Нужен ли Telegram-бот (создание токена через BotFather)? | Этап 8 | Откладывается |
| Q5 | Где хранить аудиофайлы битов: по путям или копировать в библиотеку? | Этап 7 | По путям |
| Q6 | Нужна ли подпись и нотаризация `.app`? | Этап 9 | Позже |

## 8.5. Спайки (обязательные технические проверки)

| ID | Проверка | Критерий успеха | Этап |
|---|---|---|---|
| S1 | PySide6 на Python 3.14: окно, таблица 10k строк, диалог | Запуск без падений, прокрутка плавная | 0 |
| S2 | AppleScript-отправка в Messages | 50 сообщений подряд без ручных действий | 4 |
| S3 | Discord: отправка в канал и DM | Документированные ограничения | 4 |
| S4 | WhatsApp Cloud API: песочница | Отправка шаблона/текста, понимание окна | 4 |
| S5 | macOS Contacts через pyobjc | Чтение контактов после TCC | 1 (опционально) |
| S6 | Аудиосходство: Chromaprint vs ACRCloud | Понятный вывод о применимости | 7 |
| S7 | Spotify: доступность приложения в Development Mode | OAuth и запрос артиста | 2 |
| S8 | Instagram: доступные операции с professional-аккаунтом | Отправка ответа в окне | 4 |

---

# 9. План тестирования

## 9.1. Принципы

1. **Тесты — не пропускаются молча.** Если PostgreSQL недоступен, интеграционные тесты падают с сообщением `TEST_DATABASE_URL не доступен` (иначе «зелёный» прогон врёт).
2. **Схема тестовой БД строится Alembic-ом**, а не `create_all` — тесты проверяют миграции.
3. **Внешние сервисы — только моки** (`respx` для httpx, fake-адаптеры для каналов). Реальных отправок в тестах нет (SPEC §21).
4. **Время инъектируется** — никаких `datetime.now()` в бизнес-логике.
5. **UI-тесты — offscreen**, без скриншотов и без интерактивных окон.

## 9.2. Уровни и структура

| Уровень | Каталог | Что проверяет | Скорость |
|---|---|---|---|
| Unit | `tests/unit/` | нормализация, шаблоны, деньги, merge-правила, enum-валидация | мс |
| Integration | `tests/integration/` | репозитории и сервисы на реальном PostgreSQL, транзакции, уникальные индексы, каскады | секунды |
| Adapters | `tests/adapters/` | контракт `ChannelAdapter` на всех реализациях, mock-HTTP, таймауты, повторы | секунды |
| Migrations | `tests/migrations/` | `upgrade head`, `downgrade -1`, повторный `upgrade` | секунды |
| UI | `tests/ui/` | создание окон, заполнение таблиц, empty-state, отсутствие «мёртвых» кнопок | секунды |

## 9.3. Инфраструктура тестов

```python
# tests/conftest.py — контракт
TEST_DATABASE_URL  # postgresql+psycopg://verse:verse@localhost:5433/verse_test
# 1. session-scoped: создать БД если нет, прогнать alembic upgrade head
# 2. per-test: транзакция + savepoint, откат после теста
# 3. fake_clock: управление временем
# 4. builders: contact(), campaign(), beat() и т.п.
```

Команды: `make test` (unit+integration), `make test-fast` (unit), `make test-ui` (offscreen).

## 9.4. Маппинг обязательных сценариев SPEC §21

| № | Сценарий SPEC | Где проверяется | Ключевая проверка |
|---|---|---|---|
| 1 | Создание контакта | `integration/test_contacts.py` | запись в БД, канал, аудит |
| 2 | Импорт CSV | `integration/test_transfer.py` | маппинг, отчёт, количество строк |
| 3 | Повторный импорт без дублей | `integration/test_transfer.py` | `contact_channels` не растёт, контакт обновляется |
| 4 | Объединение контактов | `integration/test_merge.py` | сообщения/сделки/заметки сохранены, дубли удалены |
| 5 | Назначение статусов | `integration/test_statuses.py` | взаимоисключение в группе с `allows_multiple=false` |
| 6 | Создание напоминания | `integration/test_reminders.py` | `due_at`, состояние, попадание в Dashboard |
| 7 | Создание кампании | `integration/test_campaigns.py` | получатели, шаблон, состояние `draft` |
| 8 | Пауза и продолжение | `integration/test_campaigns.py` | `paused` → `running`, без потери позиции |
| 9 | Повторный запуск без дублей | `integration/test_idempotency.py` | `idempotency_key` блокирует вторую отправку |
| 10 | Исключение Do Not Contact | `integration/test_dnc.py` | DNC-контакт не попадает в кампанию/автоматизацию |
| 11 | Ошибка внешнего API | `adapters/test_email.py`, `test_ai.py` | ошибка изолирована, кампания продолжается |
| 12 | Остановка задания | `integration/test_jobs.py` | отмена в течение N секунд, состояние `cancelled` |
| 13 | Восстановление после перезапуска | `integration/test_recovery.py` | состояние и курсоры сохранены, дублей нет |
| 14 | Бэкап и восстановление | `integration/test_backup.py` | sha256, восстановление в чистую БД |
| 15 | Автоматизации по расписанию | `integration/test_schedule.py` | `missed` при пропуске, без ложных `succeeded` |
| 16 | Доступ к Telegram-боту | `integration/test_telegram_access.py` | чужой `user_id` отклонён |
| 17 | История взаимодействий | `integration/test_interactions.py` | таймлайн, порядок, дедупликация |
| 18 | Недоступность AI API | `adapters/test_ai.py` | приложение работает, ошибка в логах, данные не потеряны |

Дополнительно: миграции (все ревизии), редактирование секретов, валютная арифметика, поиск на 10 000 контактов (< 300 мс).

## 9.5. Политика для UI-тестов

- Проверяется существование и работоспособность экранов, а не пиксели.
- Каждая нереализованная функция отсутствует в навигации — отдельный тест `test_no_dead_navigation`.
- Пустые состояния информативны и не имитируют данные.

## 9.6. Ручные чек-листы

`docs/ACCEPTANCE.md` — по одному разделу на этап, с шагами «нажми/ожидай/проверь», чтобы пользователь мог самостоятельно подтвердить готовность (SPEC §23: «пользователь может проверить её работу самостоятельно»).

## 9.7. Покрытие

Целевые ориентиры: 100 % — доменная логика (нормализация, шаблоны, деньги, merge); ≥ 80 % — сервисы; адаптеры — по контракту. Метрика покрытия — вспомогательная, приоритет у сценариев из 9.4.

---

# 10. Приложения

## 10.1. Зависимости (pinned, проверены на Python 3.14.4 / macOS arm64)

| Пакет | Версия | Назначение |
|---|---|---|
| PySide6-Essentials | 6.12.0 | GUI |
| shiboken6 | 6.12.0 | биндинги Qt |
| SQLAlchemy[asyncio] | 2.1.6 | ORM |
| greenlet | 3.5.6 | требуется асинхронным SQLAlchemy |
| psycopg[binary] | 3.3.6 | драйвер PostgreSQL |
| alembic | 1.20.1 | миграции |
| pydantic | 2.14.2 | DTO и валидация |
| pydantic-settings | 2.16.2 | конфигурация |
| httpx | 0.28.1 | HTTP |
| keyring | 25.7.0 | Keychain |
| pytest | 9.2.0 | тесты |
| pytest-asyncio | 1.4.1 | async-тесты |
| pytest-qt | 4.5.0 | UI-тесты |
| respx | 0.23.1 | моки HTTP |
| openpyxl | — | экспорт/импорт XLSX (проверить при внедрении) |
| pyobjc-framework-Cocoa | 13.0 | iMessage/Contacts (опционально) |

## 10.2. Переменные окружения

```dotenv
# .env.example
APP_ENV=development
DATABASE_URL=postgresql+psycopg://verse:verse@localhost:5433/verse
TEST_DATABASE_URL=postgresql+psycopg://verse:verse@localhost:5433/verse_test
DATA_DIR=~/Library/Application Support/ProjectVerse
LOG_LEVEL=INFO
# Секреты здесь НЕ хранятся — только в macOS Keychain.
# Ключи DeepSeek / Spotify / Telegram вводятся через Settings.
```

## 10.3. Команды

```bash
make db-up        # запуск PostgreSQL (Docker)
make migrate      # alembic upgrade head
make seed         # справочники статусов (идемпотентно)
make run          # запуск приложения
make test         # unit + integration
```

## 10.4. Журнал проверок (источники)

| Проверка | Результат | Источник |
|---|---|---|
| Spotify: закрытие эндпоинтов | Related Artists, Recommendations, Audio Features/Analysis, Featured/Category Playlists недоступны новым приложениям с 27.11.2024 | [Spotify blog](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api) |
| Spotify: поля артиста | `followers`, `genres`, `popularity` — Deprecated; monthly listeners отсутствует | [Web API reference](https://developer.spotify.com/documentation/web-api/reference/get-an-artist) |
| Instagram: инициатива в диалоге | Диалог начинает пользователь; окно ответа ~24 ч | [Instagram Platform](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api) |
| WhatsApp: платформа | Cloud API: текст, медиа, интерактив, звонки | [Meta for Developers](https://developers.facebook.com/docs/whatsapp/cloud-api/overview) |
| DeepSeek: модели и Vision | `deepseek-flash` — Vision поддерживается, `deepseek-v4-pro` — нет | [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing) |
| PySide6 на Python 3.14 | `pip install --dry-run` разрешил все зависимости в бинарных колёсах | локальная проверка, 2026-11-01 |
| Среда | macOS 15.7.9, arm64, 8 ГБ, Python 3.14.4, Docker-демон выключен | локальная проверка, 2026-11-01 |

## 10.5. Соответствие SPEC

| Требование SPEC | Где в плане |
|---|---|
| §1 единая БД, без независимых баз по каналам | Разделы 2.1, 4 |
| §2 стек, локальность, секреты | 2.4, 10.1, ADR-5 |
| §3 навигация | ADR-7, 3 |
| §4 Instagram Discovery | 7.2, этап 2 |
| §5 Spotify Discovery | 7.1, этап 2 |
| §6 CRM | 4.2–4.3, этап 1 |
| §7 кампании, статусы отправки | 4.4, этап 3 |
| §8 каналы | 7.3–7.6, этап 4 |
| §9 автоматизации | 4.5, этап 5 |
| §10 Beat Series | 4.7, этап 5 |
| §11 расписание | 4.5, ADR-9, этап 5 |
| §12 AI | 4.9, 7.8, этап 6 |
| §13 Beat Catalog | 4.7, этап 7 |
| §14 Placements | 7.10, этап 7 |
| §15 Telegram | 4.8, 7.7, этап 8 |
| §16 статистика | 1.1 этапа 1 (Dashboard), этап 5 |
| §17 логи | 4.10, ADR-5 |
| §18 backup | 4.10, этап 8 |
| §19 модель данных | 4 |
| §20 надёжность | ADR-6, 8, 9 |
| §21 тестирование | 9 |
| §22 этапы | 6 |
| §23 критерии готовности | 9.6, приёмка этапов |
| §24 правила ИИ-разработчика | 6 (протокол закрытия этапа) |

## 10.6. Что считается готовым

Функция готова, если одновременно: есть рабочий интерфейс; данные сохраняются в PostgreSQL; обработаны ошибки и таймауты; написаны тесты; функция связана с общей CRM; нет фиктивных результатов; есть инструкция; пользователь может проверить сам (SPEC §23).

---

**Следующий шаг:** реализация этапа 0 (Bootstrap). Код не изменён; документ является планом.
