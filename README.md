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