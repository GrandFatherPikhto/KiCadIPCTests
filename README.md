# IPC Тесты для KiCad 10

Набор модульных тестов для проверки работоспособности IPC API KiCad 10 через библиотеку `kipy`.

## Структура
- `core.py` – подключение и логирование
- `board_utils.py`, `component_utils.py`, `net_utils.py`, `project_utils.py` – утилиты
- `cli_utils.py` – работа с kicad-cli
- `tests/` – сами тесты
- `logs/` – каталог для логов (создаётся автоматически)

## Запуск
```bash
python run_all_tests.py
```

## Изменения от 2026-07-12

По логам первого прогона (`logs/test.log`) нашлись и исправлены реальные баги:

1. **Главная причина `"KiCad is busy"` на большинстве тестов**: каждый
   `test_*.py` открывал НОВОЕ IPC-подключение через `get_kicad_board()`, ни
   одно из них не закрывалось (`kipy.KiCad` в 0.7.1 не имеет `close()`), и
   к моменту тяжёлых тестов на плате скапливалось 7-8 незакрытых сокетов.
   `core.get_kicad_board()` теперь кэширует одно соединение на процесс и
   переиспользует его (с автоматическим переподключением, если оно
   протухло). Проверяется тестом `test_connection_reuse.py`.
2. `test_full_api.py`: `UnboundLocalError` из-за необъявленных переменных
   при исключении внутри `try`, и неверный вызов `board.get_items(types=
   0xFFFFFFFF)` — `types` это значения enum `KiCadObjectType`, а не битовая
   маска.
3. `component_utils.get_pads()` обращался к несуществующему
   `footprint.definition.pads` (в 0.7.1 это `definition.items`,
   отфильтрованный по `isinstance(item, Pad)`).
4. `board_utils.get_board_info()` вызывал несуществующий `board.get_size()`
   — размер платы теперь считается через bounding box контура `Edge.Cuts`.
5. `cli_utils.export_netlist()`: команда `kicad-cli` была
   `schematic export netlist` (не существует) с форматом `xml` (тоже не
   существует) — исправлено на `sch export netlist --format kicadxml`.
   Плюс ошибки `kicad-cli` (stdout/stderr) теперь логируются, а не
   проглатываются.

Во всех утилитах ошибки больше не глушатся молча (`except: return []`) —
они логируются через параметр `logger`, что раньше маскировало настоящие
причины под безобидным «Нет компонентов».

Добавлено подробное логирование: `core.call_ipc()` — обёртка для вызова
любого метода IPC с таймингом (мс) и единообразным `[OK]`/`[ERR]` в логе;
`test_all.py` теперь пишет время каждого теста и общее время прогона.