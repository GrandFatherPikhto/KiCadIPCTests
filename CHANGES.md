Что поправлено (всё проверено компиляцией + импортами + smoke-тестами на моках — реального KiCad у меня тут нет, так что финальная проверка всё равно за вами на Windows):

Главный фикс — core.py теперь кэширует одно IPC-соединение на процесс вместо нового на каждый test_*.py. Это была наиболее вероятная причина «KiCad is busy». Проверяется новым test_connection_reuse.py.
test_full_api.py — UnboundLocalError и неверный get_items(types=0xFFFFFFFF) (нужны конкретные значения enum KiCadObjectType, не битовая маска).
component_utils.get_pads() — обращался к несуществующему definition.pads, поправлено на definition.items + фильтр по Pad.
board_utils.get_board_info() — убран несуществующий get_size(), размер платы теперь считается через bounding box Edge.Cuts.
cli_utils.export_netlist() — реальный баг в команде kicad-cli: было schematic export netlist --format xml, должно быть sch export netlist --format kicadxml.
Все утилиты перестали глушить исключения молча — теперь логируют через logger.
Добавлено детальное логирование: core.call_ipc() — обёртка с таймингом (мс) на каждый IPC-вызов, test_all.py теперь пишет время каждого теста и общий прогон.