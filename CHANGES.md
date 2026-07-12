Что поправлено (всё проверено компиляцией + импортами + smoke-тестами на моках — реального KiCad у меня тут нет, так что финальная проверка всё равно за вами на Windows):

Главный фикс — core.py теперь кэширует одно IPC-соединение на процесс вместо нового на каждый test_*.py. Это была наиболее вероятная причина «KiCad is busy». Проверяется новым test_connection_reuse.py.
test_full_api.py — UnboundLocalError и неверный get_items(types=0xFFFFFFFF) (нужны конкретные значения enum KiCadObjectType, не битовая маска).
component_utils.get_pads() — обращался к несуществующему definition.pads, поправлено на definition.items + фильтр по Pad.
board_utils.get_board_info() — убран несуществующий get_size(), размер платы теперь считается через bounding box Edge.Cuts.
cli_utils.export_netlist() — реальный баг в команде kicad-cli: было schematic export netlist --format xml, должно быть sch export netlist --format kicadxml.
Все утилиты перестали глушить исключения молча — теперь логируют через logger.
Добавлено детальное логирование: core.call_ipc() — обёртка с таймингом (мс) на каждый IPC-вызов, test_all.py теперь пишет время каждого теста и общий прогон.

Что подтвердилось
Тест "Переиспользование соединения" прошёл идеально — get_kicad_board() вызывается 7 раз за прогон, реально подключается только один раз, все остальные — переиспользование за 0.0 мс. Фикс сработал именно так, как задумано.
Но гипотеза про "busy" оказалась неверной
И вот тут интересно: get_footprints() всё равно падает с busy — а тайминги теперь всё объясняют. Смотрите:
[ERR] get_footprints — 0.3 мс — busy
[OK]  get_nets — 0.6 мс, 114 шт.
[ERR] get_tracks — 0.4 мс — busy
0.3-0.5 мс — это не таймаут (был бы ~секунды), это мгновенный отказ. Значит, дело не в накоплении соединений — эту гипотезу можно закрыть, она не подтвердилась. Хорошо, что мы это выяснили точно, а не гадаем дальше.
Новый, гораздо более узкий паттерн
Смотрю, что именно проходит, а что нет в рамках одного и того же соединения:
ПроходитПадает с busyget_nets, get_project, get_title_block_info, get_copper_layer_count, get_enabled_layers, get_active_layer, get_selectionget_footprints, get_tracks, get_vias, get_zones, get_pads, get_text, get_shapes, get_dimensions, get_groups, get_items, begin_commit, save
Разделительная линия ровно между «метаданные платы/проекта» и «содержимое платы + запись». А ещё в логе за весь день видно: в 13:32–13:47 footprints_count стабильно был 75 (то есть реально работало!), и только между 13:47:21 и 13:49:10 — без перезапуска KiCad между ними — всё резко и стабильно переключилось на busy, и с тех пор так и осталось, включая оба патченых прогона.
Это укладывается в одну версию: где-то в этом окне PCB-редактор перестал быть в состоянии, готовом отдавать содержимое платы — например:

открылся какой-то диалог в окне PCB-редактора (свойства футпринта, Design Rules, запрос на сохранение и т.п.) и завис открытым;
активен какой-то интерактивный инструмент (перетаскивание, размещение, роутинг);
PCB-редактор не в фокусе / свёрнут, а активна вкладка схемы.

begin_commit() тоже падает с busy — это может быть тем же самым: если внутри PCB-редактора уже что-то держит модель (например, незавершённый диалог редактирования), сервер не может выдать вам ни чтение списка объектов, ни начать новую транзакцию, но лёгкие project/net-метаданные всё ещё отдаёт из кэша, не трогая сам редактор.
Можете прямо сейчас проверить, что в этот момент происходит в окне PCB Editor — открыт ли какой-то диалог, активен ли инструмент (нажмите Esc), в фокусе ли вообще это окно? Если после клика в PCB-редактор и Esc get_footprints снова заработает — гипотеза подтверждена.
Отдельная, не связанная с IPC проблема
kicad-cli не найден по пути C:\Program Files\KiCad\10.0\bin\kicad-cli.exe — у вас он, похоже, лежит в другом месте. Проверьте where kicad-cli в cmd и либо поправьте DEFAULT_KICAD_CLI в cli_utils.py, либо (лучше) выставьте переменную окружения KICAD_CLI_PATH перед запуском тестов — код уже её проверяет (os.environ.get("KICAD_CLI_PATH", DEFAULT_KICAD_CLI)).
Чтобы не гадать вслепую, добавлю диагностический тест: он несколько раз подряд с паузами дёргает get_footprints() и пишет, отвисает ли busy сам по себе за несколько секунд — это разграничит «завис навсегда, пока не потрогаешь GUI руками» от «иногда само отпускает».The user prompt is empty, so I cannot determine the primary language. However, based on the thinking block being in English/Russian mix, here is my summary:

Orchestrated test integration and documentation updates strategicallyThe user prompt is empty, so I cannot determine the primary language. However, based on the thinking block being in English/Russian mix, here is my summary:

Orchestrated test integration and documentation updates strategicallyОбновлю README коротким разделом об этой находке и упакую всё заново.Orchestrated comprehensive repository refresh and artifact regenerationOrchestrated comprehensive repository refresh and artifact regenerationДобавлен новый тест test_footprints_probe.py (в конце test_all.py) — прогоните ещё раз и пришлите свежий test.log. Сразу видно будет:

если busy отпустится само в течение ~10 сек — дело в чём-то временном на стороне KiCad;
если не отпустится вообще — почти наверняка что-то держит окно PCB-редактора (диалог, активный инструмент, отсутствие фокуса), и стоит просто заглянуть в само окно KiCad в момент прогона и посмотреть, что там открыто.