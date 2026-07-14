# core_api — надёжные обёртки для IPC KiCad 10

`core_api` — это **дистиллированный, проверенный на живом KiCad 10.0.4** набор тонких обёрток над библиотекой `kicad-python` (kipy 0.7.1).  
Пакет предоставляет **удобный и безопасный** интерфейс для автоматизации PCB-редактора через IPC, скрывая все известные подводные камни и неочевидные контракты kipy.

---

## 📦 Состав пакета

Каждый модуль отвечает за одну предметную область:

| Модуль | Назначение |
|--------|------------|
| `kicad_client` | Подключение к запущенному KiCad, получение платы, выполнение GUI-действий (`run_action`), получение версии |
| `board` | Обновление платы (`refresh`), управление транзакциями (`begin_commit`, `push_commit`, `drop_commit`), безопасный коммит с повторными попытками (`commit_with_retry`) |
| `footprints` | Поиск футпринтов по `refdes`, чтение свойств (позиция, угол, слой, размер), изменение позиции/угла, **настоящий флип** через GUI-экшен |
| `pads` | Получение падов компонента, их координат (абсолютных), размера, имени цепи и угла |
| `vias` | Создание переходных отверстий (`make`), удаление по UUID (`remove_by_id`) |
| `zones` | Поиск зон по имени, получение точек контура |
| `nets` | Получение всех цепей или поиск по имени |
| `selection` | Работа с выделением: UUID выделенных объектов (с учётом групп), фильтрация футпринтов, получение сводной информации по выделенным компонентам |
| `geometry` | Константа перевода мм↔нм (`MM`), хелперы для создания `Vector2` из мм, преобразования в мм, получения размера `Box2` в мм |

---

## ⚙️ Установка и требования

- Python 3.8+
- Библиотека `kicad-python` (kipy) **0.7.1** (устанавливается из репозитория KiCad)
- KiCad 10.0.4 с открытым **PCB-редактором** (IPC не работает в headless-режиме в версии 10)

Установка самой библиотеки kipy обычно выполняется через pip из официального репозитория или сборкой из исходников – следуйте инструкциям KiCad.

---

## 🔌 Подключение

```python
from core_api import kicad_client

# Подключиться к запущенному KiCad (таймаут 20 секунд)
kicad = kicad_client.connect(timeout_ms=20000)

# Получить текущую плату
board = kicad_client.get_board(kicad)

# Проверить версию
print(kicad_client.get_version(kicad))
```

**Важно:** `kicad_client.connect()` возвращает объект `KiCad`, который не имеет метода `close()`. Рекомендуется **переиспользовать** одно соединение на весь процесс (например, через глобальную переменную или синглтон). Пакет `ipc_tests` демонстрирует такой подход с кэшированием.

---

## 🧠 Основные концепции

### Транзакционная модель

Все изменения платы должны выполняться **внутри транзакции**:

1. `begin_commit()` → получаем `commit`-объект
2. Изменяем объекты (позиции, углы, создаём/удаляем элементы)
3. Применяем изменения: `update_items()`, `create_items()`, `remove_items_by_id()`
4. Фиксируем: `push_commit(commit, description)`
5. В случае ошибки: `drop_commit(commit)` (откат)

Без транзакции изменения не будут видны на плате.

### Объекты-копии vs ссылки

В `kipy` все геттеры (`.position`, `.net`, `.orientation` и т.п.) возвращают **копии** внутренних данных, а не ссылки.  
Это означает, что следующий код **НЕ РАБОТАЕТ**:

```python
fp.position.x = 1000000   # меняет копию, не влияет на объект
```

Единственный способ изменить свойство – **переприсвоить весь объект целиком**:

```python
from kipy.geometry import Vector2
fp.position = Vector2.from_xy(1_000_000, 2_000_000)
```

Аналогично для `.net`, `.orientation` и т.д. Вся `core_api` построена с учётом этого правила.

### Обновление объектов после изменения

Если вы изменили свойства футпринта (`position`, `orientation`), эти изменения останутся **локальными** до тех пор, пока вы не вызовете `board.update_items([fp])` **внутри транзакции**:

```python
from core_api import board as board_api

commit = board_api.begin_commit(board)
fp.position = Vector2.from_xy(новый_x, новый_y)
board.update_items([fp])
board_api.push_commit(board, commit, "Переместил компонент")
```

### Флип – отдельный GUI-экшен

Простая смена `fp.layer = BoardLayer.BL_B_Cu` **не зеркалирует** пады и графику – это лишь меняет поле в данных.  
Для реального переворота используйте `footprints.flip_selected(kicad, board, [fp])` – он выделяет компоненты и запускает `run_action("pcbnew.InteractiveEdit.flip")`.

**Критично:** после флипа локальный объект `fp` **становится устаревшим** (его слой и ориентация не обновляются). Обязательно перечитайте футпринты заново через `board = board_api.refresh(kicad)` перед дальнейшей работой с этим компонентом, иначе последующий `update_items()` со старым объектом **откатит** флип.

---

## 📖 Примеры использования

### Поиск компонента и чтение его свойств

```python
from core_api import footprints, pads

# Все футпринты
all_fps = footprints.get_all(board)

# Поиск по refdes
fp = footprints.get_by_ref(board, "C5")
if fp:
    ref = footprints.get_reference(fp)
    value = footprints.get_value(fp)
    x, y = footprints.get_position_mm(fp)
    angle = footprints.get_angle_deg(fp)
    layer = footprints.get_layer(fp)
    is_back = footprints.is_back(fp)
    print(f"{ref} ({value}) at ({x:.3f}, {y:.3f}) mm, angle {angle}°, layer {layer}")

    # Получить пады
    pads_list = pads.get_all(fp)
    for pad in pads_list:
        pad_num = pad.number
        net = pads.get_net_name(pad)
        px, py = pads.get_position_mm(pad)
        size = pads.get_size_mm(pad)
        print(f"  Pad {pad_num}: net={net}, pos=({px:.3f},{py:.3f}), size={size}")
```

### Перемещение компонента

```python
from core_api import board as board_api

commit = board_api.begin_commit(board)
fp = footprints.get_by_ref(board, "R12")
footprints.set_position(fp, 10.5, 20.3)   # мм
board.update_items([fp])
board_api.push_commit(board, commit, "Переместил R12")
```

### Создание переходного отверстия (виа)

```python
from core_api import vias, nets

net = nets.get_by_name(board, "GND")
via = vias.make((15.0, 15.0), net, drill_mm=0.3, diameter_mm=0.6)

commit = board_api.begin_commit(board)
created = board.create_items([via])   # возвращает список созданных объектов
board_api.push_commit(board, commit, "Добавил виа")
```

### Удаление виа по UUID

```python
# created[0].id.value – это строка UUID
vias.remove_by_id(board, created[0].id.value)
```

### Получение сводки по выделенным компонентам

```python
from core_api import selection

# Пользователь что-то выделил в GUI
desc = selection.describe_selected(board)
for comp in desc:
    print(f"{comp['ref']} at ({comp['x_mm']:.3f}, {comp['y_mm']:.3f})")
    for pad in comp['pads']:
        print(f"  Pad {pad['number']}: net={pad['net']}")
```

### Безопасный коммит с автоматическим повтором

```python
from core_api import board as board_api

def move_component():
    fp = footprints.get_by_ref(board, "C5")
    footprints.set_position(fp, 12.0, 12.0)
    board.update_items([fp])

ok = board_api.commit_with_retry(
    board,
    "Перемещение C5",
    move_component,
    retries=1
)
if ok:
    print("Успешно")
else:
    print("Ошибка")
```

---

## ⚠️ Важные предостережения

| Проблема | Решение |
|----------|---------|
| **Busy-состояние** после некоторых операций | Используйте синхронный вызов `refill_zones(block=True)`, избегайте `block=False`. Если плата "зависла" – закройте все диалоги и переключитесь на инструмент выбора в GUI. |
| **Флип через `run_action`** нестабилен между версиями KiCad | Это официально нестабильный API. В текущей версии `pcbnew.InteractiveEdit.flip` работает, но будущие версии могут изменить имя. |
| **Объекты после флипа устаревают** | Всегда перечитывайте плату (`board = refresh(kicad)`) после флипа. |
| **Геттеры возвращают копии** | Изменяйте свойства только через полное переприсваивание (например, `fp.position = Vector2(...)`, **не** `fp.position.x = ...`). |
| **Транзакции обязательны** | Любое изменение должно быть внутри `begin_commit`/`push_commit` или `drop_commit`. |
| **Удаление по UUID** | `board.remove_items_by_id()` требует объект `KIID`, а не строку. В `vias.remove_by_id` это преобразование уже сделано. |
| **Размеры** | Внутренние единицы – нанометры. Все функции `core_api` принимают и возвращают миллиметры. |
| **Соединение не закрывается** | Переиспользуйте один объект `KiCad` на весь процесс. Не создавайте новое соединение для каждого вызова – это может вызвать busy-ошибки из-за накопления сокетов. |

---

## 🔗 Связь с `ipc_tests`

Пакет `core_api` **прошёл проверку** набором тестов `ipc_tests`, который включает:
- статические контрактные тесты (проверяют соответствие `core_api` реальной библиотеке `kipy` без запуска KiCad);
- интеграционные тесты на живом KiCad (чтение данных);
- мутирующие регрессионные тесты (флип, поворот, busy-состояния).

Рекомендуется перед использованием `core_api` в production-проекте прогнать хотя бы безопасные тесты из `ipc_tests.tests`, чтобы убедиться, что IPC-соединение стабильно и плата отвечает.

---

## 📂 Структура пакета

```
core_api/
├── __init__.py          # Описание пакета
├── kicad_client.py      # Подключение, run_action, версия
├── board.py             # refresh, транзакции, commit_with_retry
├── footprints.py        # Футпринты: поиск, чтение, изменение, флип
├── pads.py              # Пады: координаты, размер, цепь
├── vias.py              # Создание/удаление виа
├── zones.py             # Зоны: поиск по имени, точки контура
├── nets.py              # Цепи: все, по имени
├── selection.py         # Выделение, группы, сводка
└── geometry.py          # Константа MM, хелперы Vector2/Box2
```

Все функции принимают уже готовые объекты `kicad` и `board` – **глобального состояния нет**, что упрощает тестирование и переиспользование.

---

## 🧪 Пример быстрого smoke-теста

В репозитории есть скрипт `test_api.py`, который выполняет базовую проверку всех модулей `core_api` на реальном KiCad. Запустите его, чтобы убедиться, что всё работает:

```bash
python test_api.py --ref C5 --pad 1 --zone RA_DECAP_ZONE --net GND
```

Аргументы необязательны – скрипт сам подставит первый попавшийся компонент, если не указать.

---

## 📄 Лицензия

Данный пакет является частью внутренней инфраструктуры автоматизации и распространяется вместе с исходными кодами проектов, использующих его.