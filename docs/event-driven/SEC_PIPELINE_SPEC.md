# SEC Event Pipeline — спецификация

Статус: spec, НЕ код. Документ описывает, что должен делать инженер.
Цель: один инженер реализует за неделю.

Связанные документы:
- EVENT_DRIVEN_LANDSCAPE.md — зачем и какие события
- RANKING_AND_RECOMMENDATION.md — приоритеты и план

## 0. Принципы, вытекающие из измерений

Эти четыре пункта — не пожелания, а следствия того, что реально проверено
в этой сессии. Нарушение любого из них приведёт к тихой поломке пайплайна.

1. **Не строить пайплайн на `browse-edgar?action=getcompany` без `company`.**
   Проверено: такой запрос возвращает валидный Atom с нулём записей. Молчаливый
   отказ, который легко принять за «нет событий».
2. **Основной источник — EDGAR full-text search (FTS) для обнаружения
   и submissions API для проверки истории по конкретному эмитенту.**
   FTS: https://efts.sec.gov/LATEST/search-index
   Submissions: https://data.sec.gov/submissions/CIK##########.json
3. **Считать уникальные CIK, а не filings.** Проверено на 10-12B: из 9
   записей за 60 дней 4 были amendments одного и того же MSGS Spinco.
   Наивный count даёт завышение в разы.
4. **Каждый запрос — с идентифицирующим User-Agent.** SEC требует контакт
   в заголовке; без него возможны блокировки. Формат:
   `User-Agent: <project> research <contact-email>`

## 1. Что скачиваем

| Форма | Роль | Ожидаемый объём (измерено, 12м) |
|---|---|---|
| 8-K | announcement (merger, chapter 11, HSR) | профильно: 4,852 по «Agreement and Plan of Merger», 1,583 по HSR, 911 по chapter 11 |
| DEFM14A | merger proxy = сделка идёт к голосованию | 269 |
| 10-12B (+ /A) | регистрация spin-off | 56 |
| SCHEDULE 13D (+ /A) | activist stake | 5,437 (family) |
| DEFA14A | дополнительные proxy-материалы | не считалось; использовать как обогащение |

Приоритет реализации: **10-12B (spin-off) → 8-K merger → DEFM14A → 13D**.
DEFA14A — последним, это обогащение, а не сигнал.

## 2. Периодичность

Один запуск в сутки, **18:00 UTC** (конец рабочего дня SEC, после закрытия
американских рынков). Обоснование: цены yfinance для обогащения нужны
EOD, а filings за день к этому моменту полностью опубликованы.

Дополнительно: ручной запуск с параметром `--backfill YYYY-MM-DD YYYY-MM-DD`
для исторической выборки (нужно на Week 2 плана).

Опционально (Week 4+): intraday-опрос каждые 30 минут в торговые часы
для spin-off/13D, где важна скорость. **Не делать на Week 1** — усложняет
отладку, а сигналы не intraday.

## 3. Storage: SQLite `event_filings`

Файл: `data/event_filings.db` (в `.gitignore`, не коммитить).

### 3.1 Основная таблица

    CREATE TABLE event_filings (
        id            INTEGER PRIMARY KEY,
        filing_type   TEXT NOT NULL,      -- '8-K','DEFM14A','10-12B','SCHEDULE 13D','DEFA14A'
        form_raw      TEXT NOT NULL,      -- как пришло из EDGAR: '10-12B/A','SCHEDULE 13D/A'
        cik           TEXT NOT NULL,      -- zero-padded 10 digits: '0001818201'
        ticker        TEXT,               -- из company_tickers.json, NULL если нет
        company_name  TEXT,
        filing_date   TEXT NOT NULL,      -- 'YYYY-MM-DD'
        accession_no  TEXT NOT NULL,      -- '0001193125-26-422320'
        primary_doc   TEXT,               -- 'd140608d8k.htm'
        url           TEXT NOT NULL,      -- полный URL документа
        event_type    TEXT,               -- merger|spin_off|activist|antitrust|chapter11|unknown
        event_conf    REAL,               -- уверенность 0..1
        summary_text  TEXT,               -- 1-3 предложения вокруг сигнала
        raw_json      TEXT,               -- исходный _source из FTS для отладки
        ingested_at   TEXT NOT NULL,      -- ISO timestamp
        UNIQUE(accession_no, primary_doc)
    );

Ключевое: `UNIQUE(accession_no, primary_doc)` делает пайплайн идемпотентным.
Повторный запуск за тот же день не создаёт дублей.

### 3.2 Вспомогательные таблицы

Справочник тикеров (обновлять раз в неделю, ~10,443 записи):

    CREATE TABLE ticker_map (
        cik     TEXT PRIMARY KEY,
        ticker  TEXT,
        title   TEXT,
        updated_at TEXT
    );

Обогащение ценами (заполняется асинхронно, T+1/T+5/T+30):

    CREATE TABLE price_reaction (
        id           INTEGER PRIMARY KEY,
        filing_id    INTEGER NOT NULL REFERENCES event_filings(id),
        ticker       TEXT NOT NULL,
        t0_date      TEXT,   -- торговый день до/в день filing
        close_t0     REAL,
        close_t1     REAL,
        close_t5     REAL,
        close_t30    REAL,
        ret_t1       REAL,   -- (close_t1/close_t0 - 1)
        ret_t5       REAL,
        ret_t30      REAL,
        adv_60d_usd  REAL,   -- средний ADV за 60 торговых дней до filing
        computed_at  TEXT
    );

Поле `adv_60d_usd` обязательно: без него нельзя применить правило
«позиция не более 5% ADV», а оно — главный ограничитель capacity.

### 3.3 Служебная таблица для идемпотентности backfill

    CREATE TABLE ingest_runs (
        id         INTEGER PRIMARY KEY,
        run_type   TEXT,     -- 'daily'|'backfill'
        started_at TEXT,
        finished_at TEXT,
        window_from TEXT,
        window_to   TEXT,
        n_found    INTEGER,
        n_inserted INTEGER,
        n_errors   INTEGER,
        notes      TEXT
    );

## 4. Пайплайн: шаг за шагом

### Шаг 1 — Обновить ticker_map

Источник: https://www.sec.gov/files/company_tickers.json (проверено, 10,443
записи, 799 KB). Запускать раз в неделю, не ежедневно.

Маппинг нужен, потому что FTS отдаёт `ciks` и `display_names`, но не всегда
даёт чистый ticker. `display_names` имеет формат
`"CCC Intelligent Solutions Holdings Inc.  (CCC)  (CIK 0001818201)"` —
ticker парсится regex `\(([A-Z][A-Z0-9.\-]{0,9})\)`, но надёжнее брать
из официального маппинга по CIK.

### Шаг 2 — Обнаружение событий (FTS)

Запрос на каждую форму за окно [сегодня-1, сегодня]:

    GET https://efts.sec.gov/LATEST/search-index
        ?q=<query>
        &forms=<FORM>
        &dateRange=custom
        &startdt=<YYYY-MM-DD>
        &enddt=<YYYY-MM-DD>

Проверенные значения `forms` (важно: именно так, как принимает API):
- `8-K`
- `DEFM14A`
- `10-12B`
- `SCHEDULE 13D`  — НЕ «SC 13D» (это даёт 0)
- `SCHEDULE 13D/A`
- `DEFA14A`

Для 8-K использовать `q` как полнотекстовый фильтр:
- merger: `"Agreement and Plan of Merger"`
- chapter11: `"chapter 11"`
- antitrust: `"second request"` или `"Hart-Scott-Rodino"`

`q` для 10-12B / DEFM14A / 13D оставить пустым — форма сама достаточно
специфична, а текстовый фильтр только навредит.

Ответ: JSON, `hits.hits[]._source` содержит:
`ciks[]`, `display_names[]`, `form`, `file_date`, `adsh` (accession),
`file_type`, `_id` (вида `0001193125-26-422320:d140608d8k.htm`).

**Важно: 429 и троттлинг.** Между запросами пауза не менее 0.2 сек.
При 429 — экспоненциальный backoff (2s, 4s, 8s, максимум 3 попытки).

### Шаг 3 — Дедупликация по CIK для spin-off

Специфично для 10-12B: если в окне есть несколько filings одного CIK,
это amendments. Правило:

- для каждого CIK берём **самый ранний filing в истории** как
  `spin_off_registered` (событие);
- последующие `/A` не создают нового события, а обновляют
  `summary_text` и `event_conf` существующей записи;
- в `event_filings` сохраняем все, но `event_type='spin_off'` ставим
  только первому, остальным — `event_type='spin_off_amend'`.

Для 13D аналогично: первичный `SCHEDULE 13D` → `activist_new`,
`SCHEDULE 13D/A` → `activist_amend`.

### Шаг 4 — Извлечение деталей (только для отобранных)

Полный текст документа качать **не для всех** filings, а только для тех,
где `event_type` входит в whitelist. Иначе объём вырастет на порядки.

URL строится детерминированно:
    https://www.sec.gov/Archives/edgar/data/<cik_int>/<accession_no_без_дефисов>/<primary_doc>

Пример (проверено): CCC, CIK 0001818201, accession 0001193125-26-422320,
документ d140608d8k.htm →
    https://www.sec.gov/Archives/edgar/data/1818201/000119312526422320/d140608d8k.htm

Обратите внимание: CIK в URL — без ведущих нулей, accession — без дефисов.
Это надо делать явно, это не очевидно и легко ошибиться.

### Шаг 5 — Regex для типа события

Ниже — рабочая отправная точка, а НЕ окончательный набор. Каждый паттерн
требует ручной валидации на выборке.

merger (8-K):
    Item\s+1\.01[^.]{0,200}(Agreement and Plan of Merger|Merger Agreement)
    (?i)(entered into|execution of).{0,80}(Merger|merger) Agreement
    (?i)per share in cash

Цена сделки (хрупко!):
    (?i)receive\s+\$\s?([\d,]+\.\d{2})\s+per\s+share
    (?i)Per Share Price[^.]{0,120}\$\s?([\d,]+\.\d{2})
    (?i)Merger Consideration[^.]{0,200}\$\s?([\d,]+\.\d{2})

Проверенный пример: в 8-K CCC фраза была
«will be converted into the right to receive $7.75 per share in cash,
without interest (the "Per Share Price")». Оба паттерна выше её ловят.
**Но рассуждение про «consideration» в контексте financing дало ложное
срабатывание на первом парсинге** — поэтому брать не первое совпадение
`Merger Consideration`, а искать в 300 символах после него символ `$`.

spin_off (10-12B):

    (?i)spin[- ]?off
    (?i)separation and distribution agreement
    (?i)record date.{0,100}distribution

activist (13D):
    (?i)purpose of transaction
    (?i)(may engage in|intends to engage in).{0,200}(discussions|negotiations)
    (?i)seek(ing)?\s+(to\s+)?(representation|board seats?)

Классификация «активист vs не-активист» (VC, пассивный держатель) по regex
**ненадёжна**. Правило: если filer есть в трекере активистов — activist;
иначе — flag_manual на ручной разбор. Не пытаться решить это автоматически.

chapter11 (8-K):
    Item\s+1\.03
    (?i)voluntary petition.{0,80}chapter\s+11
    (?i)commenced.{0,80}chapter\s+11

antitrust (8-K):
    (?i)second\s+request
    (?i)Hart-Scott-Rodino
    (?i)waiting\s+period.{0,80}(expired|terminated)

### Шаг 6 — summary_text

Не суммаризация NLP. Простое извлечение: 1-2 предложения вокруг первого
совпадения паттерна (окно ±200 символов), с нормализацией пробелов и
удалением тегов. Этого достаточно для ручного триажа и для alerting.
Полноценная суммаризация — Week 3+, если понадобится.

### Шаг 7 — Обогащение ценами (yfinance)

Для каждой записи с `ticker`:

1. Скачать дневные цены за [filing_date − 90 дней, filing_date + 35 дней]
   (нужно для ADV-60d и для T+30).
2. `close_t0` — close последнего торгового дня **до или в** filing_date.
   Тонкость: если filing пришёл до открытия — T0 это день filing;
   если после закрытия — следующий торговый день. Для дневной стратегии
   это приемлемое упрощение, отметить в отчёте.
3. `ret_t1 = close_t1/close_t0 − 1`, аналогично t5, t30.
4. `adv_60d_usd` = среднее(volume × close) за 60 торговых дней до filing.

Технические заметки:
- yfinance 1.7.0 в `.venv` работает (проверено); **raw curl к
  query1.finance.yahoo.com возвращает 429** — использовать только библиотеку.
- Тикеры вида `BRK.B` yfinance ожидает как `BRK-B`; нормализацию сделать
  явной (replace('.', '-')).
- Для не-торгуемых эмитентов (spinoff до отделения, как MSGR) тикера нет —
  `price_reaction` не заполняется, запись остаётся.

### Шаг 8 — Alerting

Файл: `data/alerts.txt` (append-only, не в git).

Правила (пороговые значения — стартовые, калибровать):

    если n_events_за_день > 20           -> ALERT: необычный объём
    если event_type=spin_off и это новый CIK -> ALERT: новый spin-off
    если event_type=activist_new и filer в трекере -> ALERT: активист из трекера
    если event_type=merger и spread > 5% (после обогащения) -> ALERT: широкий спред
    если 3 дня подряд n_errors > 0       -> ALERT: пайплайн деградировал

Формат строки:
    YYYY-MM-DDTHH:MM:SSZ | LEVEL | event_type | ticker | cik | url | note

Alerting — это файл, а не Slack/email, на Week 1. Интеграция с уведомлениями
(`src/pipeline/notify.py` уже существует в репозитории) — Week 3+.

## 5. Обработка ошибок

| Ситуация | Действие |
|---|---|
| HTTP 429 от SEC | backoff 2/4/8с, макс 3 попытки, потом записать в n_errors и продолжить |
| HTTP 403 | остановить прогон, проверить User-Agent, не ретраить слепо |
| Пустой ответ FTS | это НЕ ошибка — выходной день; логировать n_found=0 |
| yfinance вернул пустой DataFrame | записать ticker в `price_reaction` с NULL-полями, повторить на следующем прогоне |
| CIK отсутствует в ticker_map | `ticker=NULL`, не отбрасывать запись (это может быть приватная компания) |
| Документ не скачался | сохранить запись без `summary_text`, пометить для повтора |

Ключевое правило: **пайплайн не падает целиком из-за одного сбойного
filings**. Каждый шаг пишет ошибку в `ingest_runs.n_errors` и продолжает.

## 6. Оценка трудозатрат (1 инженер)

| Задача | Оценка |
|---|---|
| FTS-клиент + backoff + модели данных | 1.0 дня |
| SQLite-схема + идемпотентная вставка | 0.5 дня |
| ticker_map + submissions API клиент | 0.5 дня |
| Regex-набор + извлечение summary_text | 1.1 дня |
| yfinance-обогащение + ADV | 0.7 дня |
| Alerting + ingest_runs | 0.5 дня |
| Ручная валидация на 50 filings | 1.0 день |
| Буфер на непредвиденное | 0.7 дня |

Итого: **~6 рабочих дней**, один инженер. Это укладывается в Week 1
с запасом на ревью.

## 7. Что НЕ входит в scope недели 1

- NLP-классификация (spaCy/LLM) — regex достаточно для отбора, ручной
  триаж на 20-40 событиях в неделю реален.
- Trading integration — это research, торговля отдельно.
- Intraday polling — после того как дневной пайплайн стабилен.
- Парсинг полных текстов merger agreement (условия закрытия, MAC-клаузы) —
  это Week 2-3, и делать это надо вручную на отобранных сделках.

## 8. Критерии готовности Week 1

1. Прогон за исторический месяц (2026-09-01..2026-09-30) заполняет
   `event_filings` без ошибок, `n_errors=0`.
2. Повторный прогон за тот же период не добавляет строк (идемпотентность).
3. На выборке 50 записей ручная проверка `event_type` даёт точность ≥ 90%.
4. `price_reaction.adv_60d_usd` заполнен для ≥ 80% записей с тикером.
5. Три живых примера из этой итерации корректно распознаются:
   CCC (merger, $7.75), MSGS Spinco (spin_off), Shah Capital NVAX/VEON (activist).

## 9. Приложение: проверенные значения для отладки

    # FTS: 8-K с merger agreement за 12 месяцев -> 4852
    q="Agreement and Plan of Merger"&forms=8-K
    startdt=2025-10-01&enddt=2026-10-01

    # FTS: DEFM14A за 12 месяцев -> 269
    q=&forms=DEFM14A&startdt=2025-10-01&enddt=2026-10-01

    # FTS: 10-12B за 12 месяцев -> 56
    q=&forms=10-12B&startdt=2025-10-01&enddt=2026-10-01

    # FTS: SCHEDULE 13D за 12 месяцев -> 5437
    q=&forms=SCHEDULE 13D&startdt=2025-10-01&enddt=2026-10-01

    # FTS: chapter 11 в 8-K -> 911
    q="chapter 11"&forms=8-K&startdt=2025-10-01&enddt=2026-10-01

    # submissions API: CCC -> 586 recent filings, tickers=['CCC']
    https://data.sec.gov/submissions/CIK0001818201.json

    # ticker map: 10,443 записи
    https://www.sec.gov/files/company_tickers.json

Если после реализации числа радикально расходятся с этими — сначала
проверить формат дат (startdt/enddt должны быть YYYY-MM-DD) и наличие
кавычек в `q` для фразовых запросов. Запрос `q=chapter 11` без кавычек
даст совершенно другой результат, чем `q="chapter 11"`.
