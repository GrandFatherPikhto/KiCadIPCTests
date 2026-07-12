# Отчёт: аудит KiCadIPCTests + сверка находок по трём репозиториям

Дата: 2026-07-12
Область: `KiCadIPCTests`, `KiCadDecapPlacer`, `KiCadTemplateCloner` (все три — GrandFatherPikhto)
Среда: `kicad-python` (kipy) **0.7.1**, KiCad **10.0.4**

Метод: 1) полное чтение кода всех трёх репозиториев, 2) статическая проверка
контрактов API против реально установленной `kicad-python==0.7.1` (без
живого KiCad — то, что можно доказать одним импортом библиотеки),
3) сверка со строками `logs/test.log` реального прогона `KiCadIPCTests`.

---

## 1. Что уже реализовано в `KiCadIPCTests` (инвентаризация)

| Область | Файл | Статус |
|---|---|---|
| Подключение + кэш соединения на процесс | `core.py` | ✅ реализовано, регрессия — `test_connection_reuse.py` |
| Единая обёртка вызова IPC с таймингом | `core.py: call_ipc()` | ✅ реализовано, используется в `test_full_api.py` |
| Информация о плате (footprints/nets/bbox/слои) | `board_utils.py` | ✅ реализовано |
| Компоненты: reference/value/pads | `component_utils.py` | ✅ реализовано, **не через `board.get_pads()`, а через `footprint.definition.items`** |
| Цепи: имя/код/карта | `net_utils.py` | ✅ реализовано, деprecation `net.code` учтён |
| Путь проекта/схемы | `project_utils.py` | ✅ реализовано |
| Экспорт netlist через `kicad-cli` | `cli_utils.py` | ✅ реализовано, формат `kicadxml` подтверждён |
| Полный обзор классов/методов IPC | `test_full_api.py` | ✅ реализовано: get_items, get_items_by_id/net/netclass, get_connected_items, selection, commit/rollback, save, refill_zones(block=True) |
| Диагностика busy-паттерна | `test_footprints_probe.py` | ✅ реализовано (проба с паузами), но **гипотеза про причину не проверена намеренным воспроизведением** |
| Регрессия на переиспользование соединения | `test_connection_reuse.py` | ✅ реализовано |

**Вывод по пункту 1:** базовый каркас чтения платы и метаданных закрыт
плотно и качественно — логирование без глушения исключений, кэш
соединения, тайминги. Пробелы там, где нужна **запись** (move/rotate/flip/
create) и там, где нужно **намеренно воспроизвести**, а не просто
задокументировать гипотезу.

---

## 2. Сверка с находками `KiCadDecapPlacer` / `KiCadTemplateCloner` — что не было покрыто

| Находка (источник) | Было в `KiCadIPCTests` до аудита? | Добавлено сейчас |
|---|---|---|
| Поворот через `fp.orientation = ...; update_items()` — потенциально бьёт по #21655 | ❌ нет | `mutating/test_footprint_rotation_linkage.py` |
| Флип через `run_action("pcbnew.InteractiveEdit.flip")` + отдельная семантика от `update_items()` | ❌ нет | `mutating/test_flip_then_update_items.py` |
| "Стухший" локальный объект после флипа тихо откатывает изменения (баг, найденный и исправленный в DecapPlacer СЕГОДНЯ) | ❌ нет регрессии | `mutating/test_flip_then_update_items.py` (вариант A/B) |
| `refill_zones(block=False)` как гипотеза причины постоянного busy | ⚠️ упомянуто в README/CHANGES, но не проверено намеренным воспроизведением | `mutating/test_refill_zones_busy_repro.py` |
| Геометрический маппинг pad→footprint (обоснование в README TemplateCloner) | ⚠️ одноразовое наблюдение в логе, не формализовано | `mutating/test_pad_ownership_comparison.py` + статический тест |
| Создание via/track через `board.create_items()` | ❌ нет (только чтение через `test_full_api.py`) | не добавлено в этом проходе — см. §5 «Что осталось не закрыто» |
| Точные имена полей у `Via`/`Angle`/`FootprintInstance` (drill_diameter, .degrees, .layer) | ❌ нет | `static/test_kipy_contract.py` — 12 тестов |
| Семантика copy-vs-reference у getter'ов kipy (`position`, `net`, ...) | ❌ нет, и именно тут найдены самые серьёзные баги | `static/test_kipy_contract.py` |

---

## 3. Новые тесты, добавленные в этом аудите

### 3.1. Статические (не требуют живого KiCad — можно гонять в CI)

`ipc_tests/static/test_kipy_contract.py`, запуск: `python run_static_tests.py`

Проверяют голые факты об установленной библиотеке `kicad-python==0.7.1`:
существование атрибутов/методов, что возвращает getter (копию или
ссылку), что принимает setter. **Прогнано прямо сейчас, результат — 12/12
пройдено** (полный вывод — см. §4, там же смысл каждого).

### 3.2. Живые (требуют запущенного KiCad, НЕ входят в автоматический `test_all.py`)

Размещены в `ipc_tests/mutating/` — по аналогии с диагностическими
скриптами `DecapPlacer/tests/` (`test_move_one_cap.py` и т.п.): по одному,
вручную, с явным refdes тестового компонента, не входят в общий прогон.

| Файл | Что проверяет | Мутирует плату? |
|---|---|---|
| `test_pad_ownership_comparison.py` | `board.get_pads()` (нет владельца) vs `footprint.definition.items` (есть) на реальных данных | Нет, только чтение |
| `test_refill_zones_busy_repro.py` | Намеренная репродукция гипотезы про `refill_zones(block=False)` → постоянный busy | Да — заливка зон; при подтверждении гипотезы плата останется в busy до перезапуска KiCad |
| `test_footprint_rotation_linkage.py` | Поворот конкретного компонента, сравнение состояния пэдов/имени футпринта до/после (косвенная проверка #21655 на PCB-стороне) | Да, с `--revert` |
| `test_flip_then_update_items.py` | Регрессия на баг "стухшего объекта после флипа" — воспроизводит баг (вариант A) и подтверждает фикс (вариант B) | Да, но возвращает исходное состояние в конце |

---

## 4. Полный список находок по API (кто прав, кто нет, с доказательством)

Все строки ниже подтверждены **статически**, кодом `test_kipy_contract.py`,
прогнанным только что (`12/12 passed`), либо **эмпирически**, реальным
логом `KiCadIPCTests/logs/test.log` (прогон `2026-07-12 13:32:26`).

| # | API / приём | Правильно (подтверждено) | Неправильно (кто использует) | Доказательство |
|---|---|---|---|---|
| 1 | Диаметр сверла via | `via.drill_diameter` (плоское поле) | `via.drill.diameter` — **DecapPlacer/create_via читает верно; TemplateCloner extractor.py:99 и applier.py:20 обращаются к несуществующему `.drill`** | статика: `hasattr(Via(),'drill')==False` |
| 2 | Угол поворота в градусах | `fp.orientation.degrees` (свойство) | `fp.orientation.as_degrees()` — **TemplateCloner extractor.py:80** | статика: `hasattr(Angle,'as_degrees')==False` → angle всегда 0.0 |
| 3 | Слой футпринта | `fp.layer` (свойство) | `fp.get_layer()` — **TemplateCloner extractor.py:78** | статика: метода нет → layer всегда хардкод `"F.Cu"` |
| 4 | Изменение позиции | `fp.position = Vector2.from_xy(x, y)` — целиком, через setter (DecapPlacer, IPCTests) | `fp.position.x = x_nm` — **TemplateCloner applier.py:73-74, 17-18** | статика: getter возвращает `Vector2(CopyFrom(...))` — независимая копия; присваивание `.x` копии — **тихий no-op**, без исключения |
| 5 | Назначение цепи на via/track | `via.net = net_obj` — целиком (DecapPlacer create_via) | `via.net.name = net_name` — **TemplateCloner applier.py:23, :39** | статика: тот же паттерн copy-getter — **тихий no-op** |
| 6 | Установка поворота | `fp.orientation = Angle.from_degrees(...)` | `fp.orientation = math.radians(comp.angle)` (сырое число) — **TemplateCloner applier.py:78** | статика: падает `AttributeError: 'float' object has no attribute 'normalize180'` — **не no-op, а мгновенный крэш** на первом же компоненте |
| 7 | Применение транзакции | `commit = board.begin_commit(); ...; board.push_commit(commit, msg)` | `board.push_commit()` без аргументов и без предварительного `begin_commit()` — **TemplateCloner applier.py:92, apply_template()** | статика: `commit` обязателен и позиционен → `TypeError` |
| 8 | Пады с привязкой к владельцу | `footprint.definition.items`, отфильтрованный по `isinstance(item, Pad)` — привязка есть по конструкции запроса | `board.get_pads()` (плоский список) + геометрический nearest-neighbor — **обоснование в README TemplateCloner** | эмпирика: реальный лог показал корректные net-имена (`+3V3`, `+3V3_OSCILL`) через `definition.items`, без единого geometry-вызова; статика подтвердила отсутствие обратной ссылки именно у `board.get_pads()`-пэдов |
| 9 | `refill_zones` default | `block=True` — **это default самой библиотеки** | Кто-то (в раннем непатченом коде) явно передал `block=False, max_poll_seconds=1` | статика: сигнатура `Board.refill_zones(self, block=True, ...)` |
| 10 | `run_action(...)` (флип и т.п.) | Работает, но **официально документирован как unstable API** | Используется как основной механизм флипа в обоих `adapter.py` | статика: docstring `KiCad.run_action` содержит явное `WARNING: unstable API` |
| 11 | `net.code` | Использовать `net.name` для сопоставления | `net.code` работает, но deprecated с 0.4.0 | статика + существующий комментарий в `net_utils.py`, подтверждено декоратором `@deprecated` |
| 12 | Обработка `commit=None` при падении `begin_commit()` | `commit = None` до `try`, `drop_commit` только если `commit is not None` | Старый вариант держал `commit = self.begin_commit()` внутри `try` — маскировал `UnboundLocalError` | Подтверждено комментарием в `commit_with_retry` (DecapPlacer, фикс от 2026-07-12); не переисследовано статически в этом проходе |

### Системный вывод по строкам 1, 4, 5, 6, 7

Это не набор случайных опечаток — это **один и тот же системный анти-паттерн**
в `TemplateCloner` (унаследованном от `DecapPlacer`, но с ошибками при
переносе): попытка мутировать объект, полученный через **getter**, вместо
переприсвоения через **setter**. У kipy 0.7.1 практически все составные
поля (`position`, `net`, `orientation`, `drill`-подобные) — это getter'ы,
которые оборачивают **копию** protobuf-сообщения (`CopyFrom`), а не живую
ссылку. Правило одно: **если поле составное — переприсваивай целиком**.
`KiCadDecapPlacer` (и, соответственно, места в `KiCadTemplateCloner`,
скопированные из него без изменений — `create_via`, `flip_selected`,
`commit_with_retry`) следуют этому правилу верно. Код, дописанный поверх
(`extractor.py`, `applier.py`) — нет.

### Практическое следствие

`template_cloner place` (`applier.py: apply_template`) в текущем виде:
1. Не двигает ни один компонент (п. 4 — no-op).
2. Падает с `AttributeError` на первом же компоненте из-за строки поворота
   (п. 6) — **до** создания via/track и до commit.
3. Даже если бы дошёл дальше — via/track не создались бы (drill/net — п. 1, 5),
   и `push_commit()` в конце упал бы с `TypeError` (п. 7).

Это стоит знать до того, как `place` будет опробован на реальной плате —
сейчас команда не рабочая, а не "рабочая, но с нюансами".

---

## 5. Что осталось не закрыто (честно, без прикрас)

- **Создание via/track через `create_items()`** — в `KiCadIPCTests` нет
  своего теста (только чтение проверено в `test_full_api.py`). У
  `DecapPlacer` есть рабочий диагностический `tests/test_create_one_via.py`
  с верными полями — его стоит перенести в `ipc_tests/mutating/` как
  постоянный регрессионный тест, а не разовый скрипт. Не сделано в этом
  проходе из-за объёма — если нужно, сделаю следующим шагом.
- **Истинная проверка #21655** (связь symbol↔footprint в схеме) —
  IPC в KiCad 9/10 не даёt доступа к редактору схем в принципе (это уже
  зафиксировано как ограничение в памяти о `kipy`), так что
  `test_footprint_rotation_linkage.py` проверяет только PCB-сторону
  (пэды/net остались теми же). Настоящую проверку нужно делать руками:
  Update PCB from Schematic после поворота, смотреть на предупреждения.
- **`commit_with_retry` (п. 12 таблицы)** — не переисследовано статически;
  сам паттерн (commit=None до try) корректен и его несложно формализовать
  отдельным static-тестом (проверка, что `begin_commit()` реально может
  бросить исключение до присваивания) — не сделано, чтобы не раздувать
  и так большой объём.
- Три новых `mutating`-теста **не прогнаны на реальном KiCad** — это
  физически невозможно из моей среды (нет GUI, нет живого KiCad). Они
  проверены на компиляцию и импорт, написаны строго по паттернам,
  подтверждённым в уже работавшем коде (`test_move_one_cap.py`,
  `test_create_one_via.py`, логи реальных прогонов) — но финальная
  проверка результата всё равно за тобой, на Windows.

---

## 6. Файлы, добавленные в репозиторий

```
KiCadIPCTests/
├── run_static_tests.py                              # новый — точка входа
├── ipc_tests/
│   ├── static/
│   │   ├── __init__.py                              # новый
│   │   └── test_kipy_contract.py                    # новый — 12 тестов, 12/12 pass
│   └── mutating/
│       ├── __init__.py                              # новый
│       ├── test_pad_ownership_comparison.py         # новый, безопасен (read-only)
│       ├── test_refill_zones_busy_repro.py          # новый, МУТИРУЕТ (заливка зон)
│       ├── test_footprint_rotation_linkage.py        # новый, МУТИРУЕТ (поворот, есть --revert)
│       └── test_flip_then_update_items.py            # новый, МУТИРУЕТ (флип, восстанавливает сам)
└── AUDIT_REPORT.md                                    # этот файл
```

## 7. Рекомендуемый порядок прогона на Windows

```bash
# 1. Ничего не трогает, живой KiCad не нужен — гонять хоть в CI
python run_static_tests.py

# 2. Обычный набор, живой KiCad нужен, ничего не мутирует
python run_all_tests.py

# 3. По одному, вручную, на тестовом компоненте (например C401 —
#    декаплинг-конденсатор с тестовой платы test_boards/10CL006YE144C8G)
python -m ipc_tests.mutating.test_pad_ownership_comparison
python -m ipc_tests.mutating.test_footprint_rotation_linkage C401 --angle-deg 45
python -m ipc_tests.mutating.test_footprint_rotation_linkage C401 --revert
python -m ipc_tests.mutating.test_flip_then_update_items C401

# 4. Последним, и только когда не жалко положить сессию KiCad —
#    если гипотеза подтвердится, плата зависнет в busy до перезапуска KiCad
python -m ipc_tests.mutating.test_refill_zones_busy_repro
```
