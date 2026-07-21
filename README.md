# KiCad IPC Test Framework

**General purpose of the project** – creating a unified, safe, and extensible system for testing and automating interaction with the **KiCad** PCB editor via IPC (the `kipy` library). The toolkit allows you to:

- perform **smoke, safe, and mutating tests** on a real board;
- conduct **static contract analysis** of the installed version of `kipy`;
- automate typical operations (moving, flipping components, creating vias);
- diagnose connection state and reproduce known KiCad bugs.

The project is built around a **single runner** that manages configuration, logging, the test registry, and the connection to KiCad, ensuring integrity and repeatability of runs.

---

## Installation and Dependencies

- **Python 3.8+**
- **KiCad 9 or 10** with GUI running (IPC works only with an open PCB editor)
- **`kipy` library** – official Python wrapper for KiCad IPC (installed separately, see [repository](https://gitlab.com/kicad/libraries/kipy))
- Optionally for CLI netlist export – **`kicad-cli`** (included in KiCad)

It is recommended to use a virtual environment:

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install kipy
```

---

## Configuration

All settings are done via a **single YAML file**. Minimal structure:

```yaml
kicad:
  timeout_ms: 20000               # IPC call timeout (ms)

logging:
  console_level: INFO             # console log level
  file: logs/test.log             # log file path
  file_level: DEBUG               # file log level
  rotate_max_bytes: 5242880       # max size per file
  rotate_backups: 3               # number of rotations

boards:                           # parameter profiles for different boards
  10CL006:
    ref: "C5"                     # default refdes
    pad: "1"                      # pad number
    zone: "RA_DECAP_ZONE"         # zone name
    net: "GND"                    # net name
    extra:                        # additional parameters
      offset_mm: 1.2

suites:                           # test groups
  smoke:
    enabled: true
    tests:
      smoke_footprints:
        enabled: true
  mutating:
    enabled: false                # dangerous tests are disabled by default
    tests:
      mutating_flip_then_update_items:
        enabled: false
        dangerous: true
        params:
          ref: "Ctest"
```

Parameters from `boards` and `tests` are merged via `resolve_params` (test parameters have higher priority).

---

## Running

**Main command:**

```bash
python -m runner.run --config <config.yaml> [--board <profile>] [--suite <suite>] [--test <test>]
```

- `--config` – required, path to YAML config.
- `--board` – board profile name (substitutes `ref/pad/zone/net` parameters).
- `--suite` – run only the specified suite.
- `--test` – run a specific test (even if not described in config – it will execute with default parameters, **except dangerous ones** – they require explicit `enabled: true`).

**Examples:**

```bash
# All safe tests for board 10CL006
python -m runner.run --config config/10CL006.yaml --board 10CL006 --suite safe

# Single smoke test on component C5
python -m runner.run --config config/10CL006.yaml --board 10CL006 --test smoke_footprints

# Dangerous test (only if enabled in config)
python -m runner.run --config config/10CL006.yaml --test decap_create_one_via
```

After execution, the runner outputs a summary `[PASS]/[FAIL]` and an exit code: `0` – all passed, `1` – some errors, `2` – attempt to run a disabled dangerous test.

---

## Project Structure

```
project_root/
├── core_api/                     # Base abstraction layer over kipy
│   ├── board.py                  # Transactions, board metadata (size, layers)
│   ├── footprints.py             # Footprint search, read, modification, flip
│   ├── geometry.py               # MM constant, coordinate utilities
│   ├── kicad_client.py           # Connection, run_action, version
│   ├── nets.py                   # Nets (search by name, code map)
│   ├── pads.py                   # Pads (obtained via definition.items)
│   ├── project.py                # Project and schematic paths
│   ├── selection.py              # Description of selected items
│   ├── vias.py                   # Create/delete vias
│   ├── zones.py                  # Zones (search, outline points)
│   └── __init__.py
│
├── runner/                       # Unified launch system
│   ├── config_schema.py          # Dataclass models and YAML loading
│   ├── logging_setup.py          # Logging setup (console + rotating file)
│   ├── registry.py               # Test registry (@register decorator)
│   ├── run.py                    # Main script (parsing, discovery, execution)
│   ├── step_helper.py            # call_step – logging with timing
│   └── __init__.py
│
├── tests/
│   ├── decap_tools/              # Dangerous tests for capacitors and vias
│   │   ├── test_create_one_via.py      # Create/delete one via
│   │   ├── test_flip_one_cap.py        # Flip component (toggle)
│   │   ├── test_move_one_cap.py        # Shift component along X
│   │   ├── test_via_placer.py          # Automatic via placement with keepout
│   │   ├── geometry/
│   │   │   ├── boundary.py             # Ray–polygon intersection, normals
│   │   │   └── keepout.py              # Keepout zones, free point search
│   │   └── __init__.py
│   │
│   ├── mutating/                 # Regression dangerous tests
│   │   ├── test_flip_then_update_items.py      # Stale object after flip
│   │   ├── test_footprint_rotation_linkage.py  # Rotation and schematic link (#21655)
│   │   ├── test_pad_ownership_comparison.py    # Comparison of pad acquisition methods
│   │   ├── test_refill_zones_busy_repro.py     # Eternal busy reproduction
│   │   └── __init__.py
│   │
│   ├── safe/                    # Safe tests (read-only)
│   │   ├── test_board_info.py          # Board summary (get_info)
│   │   ├── test_cli_netlist.py         # Netlist export via kicad-cli
│   │   ├── test_connection_reuse.py    # Single connection reuse check
│   │   ├── test_footprints_probe.py    # Temporary busy diagnostics
│   │   ├── test_project.py             # Project and schematic paths
│   │   ├── cli_utils.py                # kicad-cli utilities (not a test)
│   │   └── __init__.py
│   │
│   ├── smoke/                   # Smoke tests for basic modules
│   │   ├── test_board.py               # commit_with_retry (empty transaction)
│   │   ├── test_footprints.py          # Footprint reading and bounding box
│   │   ├── test_kicad_client.py        # Version and board re-fetch
│   │   ├── test_nets.py                # Net search by name
│   │   ├── test_pads.py                # Footprint pad reading
│   │   ├── test_selection.py           # Selection description (no input)
│   │   ├── test_vias.py                # Create/delete via (no leftovers)
│   │   ├── test_zones.py               # Zone search and outline point
│   │   └── __init__.py
│   │
│   ├── static/                  # Static contract checks of kipy
│   │   ├── test_kipy_contract.py       # 12 API incompatibility checks
│   │   └── __init__.py
│   │
│   ├── toy/                     # Dummy tests for runner debugging
│   │   ├── dummy_tests.py              # dummy_ok, fail, raises, needs_params, dangerous
│   │   └── __init__.py
│   │
│   └── __init__.py
│
├── config/                      # (example) YAML configs for different boards
│   └── test_config.yaml
│
└── logs/                        # Log files (auto-created)
    └── test.log
```

---

## Important Notes

- **Dangerous tests** (flag `dangerous: true`) are **never run** without explicit `enabled: true` in the config – this protects against accidental board damage.
- **Single connection** – all tests in one run use the same connection, preventing socket leaks.
- **After GUI flip**, you must re‑read the board, otherwise local objects become stale.
- **Static tests** do not require KiCad running and can be executed in CI.

---

## Extending

To add a new test:

1. Create a Python file in one of the `tests/` subdirectories.
2. Define a function with signature `def run_test(logger, **params) -> bool`.
3. Register it with the `@register("unique_name", suite="my_suite", dangerous=False, needs_kicad=True)` decorator.
4. Describe the test in the YAML config (with parameters if needed).

The runner will automatically discover the test when the `tests` package is imported.

---

## License and Authorship

The project is developed for internal use and testing of KiCad IPC capabilities. All source code is distributed under a license compatible with KiCad (GPLv3).

# `runner` Module — Unified Test and Script Launch System

`runner` is a framework for organizing, configuring, and executing test scenarios that work with KiCad via IPC. It provides:

- **Single entry point** – script `run.py` with command‑line arguments.
- **Flexible configuration** via a YAML file, where tests can be enabled/disabled, parameters can be set for different boards, and dangerous tests can be marked.
- **Test registry** based on decorators – tests are automatically registered upon import.
- **Single KiCad connection** for the entire run, to avoid socket leaks and false `busy` errors.
- **Standardized logging** with console and rotating file output.
- **Error and exception handling** – a test is considered failed on any exception; the runner catches and logs it.
- **Protection against accidental dangerous test execution** – they run only with explicit `enabled: true` in the config, even if specified with `--test`.

---

## `runner` Module Structure

### 1. `config_schema.py` – data models and configuration loading

Defines dataclasses for all config levels:

- **`KicadConfig`** – IPC settings: `timeout_ms` (default 20000), `socket_path` (optional).
- **`LoggingConfig`** – log levels, file path, rotation.
- **`BoardProfile`** – named set of parameters for a specific board: `ref` (default component refdes), `pad` (pad number), `zone` (zone name), `net` (net name), plus `extra: Dict` for any additional parameters.
- **`TestEntry`** – description of one test: `name`, `enabled` (bool), `dangerous` (bool), `params` (override dictionary).
- **`SuiteConfig`** – group of tests: `name`, `enabled`, `tests: Dict[str, TestEntry]`.
- **`RootConfig`** – root node containing `kicad`, `logging`, `boards` (profiles dictionary), and `suites`.

Functions:
- `load_config(path)` → `RootConfig` – loads and parses YAML.
- `resolve_params(board_profile, test_entry)` → `Dict[str, Any]` – merges final parameters for a test: first the `ref/pad/zone/net` fields from the board profile, then `extra` from the profile, then `params` from the test entry (overriding on conflict).

---

### 2. `logging_setup.py` – logging setup

- `setup_logging(logger_name, console_level, file_path, file_level, rotate_max_bytes, rotate_backups)` → `Logger`.
- Creates two handlers: console (level `console_level`, usually `INFO`) and rotating file (level `file_level`, usually `DEBUG`).
- **Idempotent** – on repeated calls with the same logger name, old handlers are removed to avoid duplicates.
- Disables propagation to the root logger (`logger.propagate = False`).

---

### 3. `registry.py` – test registry

- Global dictionary `_REGISTRY: Dict[str, RegisteredTest]`.
- **`RegisteredTest`** – dataclass with fields: `name`, `suite`, `dangerous`, `needs_kicad`, `func`.
- Decorator **`@register(name, suite, dangerous=False, needs_kicad=False)`** registers a function. Checks uniqueness of the name.
- `needs_kicad=True` means the test requires `kicad` and `board` objects; the runner will pass them via parameters (from `SharedConnection`).
- Access functions:
  - `get(name)` – get a registered test.
  - `all_tests()` – all tests.
  - `tests_in_suite(suite)` – tests of a specific suite.
  - `clear()` – reset registry (for testing the runner itself).

---

### 4. `step_helper.py` – step‑by‑step logging with timing

- **`call_step(logger, label, fn, *args, **kwargs)`** → `(result, success)`.
- Calls `fn`, logs the label and execution time in milliseconds.
- On exception, logs the error and returns `(None, False)` – **does not throw**.
- Used in tests for detailed tracking of each API call, to know at which step an error occurred.

---

### 5. `run.py` – main entry point

**Main script** performing the following steps:

#### Command‑line argument parsing

- `--config` (required) – path to YAML config.
- `--board` (optional) – board profile name from config.
- `--suite` (optional) – run only one suite.
- `--test` (optional) – run only one test by name.

#### Initialization

1. Loads config (`load_config`).
2. Sets up logging via `setup_logging` with config parameters.
3. Performs **test discovery**: function `discover_tests(package_name="tests")` recursively imports all modules inside the `tests` package. This ensures all `@register` decorators fire and populate the registry.

#### Test selection

Function `select_tests(cfg, suite_name, test_name)` returns a list of `(suite_name, TestEntry)` to run, considering `enabled` and `dangerous`:

- If `--test` is specified:
  - Searches for the test in all config suites.
  - If found and `enabled: false` – raises `PermissionError` (protection).
  - If the test is not in the config – creates a temporary `TestEntry` with `enabled=True`, `dangerous=False`.
- If `--suite` is specified – takes only that suite (if enabled).
- Otherwise – all suites from the config.
- Inside a suite, iterates over all tests, checking `enabled` (and for dangerous ones – that `enabled` is explicitly `true`).

#### Connection management

Class **`SharedConnection`**:

- Lazily establishes a connection to KiCad via `kicad_client.connect()` on first access.
- Provides method `get()` → `(kicad, board)`.
- Method `refresh_board()` re‑reads the board (useful after GUI actions).
- Used for all tests with `needs_kicad=True` to open **one** connection for the entire run.

#### Test execution

For each selected test:

1. Gets the `RegisteredTest` from the registry by name.
2. Builds parameters via `resolve_params(board_profile, entry)`.
3. If `needs_kicad`, adds `kicad` and `board` from `SharedConnection`.
4. Logs the start (with `[DANGEROUS]` marker if applicable).
5. Calls the test function with parameters.
6. Catches any exceptions, logs them, and counts the test as failed.
7. Stores the result `(name, ok)`.

#### Final report

- Logs the total number of tests run.
- Prints each test with `[PASS]`/`[FAIL]`.
- Exits with code `0` (all passed) or `1` (at least one failed).
- Special code `2` – when `--test` points to a disabled test (protection).

---

## Running Utility Tests

### Requirements

- Installed **KiCad** (version 9 or 10) with GUI running (IPC works only with active PCB editor).
- Installed `kipy` library (see [official repository](https://gitlab.com/kicad/libraries/kipy)).
- Python 3.8+.

### Basic Command

```bash
python -m runner.run --config <path_to_config.yaml> [--board <board_name>] [--suite <suite_name>] [--test <test_name>]
```

Examples:

- Run all enabled tests of all suites (with profile `10CL006`):
  ```bash
  python -m runner.run --config config/test_config.yaml --board 10CL006
  ```

- Run only the `safe` suite:
  ```bash
  python -m runner.run --config config/test_config.yaml --board 10CL006 --suite safe
  ```

- Run one specific test (even if not enabled in the config, it will run with default parameters):
  ```bash
  python -m runner.run --config config/test_config.yaml --test dummy_ok
  ```

- Run a dangerous test (must be explicitly enabled in the config, otherwise rejected):
  ```bash
  python -m runner.run --config config/test_config.yaml --board 10CL006 --test decap_create_one_via
  ```

### Minimal YAML config structure

```yaml
kicad:
  timeout_ms: 20000

logging:
  console_level: INFO
  file: logs/test.log
  file_level: DEBUG
  rotate_max_bytes: 5242880
  rotate_backups: 3

boards:
  10CL006:
    ref: "C5"
    pad: "1"
    zone: "RA_DECAP_ZONE"
    net: "GND"
    extra:
      custom_param: value

suites:
  toy:
    enabled: true
    tests:
      dummy_ok:
        enabled: true
      dummy_fail:
        enabled: false

  mutating:
    enabled: false   # all mutating tests disabled by default
    tests:
      mutating_flip_then_update_items:
        enabled: false
        dangerous: true
        params:
          ref: "Ctest"
```

---

## Important Architectural Decisions

- **Safety by default** – dangerous tests (`dangerous: true`) do not run, even if `--test` is specified, unless `enabled: true` is set in the config. This protects against accidental board damage.
- **Single connection** – all tests in one run share the same connection, preventing `busy` errors and resource leaks.
- **Idempotent logging** – repeated calls to `setup_logging` do not create duplicate handlers.
- **Transparent error handling** – exceptions in tests do not abort the whole run; they are logged, and the runner continues with the remaining tests.

---

## Extending and Adding New Tests

1. Create a Python file in any subdirectory of `tests/` (e.g., `tests/my_suite/test_my_feature.py`).
2. Define a function with signature `def run_test(logger, **params) -> bool`.
3. Register it with the decorator:
   ```python
   from runner.registry import register

   @register("my_test", suite="my_suite", dangerous=False, needs_kicad=True)
   def run_test(logger, kicad, board, ref=None, **params):
       # test body
       return True
   ```
4. Describe the test in the YAML config (set `enabled`, `params` if needed).
5. Run with `--suite my_suite` or `--test my_test`.

---

# `core_api` — Base Layer for KiCad Interaction

`core_api` is a universal wrapper library over the official `kipy` (KiCad IPC) Python library. It provides a unified, type‑safe, and documented interface for working with an open board in KiCad’s PCB editor.

### Core Principles

- **No global state** – all functions take ready‑made `kicad` or `board` objects as explicit arguments. This makes the code easily testable, reusable, and safe in multi‑threading scenarios.
- **Transactional approach** – all board modifications are performed inside commits (`begin_commit` / `push_commit` / `drop_commit`). This ensures atomicity and allows rollback on error.
- **Working in millimetres** – all coordinates and sizes are accepted and returned in millimetres (`float`). The internal `kipy` representation uses nanometres (integers); conversion is performed automatically using the constant `MM = 1_000_000`.
- **Explicit cache refresh** – after operations that modify the board outside the standard `update_items` mechanism (e.g., after a GUI flip via `run_action`), local objects become stale. You should re‑read data via `board.get_footprints()` or `board.refresh()`.

---

## Module Structure

### 1. `geometry.py` – geometric constants and utilities

The most basic module, defining the coordinate conversion unit:

```python
MM = 1_000_000  # number of nanometres in one millimetre
```

Helper functions:

- `vec_mm(x_mm, y_mm)` → `Vector2` – creates a vector from millimetres.
- `to_mm(vector)` → `(x_mm, y_mm)` – converts a vector to millimetres.
- `bbox_size_mm(bbox)` → `(width_mm, height_mm)` – extracts dimensions from a `Box2` object.

All other modules rely on this module for consistent unit conversion.

---

### 2. `kicad_client.py` – connection and session management

Responsible for establishing a connection to a running KiCad instance and performing low‑level actions:

- `connect(timeout_ms=20000)` → `KiCad` – connects to the currently open project. Default timeout increased to 20 seconds (in `kipy` default is 2 seconds, insufficient for heavy transactions).
- `get_board(kicad)` → `Board` – returns the board object.
- `run_action(kicad, action)` – executes a GUI action (e.g., `"pcbnew.InteractiveEdit.flip"`). This is officially an unstable API (see `kipy` documentation), but necessary for operations not available via `update_items` (e.g., true component flip with mirroring).
- `get_version(kicad)` → `str` – returns the KiCad version (useful for diagnostics).

---

### 3. `board.py` – transactions, commits, and board metadata

The most important module for board modification. It provides:

- **Transaction management**:
  - `begin_commit(board)` – starts a transaction.
  - `push_commit(board, commit, description)` – commits changes.
  - `drop_commit(board, commit)` – rolls back a transaction.
  - `commit_with_retry(board, description, work_fn, retries=1)` – executes the passed function inside a transaction with automatic rollback on exception and one retry. Returns `bool` (success/failure) or throws if all attempts fail.

- **Cache refresh**:
  - `refresh(kicad)` → `Board` – re‑reads the board. **Must be called** after GUI actions (e.g., `flip_selected`) to obtain up‑to‑date local objects.

- **Board metadata**:
  - `get_edge_bounding_box_mm(board)` → `(width_mm, height_mm)` or `None` – dimensions from Edge.Cuts contour.
  - `get_copper_layer_count(board)` → `int` or `None` – number of copper layers.
  - `get_info(board)` → `dict` – combines all metadata into one dictionary.

**Important:** in `commit_with_retry`, the `commit` variable is initialised to `None` before the `try` block. This prevents `UnboundLocalError` if `begin_commit()` itself throws.

---

### 4. `footprints.py` – working with components

Module for searching, reading, and modifying footprints.

**Search:**
- `get_all(board)` → `list[FootprintInstance]` – all board components.
- `get_by_ref(board, ref)` → `FootprintInstance` or `None` – search by refdes (e.g., `"C5"`). Case‑sensitive.

**Reading:**
- `get_reference(fp)`, `get_value(fp)`, `get_footprint_name(fp)` – strings.
- `get_position_mm(fp)` → `(x_mm, y_mm)`.
- `get_angle_deg(fp)` → `float` (degrees).
- `get_layer(fp)` → `BoardLayer` (constant).
- `is_back(fp)` → `bool` – `True` if component is on the bottom side.
- `get_bounding_box_mm(board, fp)` → `(width_mm, height_mm)` or `None` – bounding box of a single component (excluding text).
- `get_bounding_boxes_mm(board, footprints)` → `list[Optional[tuple]]` – batch query for multiple footprints (more efficient than one‑by‑one).

**Modification (local, requires `update_items` inside a commit):**
- `set_position(fp, x_mm, y_mm)` – changes position in the local object.
- `set_angle_deg(fp, angle_deg)` – changes angle.

**True flip:**
- `flip_selected(kicad, board, footprints)` – performs a GUI flip for the given footprints. **After calling, you must re‑read the board** because local objects are stale.

---

### 5. `pads.py` – pads

Working with pads **in the context of an already known footprint**.

- `get_all(fp)` → `list[Pad]` – all pads of the footprint. Retrieved from `fp.definition.items` (without geometric search or extra API calls).
- `get_by_number(fp, number)` → `Pad` or `None` – search by number (e.g., `"1"`).
- `get_position_mm(pad)` → `(x_mm, y_mm)` – absolute position (kipy accounts for footprint rotation).
- `get_net_name(pad)` → `str` – net name or empty string if unconnected.
- `get_size_mm(pad)` → `(width_mm, height_mm)` or `None` – pad size (takes the first copper layer).
- `get_angle_deg(pad)` → `float` – padstack's own angle (already synchronised with footprint).

---

### 6. `nets.py` – nets

- `get_all(board)` → `list[Net]` – all nets.
- `get_by_name(board, name)` → `Net` or `None` – search by name.
- `build_net_map(board)` → `dict[int, str]` – dictionary `{code: name}`. **Note:** `Net.code` is marked deprecated in `kipy`, so use of this function is not recommended for production code; retained only for debugging.

---

### 7. `vias.py` – vias

- `make(position_mm, net, drill_mm=0.3, diameter_mm=0.6)` → `Via` – creates a `Via` object (not yet on the board). Then you need to call `board.create_items([via])` inside a transaction.
- `remove_by_id(board, uuid_str)` – removes an object by UUID. **Important:** internally uses `board.remove_items_by_id([KIID])`, where `KIID` is an object, not a string. The function correctly converts the string.

---

### 8. `zones.py` – zones (including Rule Areas)

- `get_by_name(board, name)` → `Zone` or `None` – search by name.
- `get_boundary_points(zone)` → `list[Vector2]` – outline points (only nodes of type `has_point`; arcs ignored). For most rectangular/polygonal zones this is sufficient.

---

### 9. `project.py` – project and schematic paths

- `get_project_path(board)` → `str` or `None` – project directory.
- `get_project_name(board)` → `str` or `None` – project name.
- `get_schematic_path(board)` → `str` or `None` – full path to `.kicad_sch` file (constructed from path and name).

---

### 10. `selection.py` – working with selection

Module for analysing the current selection in PCB editor.

- `get_selected_uuids(board)` → `set[str]` – UUIDs of all selected objects. **Critical:** for groups (`Group`), uses `group.proto.items` instead of the empty `group.items` (local cache).
- `get_selected_footprints(board)` → `list[FootprintInstance]` – only footprints from the selection (other types ignored).
- `describe_selected(board)` → `list[dict]` – detailed description of each selected component: refdes, position, angle, dimensions, list of pads with their nets and coordinates. Useful for diagnostics and debugging.

---

## Relationships and Typical Usage Scenario

1. **Connect** via `kicad_client.connect()`.
2. **Get board** via `kicad_client.get_board(kicad)`.
3. **Read** – use `footprints.get_by_ref`, `pads.get_all`, `nets.get_by_name`, etc.
4. **Modify** – always inside a transaction:
   ```python
   commit = board.begin_commit()
   try:
       # locally modify objects (set_position, set_angle, create via)
       board.update_items([modified_objects])
       board.create_items([new_via])
       board.push_commit(commit, "my change")
   except Exception:
       board.drop_commit(commit)
       raise
   ```
5. **After GUI actions** (e.g., `footprints.flip_selected`) always call `board = kicad_client.get_board(kicad)` or `board.refresh()` to update local objects.

---

## Safety and Performance Notes

- **Timeout** increased to 20 seconds – sufficient for bulk operations (hundreds of objects).
- **Batch requests** – use `get_bounding_boxes_mm` instead of looping `get_bounding_box_mm` to save time.
- **No geometric mapping** of pads to footprints – we always obtain pads via `definition.items` of a known footprint, which is more reliable and faster.
- **Dangerous operations** (flip, create/delete objects) are performed only in tests with the `dangerous` flag, but `core_api` itself does not contain protection logic – that is left to the runner.

---

# `tests/decap_tools` — Utilities and Tests for Decoupling Capacitors and Vias

The `tests/decap_tools/` directory contains **dangerous** diagnostic and helper tests designed to verify and demonstrate IPC interaction with KiCad for typical component operations (move, flip) and vias (create, delete, automatic placement). These tests are part of the overall runner system, registered in the `decap_tools` suite, and require explicit enabling (`enabled: true`) in the config because they modify the real board.

---

## Directory Structure

```
tests/decap_tools/
├── test_create_one_via.py
├── test_flip_one_cap.py
├── test_move_one_cap.py
├── test_via_placer.py
└── geometry/
    ├── boundary.py
    └── keepout.py
```

---

## 1. `test_create_one_via.py` – minimal via create/delete test

**Purpose:** testing basic `create_items()` and `remove_items_by_id()` operations on a single via. The test creates a via near the centre of the specified component, saves its UUID in a JSON file (`.last_test_via.json`) for later deletion without manual ID copying.

**Function:**  
`run_test(logger, kicad, board, ref=None, offset_mm=1.2, net="GND", drill_mm=0.3, diameter_mm=0.6, remove=False, remove_uuid=None, **params) -> bool`

- **Parameters:**
  - `ref` – component refdes (required if `remove=False`).
  - `offset_mm` – X offset from component centre (mm).
  - `net` – net name (default `"GND"`).
  - `drill_mm` and `diameter_mm` – via dimensions.
  - `remove` – if `True`, deletes a via instead of creating (using saved UUID or `remove_uuid`).
- **Logic:**
  - On deletion: if `remove_uuid` not given, reads `id` from JSON.
  - On creation: finds component, net, builds via, performs transaction `begin_commit` → `create_items` → `push_commit`, saves `id` to JSON.
- **Uses:** `core_api.footprints`, `core_api.nets`, `core_api.vias`, `core_api.board` (transactions), `runner.step_helper.call_step`.

---

## 2. `test_flip_one_cap.py` – component flip (toggle)

**Purpose:** testing the true component flip (GUI action `pcbnew.InteractiveEdit.flip`), which mirrors pads and silkscreen, unlike simple `.layer` change. Useful as a quick self‑check of flip functionality in the current KiCad version.

**Function:**  
`run_test(logger, kicad, board, ref=None, **params) -> bool`

- **Parameters:** `ref` – component refdes.
- **Logic:**
  - Logs component state before flip (layer, position, angle).
  - Calls `footprints.flip_selected(kicad, board, [target])`.
  - Re‑reads component and logs state after.
  - Returns `True` if layer changed to `BL_B_Cu` (or at least changed from original).
- **Important:** flip is a toggle; a second call will flip it back.
- **Uses:** `core_api.footprints` (specifically `flip_selected`).

---

## 3. `test_move_one_cap.py` – shift component along X axis

**Purpose:** isolated IPC write test – shifting one component by a given distance. Used to diagnose transaction hangs (`begin_commit`) and the `update_items` mechanism.

**Function:**  
`run_test(logger, kicad, board, ref=None, delta_mm=1.0, revert=False, **params) -> bool`

- **Parameters:** `ref` – component refdes; `delta_mm` – shift magnitude (mm); `revert` – if `True`, shift in opposite direction (`-delta_mm`).
- **Logic:**
  - Calculates new position.
  - Opens transaction, updates position via `update_items`, commits.
- **Uses:** `core_api.footprints` (read and modify position), `core_api.geometry.vec_mm`, `runner.step_helper.call_step`.

---

## 4. `test_via_placer.py` – automatic via placement near GND pads

**Purpose:** placing vias near GND pads of given components with three offset strategies (`center`, `edge`, `courtyard`), finding free space with keepout zones from other components and existing vias.

**Function:**  
`run_test(logger, kicad, board, gnd_net_name="GND", via=None, components=None, dry_run=False, **params) -> bool`

- **Parameters:**
  - `gnd_net_name` – net name (default `"GND"`).
  - `via` – dictionary of via parameters:
    - `offset_from` – `"center"`, `"edge"`, or `"courtyard"`.
    - `offset_mm` – base offset (mm).
    - `angle_deg` – preferred angle (if not given, computed automatically).
    - `drill_mm`, `diameter_mm` – via dimensions.
    - `keepout_clearance_mm` – margin for keepout zones.
    - `search_step_mm`, `search_max_radius_mm`, `search_n_directions` – free point search parameters.
  - `components` – list of dicts with fields `ref` (required), `offset_mm`, `angle_deg` (override global).
  - `dry_run` – if `True`, only logs, does not create vias.
- **Logic:**
  - For each component:
    - Finds footprint and GND pad.
    - Determines offset strategy.
    - Computes ideal via position considering pad rotation and Courtyard (if selected).
    - Builds keepout zones from bounding boxes of other components and all vias.
    - Searches for a free point near the ideal position respecting preferred direction.
    - Creates a via object.
  - Finally, executes a single transaction to create all vias (or nothing if `dry_run`).
- **Helper functions inside the file:**
  - `intersect_ray_with_rotated_rect` – ray‑rotated‑rectangle intersection (for `edge`).
  - `get_courtyard_polygon` – extracts Courtyard polygon points from `fp.definition.items` (fixed – now correctly handles `BoardRectangle` and `BoardPolygon`).
  - `compute_ideal_position` – computes ideal position based on chosen strategy.
- **Uses:** `core_api.footprints`, `core_api.pads`, `core_api.nets`, `core_api.vias`, `runner.step_helper.call_step`, local modules `geometry.boundary` and `geometry.keepout`.

---

## 5. `geometry/boundary.py` – polygon boundary utilities

**Purpose:** set of functions for working with polygons (Courtyard, zones) – computing ray‑polygon intersection, closest point on polygon, and outward normal. Used in `test_via_placer` for the `courtyard` strategy.

**Key functions:**
- `polyline_points(polyline)` – extracts points from a `PolyLine`.
- `_ray_segment_intersection(ox, oy, dx, dy, x1, y1, x2, y2)` – ray‑segment intersection.
- `ray_boundary_distance(center, target, boundary_pts)` – distance from `center` to the intersection of the ray with the polygon.
- `polygon_signed_area(polygon)` – signed area (to determine winding order).
- `closest_point_on_polygon(point, polygon)` – closest point on polygon and outward normal. **Fixed:** normal direction determined once for the entire polygon via signed area, which works correctly even in borderline cases where the point is just outside the polygon.

**Note:** code copied from the `KiCadDecapPlacer` project and is currently duplicated, but planned to be consolidated into a common location.

---

## 6. `geometry/keepout.py` – keepout zones and free point search

**Purpose:** building rectangular keepout zones from object bounding boxes and searching for a free point for via placement with a preferred direction.

**Class `Rect`:**
- Simple AABB rectangle in nanometres.
- Constructor from bounding box (`from_bbox`) with `clearance`.
- Circle approximation as square (`from_circle`).
- Intersection test (`intersects`).

**Functions:**
- `point_is_clear(point, via_radius, keepout)` – checks if the via circle of radius `via_radius` does not intersect any rectangle in `keepout`.
- `build_keepout(bboxes, clearance_mm, mm_per_unit)` – builds a list of `Rect` from a list of bounding boxes with margin.
- `find_free_point(ideal, keepout, via_radius, preferred_direction, step_mm, max_radius_mm, mm_per_unit, n_directions)` – searches for the closest free point to `ideal`, expanding in concentric rings. On each ring, checks the preferred direction first, then evenly spaced directions. Returns `Vector2` or `None` if no place found within `max_radius_mm`.

**Used in:** `test_via_placer` for final via positioning.

---

## Relationships and Dependencies

- All tests use **`core_api`** for accessing board objects and performing operations.
- **`test_via_placer`** heavily uses the geometry modules (`boundary`, `keepout`) and provides a fixed implementation for obtaining Courtyard.
- Tests are registered via **`runner.registry`** and use **`runner.step_helper.call_step`** for unified logging and error handling.
- **State saving** (`.last_test_via.json` in `test_create_one_via`) allows deleting created objects without manually entering a UUID.

---

## Running and Configuration

Tests from `decap_tools` are **disabled by default** (`enabled: false` in config) due to their dangerous nature. To run them, you must explicitly enable them in the YAML config, specifying required parameters (e.g., `ref`, `net`, `offset_mm`, etc.).

Example enabling a suite and a specific test:

```yaml
suites:
  decap_tools:
    enabled: true
    tests:
      decap_create_one_via:
        enabled: true
        params:
          ref: "C5"
          net: "GND"
          offset_mm: 1.2
```

Run:

```bash
python -m runner.run --config config.yaml --board 10CL006 --test decap_create_one_via
```

KiCad must be running with the board open, and the component `C5` must exist. For `test_via_placer`, a `components` list is required in the test parameters.

---

# `tests/mutating` — Regression Tests for Critical IPC Operations

The `tests/mutating/` directory contains **dangerous** tests that modify the real board and serve to:

- **Regression test** IPC calls related to object modifications (rotations, flip, positioning).
- **Reproduce known KiCad bugs**, for example:
  - flip rollback when using stale local objects;
  - possible break of symbol ↔ footprint link when rotating a footprint;
  - board "stuck" after asynchronous `refill_zones(block=False)` call.
- **Verify architectural decisions**, such as whether geometric mapping is needed to find pads.

All tests are registered in the `mutating` suite, use a shared connection (`needs_kicad=True`), and step‑by‑step logging via `call_step`. They are **disabled** (`enabled: false`) by default in the config – run deliberately only on test boards.

---

## 1. `test_flip_then_update_items.py` – regression on stale object after flip

**File:** `test_flip_then_update_items.py`  
**Test name:** `mutating_flip_then_update_items`

### Purpose
Checks that after a GUI flip (`pcbnew.InteractiveEdit.flip`), using the old local `Footprint` object in `update_items()` silently rolls back the layer change. The test demonstrates the **wrong** path (A) and the **correct** path (B) with re‑reading the footprint after the flip.

### Function
```python
run_test(logger, kicad, board, ref=None, **params) -> bool
```

**Parameters:** `ref` – refdes of the test component (required).

### Logic
1. Saves original layer and position.
2. **Variant A (wrong):**
   - Selects the component, executes `run_action("pcbnew.InteractiveEdit.flip")`.
   - Opens a transaction, modifies the **old** `target.position` (shift by 0.5 mm).
   - Calls `board.update_items([target])` – this rolls back the layer.
   - Checks if the layer returned to the original – if yes, bug reproduced.
3. **Variant B (correct):**
   - Calls `footprints.flip_selected(kicad, board, [after_a])` (also a GUI flip, but via wrapper).
   - **Re‑reads** the footprint (`get_by_ref`) – gets a fresh object.
   - Opens a transaction, restores the original position and commits.
   - Checks that the layer became the original (second flip reverted it).
4. Logs results.

### Important Notes
- The test **mutates** the component (flip + shift), but restores its original state at the end via variant B.
- Demonstrates a critical bug: `update_items` with a stale object after flip is a silent no‑op for the layer, but the position shift is applied.
- Requires a test component (not production).

---

## 2. `test_footprint_rotation_linkage.py` – bug #21655 (symbol ↔ footprint link break)

**File:** `test_footprint_rotation_linkage.py`  
**Test name:** `mutating_footprint_rotation_linkage`

### Purpose
Checks indirect signs of integrity of the link between schematic symbol and footprint after rotation via IPC. Direct check is impossible because IPC does not provide access to the schematic editor. The test compares snapshots before and after rotation: `reference`, `value`, footprint name, `net` on each pad.

### Function
```python
run_test(logger, kicad, board, ref=None, angle_deg=45.0, auto_revert=True, **params) -> bool
```

**Parameters:**
- `ref` – component refdes (required).
- `angle_deg` – rotation amount in degrees (default 45°).
- `auto_revert` – if `True` (default), the test restores the original angle after verification.

### Logic
1. Creates `_snapshot(fp)` – dictionary with `ref`, `value`, `footprint_name`, `pad_count`, `pads` (sorted list of `(number, net)`).
2. Rotates the component by `angle_deg` via `board.update_items` (inside transaction).
3. Re‑reads the footprint and takes a post‑snapshot.
4. Compares snapshots – if they are identical (except angle), the test considers the PCB‑side connectivity intact.
5. If `auto_revert=True`, performs a reverse rotation (`-angle_deg`).
6. Logs result.

### Important Notes
- The test does **not prove** the absence of bug #21655 on the schematic side, but shows that `net` on pads is not lost.
- By default, the board is **left unchanged** due to `auto_revert`.
- If `auto_revert=False`, the component remains rotated for manual check in Schematic Editor.

---

## 3. `test_pad_ownership_comparison.py` – comparison of two pad acquisition methods

**File:** `test_pad_ownership_comparison.py`  
**Test name:** `mutating_pad_ownership_comparison`  
**Dangerous:** `False` (read‑only)

### Purpose
Checks whether geometric mapping is needed to associate pads with footprints. The static test `static_pad_has_no_footprint_backreference` already confirmed that `board.get_pads()` does not provide a reverse reference. However, `core_api.pads` uses `fp.definition.items` – this test compares both approaches on a real board.

### Function
```python
run_test(logger, kicad, board, **params) -> bool
```

### Logic
1. **Path A:** calls `board.get_pads()` (flat list of all pads) and checks for an attribute pointing to the footprint (expected `False`).
2. **Path B:** takes the first 5 footprints, for each obtains pads via `fp.definition.items` and reads `net` for each pad (no geometry).
3. Checks that all pads gave a `net` – if yes, geometric mapping is not needed.

### Important Notes
- Test is **safe** (read‑only) but placed in the `mutating` suite due to theme.
- Confirms that when the footprint is known, geometry is not required.

---

## 4. `test_refill_zones_busy_repro.py` – reproduction of eternal busy after `refill_zones(block=False)`

**File:** `test_refill_zones_busy_repro.py`  
**Test name:** `mutating_refill_zones_busy_repro`  
**Dangerous:** **very high** – may lead to an unrecoverable board state requiring KiCad restart.

### Purpose
Tests the hypothesis that calling `board.refill_zones(block=False, max_poll_seconds=1)` leaves an unfinished asynchronous job that "locks" the board: all subsequent calls (`get_footprints`, `get_tracks`, etc.) return `busy` forever.

### Function
```python
run_test(logger, kicad, board, **params) -> bool
```

### Logic
1. **Step 1 (baseline):** calls `get_footprints`, `get_tracks`, `get_nets` – verifies everything works before the operation.
2. **Step 2:** executes `board.refill_zones(block=False, max_poll_seconds=1)` – **exactly as in the original incident**.
3. **Step 3 (immediately after):** repeats the content calls and logs whether they broke.
4. **Step 4 (retries):** makes up to 6 attempts with 5‑second pauses to see if the lock releases by itself.
5. Logs the result.

### Important Notes
- **Most dangerous test.** If the hypothesis is confirmed, the board remains in a "broken" state, and the **only way out** is a full restart of the KiCad application.
- Run **only** on a test board, not in the middle of an important session.
- The test does not run `refill_zones` with `block=True` because that would block the IPC connection for a long time and is not a reproduction of the original incident.

---

## General Characteristics of the `mutating` Suite

| Test | Dangerous | Restores | Purpose |
|------|-----------|----------|---------|
| `flip_then_update_items` | yes | yes (variant B) | regression on stale object |
| `footprint_rotation_linkage` | yes | yes (`auto_revert`) | #21655 check (indirect) |
| `pad_ownership_comparison` | no | – | comparison of pad acquisition methods |
| `refill_zones_busy_repro` | **very high** | **no** (requires KiCad restart) | reproduction of eternal busy |

### Running

All tests are disabled by default in the config. To run them, you must explicitly set `enabled: true` for the `mutating` suite and/or for the specific test, and provide required parameters (e.g., `ref` for the first three).

Example enabling:

```yaml
suites:
  mutating:
    enabled: true
    tests:
      mutating_flip_then_update_items:
        enabled: true
        params:
          ref: "Ctest"
      mutating_footprint_rotation_linkage:
        enabled: true
        params:
          ref: "Ctest"
          auto_revert: true
      mutating_refill_zones_busy_repro:
        enabled: true
```

Run:

```bash
python -m runner.run --config config.yaml --board 10CL006 --test mutating_flip_then_update_items
```

**Warning:** before running `mutating_refill_zones_busy_repro`, make sure you are prepared to restart KiCad and do not lose important changes.

---

# `tests/safe` — Safe Tests (Read‑Only)

The `tests/safe/` directory contains **safe** tests that **do not modify** the board and serve to:

- verify basic `core_api` functionality (reading board info, project, components);
- diagnose IPC connection state and busy situations;
- integrate with external tools (netlist export via `kicad-cli`).

All tests are registered in the `safe` suite, marked `dangerous=False`, use a shared KiCad connection (`needs_kicad=True`) and are **enabled by default** (`enabled: true`) in the config because they do not change the board.

---

## Directory Structure

```
tests/safe/
├── test_board_info.py
├── test_cli_netlist.py
├── test_connection_reuse.py
├── test_footprints_probe.py
├── test_project.py
└── cli_utils.py          # helper module (not a test)
```

---

## 1. `test_board_info.py` – board summary information

**Test name:** `safe_board_info`

### Purpose
Retrieves and logs general board information: number of footprints, nets, dimensions from Edge.Cuts, number of copper layers. Uses the new `core_api.board.get_info()`.

### Function
```python
run_test(logger, kicad, board, **params) -> bool
```

### Logic
- Calls `core_api.board.get_info(board)`.
- Logs the returned dictionary.
- Issues warnings if board is empty, size unknown, or layer count unknown.
- Always returns `True` (diagnostic test).

### Uses
- `core_api.board`

---

## 2. `test_cli_netlist.py` – netlist export via `kicad-cli`

**Test name:** `safe_cli_netlist`

### Purpose
Export netlist to XML format via external CLI tool `kicad-cli`, then parse the resulting file and output the number of nets and the first few nodes. This is a separate mechanism (subprocess), **not IPC**.

### Function
```python
run_test(logger, kicad, board, **params) -> bool
```

### Logic
1. Obtains schematic path via `core_api.project.get_schematic_path(board)`.
2. Creates a temporary XML file.
3. Calls `export_netlist(sch_path, tmp_path, logger)` (from `cli_utils.py`).
4. If successful, parses the XML via `parse_netlist_xml()`.
5. Logs the number of nets found and the first 5 nets with their nodes.
6. Deletes the temporary file.
7. Returns `True` if export and parsing succeeded.

### Uses
- `core_api.project`
- `cli_utils` (export and parse)

### Important Notes
- The test **takes noticeable time** (~19 seconds) due to the external process launch.
- `kicad-cli` must be installed and available on `PATH` or via the `KICAD_CLI_PATH` environment variable (see `cli_utils.find_kicad_cli`).

---

## 3. `test_connection_reuse.py` – connection reuse check

**Test name:** `safe_connection_reuse`

### Purpose
Regression test that the runner passes the **same** connection (`kicad` and `board`) to all tests, rather than opening a new one each time. This guarantees no socket leaks and no `busy` errors.

### Function
```python
run_test(logger, kicad, board, **params) -> bool
```

### Logic
- Calls `kicad_client.get_version(kicad)` 5 times and measures the time of each call.
- If all calls succeed and times are small (fractions of a millisecond), the test is considered successful.
- If each call opened a new connection, timings would be an order of magnitude higher (tens of ms).

### Uses
- `core_api.kicad_client`

### Important Notes
- The test does **not** inspect internal runner structures, but verifies behaviour from the user perspective (the objects passed).
- Passes if `get_version` consistently works on the passed connection.

---

## 4. `test_footprints_probe.py` – temporary busy diagnostics

**Test name:** `safe_footprints_probe`

### Purpose
Diagnostic test that attempts to call `board.get_footprints()` several times with pauses to check whether busy‑state releases by itself. **Does not fix** the issue, only records and logs.

### Function
```python
run_test(logger, kicad, board, **params) -> bool
```

### Logic
- Makes up to 6 attempts to call `board.get_footprints()` with 2‑second pauses.
- If at least one attempt succeeds, logs it and returns `True`.
- If all attempts returned busy, logs a warning and returns `True` (diagnostic test is not considered a failure).

### Uses
- `core_api.footprints` (via direct `board.get_footprints()` call)
- `runner.step_helper.call_step`

### Important Notes
- The test **is not considered a failure** even if busy persists – it is for analysis.
- Useful for detecting hangs caused by GUI tools or dialogs.

---

## 5. `test_project.py` – project and schematic paths

**Test name:** `safe_project`

### Purpose
Retrieves and logs the project directory, project name, and full path to the schematic file (`.kicad_sch`). Checks if the schematic file exists.

### Function
```python
run_test(logger, kicad, board, **params) -> bool
```

### Logic
- Calls `core_api.project.get_project_path(board)`, `get_project_name(board)`, `get_schematic_path(board)`.
- Logs all three values.
- Checks if the schematic file exists and issues a warning if not.
- Returns `True` if project path and name are not `None`.

### Uses
- `core_api.project`

---

## 6. `cli_utils.py` – helper utilities for `kicad-cli`

**This is not a test**, but a module with functions for working with the external CLI tool. Located in the `safe` directory because it is used only by `test_cli_netlist.py`.

### Functions

#### `find_kicad_cli(logger=None) -> str | None`
- Searches for `kicad-cli` executable:
  - via environment variable `KICAD_CLI_PATH`;
  - via standard KiCad installation paths (Windows);
  - via `shutil.which`.
- Returns the path or `None`.

#### `export_netlist(schematic_path, output_path, kicad_cli_path=None, logger=None) -> bool`
- Runs `kicad-cli sch export netlist --format kicadxml --output <output_path> <schematic_path>`.
- Returns `True` on success, `False` with logging on error.

#### `parse_netlist_xml(xml_path, logger=None) -> list[dict] | None`
- Parses the XML file generated by `kicad-cli`.
- Expects structure: root `<netlist>` → `<nets>` → many `<net name="...">` → `<node ref="..." pin="..."/>`.
- Returns a list of dicts `{"name": net_name, "nodes": [ref.pin, ...]}` or `None` on error.

---

## General Characteristics of the `safe` Suite

| Test | Dangerous | Execution time | Purpose |
|------|-----------|----------------|---------|
| `safe_board_info` | no | fast | board summary |
| `safe_cli_netlist` | no | ~19 s | netlist export via CLI |
| `safe_connection_reuse` | no | fast | connection reuse check |
| `safe_footprints_probe` | no | up to ~12 s | temporary busy diagnostics |
| `safe_project` | no | fast | project and schematic paths |

All tests use `needs_kicad=True` and receive `kicad` and `board` objects from the runner. They **do not modify** the board and are safe to run at any time.

### Running

The `safe` suite is enabled by default in the config (`enabled: true`). Run:

```bash
python -m runner.run --config config.yaml --board 10CL006 --suite safe
```

Or a single test:

```bash
python -m runner.run --config config.yaml --test safe_board_info
```

For `safe_cli_netlist`, `kicad-cli` must be installed and the schematic file must be accessible (via `core_api.project`).

---

# `tests/smoke` — Smoke Tests for Basic `core_api` Modules

The `tests/smoke/` directory contains **smoke tests** that verify the main `core_api` modules work and basic read/write operations execute without errors. These tests are **safe** (`dangerous=False`) and **do not leave changes** on the board (except `test_vias.py`, which creates and immediately deletes a test via). All tests use a shared KiCad connection (`needs_kicad=True`) and are registered in the `smoke` suite.

---

## Directory Structure

```
tests/smoke/
├── test_board.py
├── test_footprints.py
├── test_kicad_client.py
├── test_nets.py
├── test_pads.py
├── test_selection.py
├── test_vias.py
└── test_zones.py
```

---

## 1. `test_board.py` – transaction mechanism check

**Test name:** `smoke_board_commit`

### Purpose
Verifies basic `core_api.board.commit_with_retry` functionality with an empty transaction. Confirms the commit mechanism works without errors.

### Function
```python
run_test(logger, kicad, board, **params) -> bool
```

### Logic
- Calls `board.commit_with_retry(board, "smoke_board_commit: empty transaction", lambda: None)`.
- Logs the result (`True`/`False`).
- Returns the obtained value.

### Uses
- `core_api.board`

---

## 2. `test_footprints.py` – footprint reading

**Test name:** `smoke_footprints`

### Purpose
Verifies footprint reading: get all, search by `ref`, read position, angle, layer, size, and compare single vs batch bounding box query.

### Function
```python
run_test(logger, kicad, board, ref=None, **params) -> bool
```

**Parameters:** `ref` (optional) – component refdes; if not given, takes the first on the board.

### Logic
- Gets all footprints via `footprints.get_all(board)`.
- If board is empty – error.
- Determines target footprint: by `ref` or first.
- Reads and logs: `value`, `footprint_name`, position, angle, layer, `is_back`.
- Computes size via `get_bounding_box_mm` and `get_bounding_boxes_mm` (batch).
- Compares results – if different, test fails.
- Returns `True` if all operations succeed and sizes match.

### Uses
- `core_api.footprints`

---

## 3. `test_kicad_client.py` – connection and board retrieval

**Test name:** `smoke_kicad_client`

### Purpose
Checks that connection to KiCad is established and version/board can be obtained via `kicad_client`.

### Function
```python
run_test(logger, kicad, board, **params) -> bool
```

### Logic
- Calls `kicad_client.get_version(kicad)` – should return non‑empty string.
- Calls `kicad_client.get_board(kicad)` – should return a board object (not `None`).
- Returns `True` if both succeed.

### Uses
- `core_api.kicad_client`

---

## 4. `test_nets.py` – net reading

**Test name:** `smoke_nets`

### Purpose
Verifies getting all nets and searching for a specific one by name.

### Function
```python
run_test(logger, kicad, board, net="GND", **params) -> bool
```

**Parameters:** `net` – net name to search (default `"GND"`).

### Logic
- Gets all nets via `nets.get_all(board)`.
- If no nets – error.
- Searches for net by name via `nets.get_by_name(board, net)`.
- If not found – error.
- Logs the found net.
- Returns `True` if search succeeds.

### Uses
- `core_api.nets`

---

## 5. `test_pads.py` – pad reading

**Test name:** `smoke_pads`

### Purpose
Verifies obtaining pads of a footprint, search by number, read position, size, angle, and net.

### Function
```python
run_test(logger, kicad, board, ref=None, pad="1", **params) -> bool
```

**Parameters:**
- `ref` – component refdes (required).
- `pad` – pad number (default `"1"`).

### Logic
- Finds footprint by `ref` via `footprints.get_by_ref`.
- Gets all pads via `pads.get_all(fp)`.
- If no pads – error.
- Searches for pad by number via `pads.get_by_number(fp, pad)`. If not found, takes the first.
- Reads and logs: position, `net`, size, angle.
- Returns `True` if all succeed.

### Uses
- `core_api.footprints`, `core_api.pads`

---

## 6. `test_selection.py` – selection description

**Test name:** `smoke_selection`

### Purpose
Reads and describes the current selection in the PCB editor. Unlike the old version, it does **not block** user input, but simply reads the state.

### Function
```python
run_test(logger, kicad, board, **params) -> bool
```

### Logic
- Calls `selection.describe_selected(board)`.
- If nothing is selected – logs that and returns `True` (no selection is not an error).
- Otherwise, logs each selected component with its pads (position, size, nets).
- Returns `True`.

### Uses
- `core_api.selection`

---

## 7. `test_vias.py` – create and delete test via

**Test name:** `smoke_vias`

### Purpose
Verifies creating and deleting a via via `core_api.vias`. Creates a via near the specified component, then immediately deletes it – board remains clean.

### Function
```python
run_test(logger, kicad, board, ref=None, net="GND", **params) -> bool
```

**Parameters:**
- `ref` – component refdes (required).
- `net` – net for via (default `"GND"`).

### Logic
- Finds component by `ref`.
- Finds net by name.
- Computes via position (2 mm X offset from component centre).
- Creates via object via `vias.make`.
- Inside `commit_with_retry`:
  - calls `board.create_items([via])`, saves created `id`.
- If creation succeeds, inside a second transaction:
  - calls `vias.remove_by_id(board, created_id)`.
- Logs success or error.
- Returns `True` if both creation and deletion succeed.

### Uses
- `core_api.footprints`, `core_api.nets`, `core_api.vias`, `core_api.board` (commit_with_retry)

### Important Notes
- Test is **safe** because it always deletes the created via.
- If deletion fails, a warning about "leftover" on the board is logged.

---

## 8. `test_zones.py` – zone reading

**Test name:** `smoke_zones`

### Purpose
Finds a zone by name and reads its outline points.

### Function
```python
run_test(logger, kicad, board, zone=None, **params) -> bool
```

**Parameters:** `zone` – zone name (required, otherwise test is skipped).

### Logic
- If `zone` not passed – logs warning and returns `True` (skip).
- Searches for zone via `zones.get_by_name(board, zone)`.
- If not found – error.
- Gets outline points via `zones.get_boundary_points(z)`.
- Checks that there are at least 3 points.
- Returns `True` if zone found and outline valid.

### Uses
- `core_api.zones`

---

## General Characteristics of the `smoke` Suite

| Test | Dangerous | Parameters | Purpose |
|------|-----------|------------|---------|
| `smoke_board_commit` | no | – | transaction check |
| `smoke_footprints` | no | `ref` (opt.) | component and size reading |
| `smoke_kicad_client` | no | – | connection and version |
| `smoke_nets` | no | `net` (opt.) | net reading |
| `smoke_pads` | no | `ref` (req.), `pad` (opt.) | pad reading |
| `smoke_selection` | no | – | selection description |
| `smoke_vias` | no (create/delete) | `ref` (req.), `net` (opt.) | via create/delete |
| `smoke_zones` | no | `zone` (req.) | zone reading |

All tests use `needs_kicad=True` and receive `kicad` and `board` from the runner. They **do not leave changes** on the board (via is created and deleted). The `smoke` suite is enabled (`enabled: true`) by default in the config, as it is safe.

### Running

```bash
python -m runner.run --config config.yaml --board 10CL006 --suite smoke
```

Or a single test with required parameters (e.g., `ref` for `smoke_footprints`):

```bash
python -m runner.run --config config.yaml --test smoke_footprints
```

Parameters are substituted from the board profile in the config.

---

# `tests/static` — Static Contract Checks of the `kipy` Library

The `tests/static/` directory contains **one file** – `test_kipy_contract.py`, which implements **static contract tests**. These tests **do not require a running KiCad** and do not open an IPC connection – they analyse only types, attributes, method signatures, and object behaviour **directly during import** of the `kicad-python` (kipy) library. They serve for early detection of API incompatibilities that could lead to:

- **silent no‑op operations** (e.g., assigning to a copy of an object);
- **exceptions** (e.g., passing wrong type to a setter);
- **data loss** (e.g., ignoring rotation angle or component layer);
- use of **deprecated or unstable** APIs.

All tests are registered in the `static` suite, marked `dangerous=False`, **do not use** `needs_kicad` (default `False`), so the runner does not pass `kicad`/`board` objects. They run quickly and safely, ideal for CI/CD.

---

## File: `test_kipy_contract.py`

This file contains 12 separate checks, each emulating a specific bug found in `KiCadTemplateCloner` or `KiCadDecapPlacer` tools, or verifying documentation/behaviour of `kipy` against reality.

All checks use the `inspect` module for signature and docstring analysis, and create class instances to check for attributes/methods.

---

## List of Tests (Functions)

### 1. `static_via_drill_attribute_name`

**Test name:** `static_via_drill_attribute_name`

**Purpose:** Checks that a `Via` object has a flat attribute `drill_diameter`, not nested `drill.diameter` (as mistakenly used in `KiCadTemplateCloner`).

**Logic:**
- Creates a `Via` instance.
- Checks `hasattr(v, "drill")` (should be `False`) and `hasattr(v, "drill_diameter")` (should be `True`).
- Logs result.

**Bug source:** `extractor.py:99`, `applier.py:20` – accessing `via.drill.diameter`.

**Expected:** `has_flat_drill=True`, `has_nested_drill=False`.

---

### 2. `static_footprint_orientation_property_name`

**Test name:** `static_footprint_orientation_property_name`

**Purpose:** Checks that an `Angle` object has a property `degrees`, not a method `as_degrees()` (which was used in `extractor.py` and always returned `False`, losing the angle).

**Logic:**
- Creates `Angle.from_degrees(45.0)`.
- Checks `hasattr(a, "as_degrees")` (should be `False`) and `a.degrees == 45.0` (should be `True`).
- Logs result.

**Bug source:** `extractor.py:80` – `hasattr(fp.orientation, 'as_degrees')` always `False`, angle lost.

**Expected:** `has_method=False`, property `degrees` works.

---

### 3. `static_footprint_get_layer_method`

**Test name:** `static_footprint_get_layer_method`

**Purpose:** Checks that `FootprintInstance` has a property `layer`, not a method `get_layer()` (which was used in `extractor.py` and absent).

**Logic:**
- Creates `FootprintInstance()`.
- Checks `hasattr(fp, "get_layer")` (should be `False`) and `hasattr(fp, "layer")` (should be `True`).
- Logs result.

**Bug source:** `extractor.py:78` – calling `fp.get_layer()` leads to error or hardcoded `'F.Cu'`.

**Expected:** `has_method=False`, property `layer` exists.

---

### 4. `static_getter_returns_copy_not_reference`

**Test name:** `static_getter_returns_copy_not_reference`

**Purpose:** **Critical check** that getters like `.position` return a **copy** of the object, not a reference. Assigning to `.x` on that copy is a silent no‑op, the position does not change. This is the most important bug found in `applier.py`.

**Logic:**
- Creates `FootprintInstance`, sets `position = Vector2(1_000_000, 2_000_000)`.
- Saves `before_x = fp.position.x`.
- Executes `fp.position.x = 99_000_000` (as in `applier.py`).
- Reads `after_x = fp.position.x`.
- Checks that `after_x == before_x` and `after_x != 99_000_000` – proving the no‑op.

**Bug source:** `applier.py:17-19, 73-74` – `fp.position.x = ...` and `via.position.x = ...`.

**Expected:** `is_noop=True` – confirming that such code does not work.

**Fix:** reassign the whole object: `fp.position = Vector2(...)`.

---

### 5. `static_net_assignment_via_attribute_is_noop`

**Test name:** `static_net_assignment_via_attribute_is_noop`

**Purpose:** Similar to above, but for `.net.name`. Assigning `via.net.name = ...` is also a silent no‑op because `.net` returns a copy.

**Logic:**
- Creates `Via`, sets `net = Net(name="GND")`.
- Saves `before_name = v.net.name`.
- Executes `v.net.name = "CHANGED_VIA_ATTRIBUTE_ASSIGNMENT"`.
- Reads `after_name = v.net.name`.
- Checks that name did not change.

**Bug source:** `applier.py:23, 39` – `via.net.name = ...` / `tr.net.name = ...`.

**Expected:** `is_noop=True`.

**Fix:** assign the whole `Net` object: `via.net = net_obj`.

---

### 6. `static_orientation_setter_rejects_raw_float`

**Test name:** `static_orientation_setter_rejects_raw_float`

**Purpose:** Checks that the `.orientation` setter only accepts an `Angle` object, not a raw number (radians or degrees). In `applier.py`, `math.radians(comp.angle)` was passed, causing `TypeError`.

**Logic:**
- Creates `FootprintInstance()`.
- Attempts `fp.orientation = math.radians(45.0)`.
- Catches exception and logs its type/message.
- Returns `True` if exception occurred (confirms bug).

**Bug source:** `applier.py:78` – `fp.orientation = math.radians(comp.angle)`.

**Expected:** `raised=True` (exception).

---

### 7. `static_push_commit_requires_commit_argument`

**Test name:** `static_push_commit_requires_commit_argument`

**Purpose:** Checks the signature of `Board.push_commit` – required first argument `commit`. In `applier.py`, they called `board.push_commit()` without arguments, causing `TypeError`.

**Logic:**
- Gets signature of `Board.push_commit` via `inspect.signature`.
- Checks if there is a parameter named `commit` and if it is required (no default).
- Logs the signature and result.

**Bug source:** `applier.py:92` – `board.push_commit()`.

**Expected:** `commit_required=True`.

---

### 8. `static_pad_has_no_footprint_backreference`

**Test name:** `static_pad_has_no_footprint_backreference`

**Purpose:** Checks the assertion from `KiCadTemplateCloner` README that a pad (from `board.get_pads()`) has no back‑reference to its footprint. This justified the need for geometric mapping.

**Logic:**
- Creates `Pad` instance.
- Checks for attributes indicating ownership (`footprint`, `parent`, `reference`, `footprint_reference`, `owner`).
- Returns `True` if none exist.

**Source:** `KiCadTemplateCloner` README.

**Expected:** `ok=True` – confirms absence of back‑reference in flat list.

**Note:** the next test shows a workaround.

---

### 9. `static_footprint_definition_items_contains_pads`

**Test name:** `static_footprint_definition_items_contains_pads`

**Purpose:** Checks that `FootprintInstance.definition.items` can be filtered for objects of type `Pad` – they already belong to that footprint, so geometric mapping is not needed if the footprint is known.

**Logic:**
- Creates `FootprintInstance()`.
- Checks existence of `definition` and `definition.items`.
- Logs result.

**Source:** `ipc_tests/component_utils.py` – workaround for `board.get_pads()`.

**Expected:** `has_items=True`.

---

### 10. `static_run_action_is_documented_unstable`

**Test name:** `static_run_action_is_documented_unstable`

**Purpose:** Checks that the docstring of `KiCad.run_action` contains a warning about API instability (action names may change). This confirms that using `run_action` is a conscious risk.

**Logic:**
- Gets docstring of `KiCad.run_action`.
- Checks for presence of the word `unstable` (case‑insensitive).
- Logs part of the docstring.

**Expected:** `warns_unstable=True`.

---

### 11. `static_refill_zones_default_is_blocking`

**Test name:** `static_refill_zones_default_is_blocking`

**Purpose:** Checks that `Board.refill_zones` has parameter `block` defaulting to `True`. This disproves the hypothesis that the busy bug arose because someone forgot to specify `block=True` – on the contrary, someone explicitly passed `block=False`.

**Logic:**
- Gets signature of `Board.refill_zones`.
- Finds parameter `block` and checks its default value.
- Logs the signature.

**Expected:** `default_is_true=True`.

---

### 12. `static_net_code_deprecated_but_present`

**Test name:** `static_net_code_deprecated_but_present`

**Purpose:** Checks that the `Net.code` property is marked as deprecated in the documentation. This confirms the warning in `core_api.nets.build_net_map`.

**Logic:**
- Gets the `Net.code` property.
- Extracts its docstring (or the getter's docstring).
- Checks for presence of the word `deprecat` (case‑insensitive).
- Logs part of the docstring.

**Expected:** `looks_deprecated=True`.

---

## General Characteristics of the `static` Suite

| Test Name | Checks | Dangerous | Needs KiCad |
|-----------|--------|-----------|-------------|
| `static_via_drill_attribute_name` | existence of `drill_diameter` | no | no |
| `static_footprint_orientation_property_name` | `degrees` property vs `as_degrees` method | no | no |
| `static_footprint_get_layer_method` | `layer` property vs `get_layer` method | no | no |
| `static_getter_returns_copy_not_reference` | no‑op on `fp.position.x = ...` | no | no |
| `static_net_assignment_via_attribute_is_noop` | no‑op on `via.net.name = ...` | no | no |
| `static_orientation_setter_rejects_raw_float` | setter `.orientation` only accepts `Angle` | no | no |
| `static_push_commit_requires_commit_argument` | `commit` mandatory in `push_commit` | no | no |
| `static_pad_has_no_footprint_backreference` | absence of back‑reference in `Pad` | no | no |
| `static_footprint_definition_items_contains_pads` | existence of `definition.items` in footprint | no | no |
| `static_run_action_is_documented_unstable` | `run_action` instability (documentation) | no | no |
| `static_refill_zones_default_is_blocking` | default `block=True` | no | no |
| `static_net_code_deprecated_but_present` | deprecation of `Net.code` | no | no |

---

## Running and Configuration

Tests from `static` **do not require** a running KiCad and can be executed even without an open board. They are registered in the `static` suite and are enabled by default (`enabled: true`). Run:

```bash
python -m runner.run --config config.yaml --suite static
```

Or a single test:

```bash
python -m runner.run --config config.yaml --test static_getter_returns_copy_not_reference
```

In the config for `static`, no `board` or `ref` parameters are needed – they are ignored (tests do not use `needs_kicad`).

---

# `tests/toy` — Dummy Tests for Runner Mechanism Validation

The `tests/toy/` directory contains **dummy tests** intended solely for verifying and debugging the **runner** itself, not for interacting with KiCad. They do not require a running KiCad, do not use IPC, and do not modify the board. These tests help ensure that:

- configuration is loaded and applied;
- test selection (by suite, by name, respecting `enabled`/`dangerous`) works correctly;
- parameters are substituted via `resolve_params`;
- exceptions are caught and logged;
- final report is generated correctly.

All tests are registered in the `toy` suite, default `dangerous=False` (except one), `needs_kicad=False` (do not require a connection). In production environments, this suite is usually **disabled** (`enabled: false`) to avoid cluttering logs.

---

## Directory Structure

```
tests/toy/
├── __init__.py
└── dummy_tests.py
```

---

## File: `dummy_tests.py`

Contains 5 dummy tests covering various execution scenarios.

---

### 1. `dummy_ok` – successful test

**Function:** `run_dummy_ok(logger, **params) -> bool`

**Behaviour:** Always returns `True`. Logs received parameters.

**Purpose:** Tests successful test execution – runner should count it as `PASS`.

---

### 2. `dummy_fail` – failing test

**Function:** `run_dummy_fail(logger, **params) -> bool`

**Behaviour:** Always returns `False`. Logs a message.

**Purpose:** Tests handling of a failing test – runner should count it as `FAIL` and include in final statistics.

---

### 3. `dummy_raises` – test that raises an exception

**Function:** `run_dummy_raises(logger, **params) -> bool`

**Behaviour:** Raises `RuntimeError` with a message "deliberate error to check runner exception handling".

**Purpose:** Tests that the runner catches the exception, logs it (with traceback), counts the test as failed, and continues with the remaining tests.

---

### 4. `dummy_needs_params` – test that requires parameters

**Function:** `run_dummy_needs_params(logger, ref=None, pad=None, **params) -> bool`

**Behaviour:** Returns `True` only if `ref` and `pad` are not `None`. Logs the passed values.

**Purpose:** Tests the `resolve_params` mechanism – that parameters from the board profile and test are correctly merged and overridden.

---

### 5. `dummy_dangerous` – dangerous (by flag) test

**Function:** `run_dummy_dangerous(logger, **params) -> bool`

**Registration:** `@register("dummy_dangerous", suite="toy", dangerous=True)`

**Behaviour:** Always returns `True`, but logs a warning: _"this test actually ran — if you see this without explicit enabled:true in config, the protection failed!"_

**Purpose:** Verifies that dangerous tests **do not run** without explicit `enabled: true` in the config, even if they are included in a suite. This is critical protection against accidental dangerous mutations.

---

## General Characteristics of the `toy` Suite

| Test | Returns | Exception | Parameters | Dangerous |
|------|---------|-----------|------------|-----------|
| `dummy_ok` | `True` | no | no | no |
| `dummy_fail` | `False` | no | no | no |
| `dummy_raises` | – | `RuntimeError` | no | no |
| `dummy_needs_params` | `True` when `ref` and `pad` provided | no | `ref`, `pad` | no |
| `dummy_dangerous` | `True` | no | no | **yes** |

All tests use `needs_kicad=False` (default), so the runner **does not pass** `kicad`/`board` objects.

---

## Running and Configuration

The `toy` suite is usually **disabled** in production configs (`enabled: false`), but can be enabled for runner debugging.

Example enabling in YAML:

```yaml
suites:
  toy:
    enabled: true
    tests:
      dummy_ok:
        enabled: true
      dummy_fail:
        enabled: true
      dummy_raises:
        enabled: true
      dummy_needs_params:
        enabled: true
        params:
          ref: "C1"
          pad: "1"
      dummy_dangerous:
        enabled: false   # dangerous – must be explicitly enabled
```

Run:

```bash
python -m runner.run --config config.yaml --suite toy
```

Or a single test:

```bash
python -m runner.run --config config.yaml --test dummy_needs_params
```

For `dummy_needs_params`, parameters can be passed via config (as above) or via `--board` profile if the profile contains `ref` and `pad`.

---

## 1. `kicad_client.py` — connection and basic actions

All official documentation for KiCad Python bindings (`kicad-python`) is available at: **[https://docs.kicad.org/kicad-python-main/](https://docs.kicad.org/kicad-python-main/)**.

| Function / Class | Documentation |
| :--- | :--- |
| `kipy.KiCad` (constructor) | [KiCad — kicad-python documentation](https://docs.kicad.org/kicad-python-main/kicad.html#kipy.KiCad) |
| `kipy.KiCad.get_board()` | [KiCad.get_board](https://docs.kicad.org/kicad-python-main/kicad.html#kipy.KiCad.get_board) |
| `kipy.KiCad.get_version()` | [KiCad.get_version](https://docs.kicad.org/kicad-python-main/kicad.html#kipy.KiCad.get_version) |
| `kipy.KiCad.run_action()` | [KiCad.run_action](https://docs.kicad.org/kicad-python-main/kicad.html#kipy.KiCad.run_action) — **unstable API** (official warning) |

---

## 2. `board.py` — board and transactions

| Function / Class | Documentation |
| :--- | :--- |
| `kipy.board.Board` | [Board — kicad-python documentation](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board) |
| `Board.begin_commit()` | [Board.begin_commit](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.begin_commit) |
| `Board.push_commit()` | [Board.push_commit](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.push_commit) |
| `Board.drop_commit()` | [Board.drop_commit](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.drop_commit) |
| `Board.create_items()` | [Board.create_items](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.create_items) |
| `Board.update_items()` | [Board.update_items](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.update_items) |
| `Board.remove_items_by_id()` | [Board.remove_items_by_id](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.remove_items_by_id) |
| `Board.get_item_bounding_box()` | [Board.get_item_bounding_box](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.get_item_bounding_box) |
| `Board.get_copper_layer_count()` | [Board.get_copper_layer_count](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.get_copper_layer_count) |
| `Board.get_project()` | [Board.get_project](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.get_project) |
| `Board.get_selection()` | [Board.get_selection](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.get_selection) |
| `Board.add_to_selection()` | [Board.add_to_selection](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.add_to_selection) |
| `Board.clear_selection()` | [Board.clear_selection](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.clear_selection) |
| `Board.refill_zones()` | [Board.refill_zones](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.refill_zones) |

---

## 3. `geometry.py` — geometric primitives

| Function / Class | Documentation |
| :--- | :--- |
| `kipy.geometry.Vector2` | [Vector2 — kicad-python documentation](https://docs.kicad.org/kicad-python-main/utilities.html#kipy.geometry.Vector2) |
| `Vector2.from_xy()` | [Vector2.from_xy](https://docs.kicad.org/kicad-python-main/utilities.html#kipy.geometry.Vector2.from_xy) |
| `kipy.geometry.Angle` | [Angle — kicad-python documentation](https://docs.kicad.org/kicad-python-main/utilities.html#kipy.geometry.Angle) |
| `Angle.from_degrees()` | [Angle.from_degrees](https://docs.kicad.org/kicad-python-main/utilities.html#kipy.geometry.Angle.from_degrees) |
| `Angle.degrees` (property) | [Angle.degrees](https://docs.kicad.org/kicad-python-main/utilities.html#kipy.geometry.Angle.degrees) |
| `kipy.geometry.Box2` | [Box2 — kicad-python documentation](https://docs.kicad.org/kicad-python-main/utilities.html#kipy.geometry.Box2) |

---

## 4. `footprints.py` — working with components

| Function / Class | Documentation |
| :--- | :--- |
| `kipy.board_types.FootprintInstance` | [FootprintInstance — kicad-python documentation](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.FootprintInstance) |
| `Board.get_footprints()` | [Board.get_footprints](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.get_footprints) |

**Fields/properties of `FootprintInstance`:**
| Field | Documentation |
| :--- | :--- |
| `.reference_field` | [FootprintInstance.reference_field](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.FootprintInstance.reference_field) |
| `.value_field` | [FootprintInstance.value_field](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.FootprintInstance.value_field) |
| `.definition` | [FootprintInstance.definition](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.FootprintInstance.definition) |
| `.position` | [FootprintInstance.position](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.FootprintInstance.position) |
| `.orientation` | [FootprintInstance.orientation](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.FootprintInstance.orientation) |
| `.layer` | [FootprintInstance.layer](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.FootprintInstance.layer) |

---

## 5. `pads.py` — working with pads

| Function / Class | Documentation |
| :--- | :--- |
| `kipy.board_types.Pad` | [Pad — kicad-python documentation](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.Pad) |
| `Pad.number` | [Pad.number](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.Pad.number) |
| `Pad.position` | [Pad.position](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.Pad.position) |
| `Pad.net` | [Pad.net](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.Pad.net) |
| `Pad.padstack` | [Pad.padstack](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.Pad.padstack) |

---

## 6. `nets.py` — working with nets

| Function / Class | Documentation |
| :--- | :--- |
| `kipy.board_types.Net` | [Net — kicad-python documentation](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.Net) |
| `Net.name` | [Net.name](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.Net.name) |
| `Net.code` | [Net.code](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.Net.code) — **deprecated** |
| `Board.get_nets()` | [Board.get_nets](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.get_nets) |

---

## 7. `vias.py` — working with vias

| Function / Class | Documentation |
| :--- | :--- |
| `kipy.board_types.Via` | [Via — kicad-python documentation](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.Via) |
| `Via.position` | [Via.position](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.Via.position) |
| `Via.net` | [Via.net](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.Via.net) |
| `Via.drill_diameter` | [Via.drill_diameter](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.Via.drill_diameter) |
| `Via.diameter` | [Via.diameter](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.Via.diameter) |
| `Board.get_vias()` | [Board.get_vias](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.get_vias) |

---

## 8. `zones.py` — working with zones

| Function / Class | Documentation |
| :--- | :--- |
| `kipy.board_types.Zone` | [Zone — kicad-python documentation](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.Zone) |
| `Zone.name` | [Zone.name](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.Zone.name) |
| `Zone.outline` | [Zone.outline](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.Zone.outline) |
| `Board.get_zones()` | [Board.get_zones](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.get_zones) |

---

## 9. `selection.py` — working with selection

| Function / Class | Documentation |
| :--- | :--- |
| `kipy.board_types.Group` | [Group — kicad-python documentation](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.Group) |
| `Group.proto` | **Undocumented internal field** – no official link |

---

## 10. `project.py` — project information

| Function / Class | Documentation |
| :--- | :--- |
| `kipy.board.Project` | [Project — kicad-python documentation](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Project) |
| `Project.path` | [Project.path](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Project.path) |
| `Project.name` | [Project.name](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Project.name) |
| `Board.get_project()` | [Board.get_project](https://docs.kicad.org/kicad-python-main/board.html#kipy.board.Board.get_project) |

---

## 11. Other Types and Constants

| Component | Documentation |
| :--- | :--- |
| `kipy.board_types.BoardLayer` | [BoardLayer — kicad-python documentation](https://docs.kicad.org/kicad-python-main/board.html#kipy.board_types.BoardLayer) |
| `kipy.proto.common.types.KIID` | [KIID — kicad-python documentation](https://docs.kicad.org/kicad-python-main/kicad.html#kipy.proto.common.types.KIID) |
| `kipy.proto.common.types.KiCadObjectType` | [KiCadObjectType — kicad-python documentation](https://docs.kicad.org/kicad-python-main/kicad.html#kipy.proto.common.types.KiCadObjectType) |

---

## Documentation Missing in the Official API

The following elements **do not have** official documentation because they are either unstable or internal:

| Element | Status | Reason |
| :--- | :--- | :--- |
| `KiCad.run_action()` | **Unstable** | Official warning in documentation |
| `Group.proto.items` | **Undocumented** | Internal protobuf field |
| `FootprintInstance.definition.items` | **Undocumented** | Access to internal definition structure |
| `Net.code` | **Deprecated** | Marked as deprecated, will be removed |
| `kicad-cli` (external tool) | **External** | Not part of Python API |

---

## Alternative Documentation (SWIG / pcbnew)

For some operations, the documentation for the "classic" Python API **pcbnew** (SWIG bindings) may also be useful:

- [pcbnew.BOARD Class Reference (Doxygen)](https://docs.kicad.org/doxygen-python-7.0/classpcbnew_1_1BOARD.html)
- [KiCad Pcbnew Python Scripting](https://docs.kicad.org/doxygen-python-7.0/) – general index

> **Important:** The modern IPC API (`kicad-python`) is gradually replacing SWIG bindings, but pcbnew documentation can still be helpful for understanding object internals.

# Use of Unstable, Undocumented, and Deprecated APIs

The toolkit is designed to solve real automation and testing tasks for the KiCad PCB editor. Some of these tasks **cannot** be performed while strictly staying within the stable public API provided by the `kipy` library. Therefore, the project intentionally uses:

- **unstable** (officially not guaranteed) methods;
- **undocumented** internal fields;
- **deprecated** properties;
- **workarounds** to compensate for illogical getter/setter behaviour;
- **external CLI tools** where IPC is insufficient.

All such places are **documented** in the code, and their functionality is **verified** by static contract tests (the `static` suite). This allows early detection of breakage when updating KiCad or `kipy`.

---

## 1. Unstable APIs

### `kicad.run_action(action)`

**Where used:**  
- `core_api/footprints.py` – `flip_selected()` calls `kicad.run_action("pcbnew.InteractiveEdit.flip")`.  
- Diagnostic tests (`test_flip_one_cap.py`, `test_flip_then_update_items.py`).

**Why:**  
This is the **only** way to perform a "true" component flip with mirroring of pads and silkscreen. Simply changing the `.layer` field does not give the desired effect – the component visually remains unchanged.

**Risk:**  
The `run_action` method and action names (e.g., `pcbnew.InteractiveEdit.flip`) are officially marked in the `kipy` documentation as **unstable**. They may be changed or removed in any KiCad version without warning.

**Alternative:**  
None – without this, a correct flip is impossible.

**Protection:**  
The static test `static_run_action_is_documented_unstable` checks that the `kipy` documentation contains the instability warning. When the library is updated, the test will warn if the warning disappears (which may indicate API changes).

---

## 2. Undocumented Internal Fields

### `Group.proto.items` to obtain group members

**Where used:**  
- `core_api/selection.py` – `get_selected_uuids()`.

**Why:**  
In `kipy`, the `Group` object has a property `.items`, but it is **always empty** (a local cache, not synchronised with the server). The real group members are stored in the internal protobuf field `.proto.items`, which is used instead.

**Risk:**  
This is an internal data structure that may change in `kipy` updates without notice.

**Alternative:**  
One could iterate over all board items and check if each belongs to the group (by UUID), but this is inefficient and does not guarantee that the group actually contains those items.

**Protection:**  
Tests that use selection (`smoke_selection`) indirectly verify this workaround.

---

### `FootprintInstance.definition.items` to obtain pads

**Where used:**  
- `core_api/pads.py` – `get_all(fp)`.

**Why:**  
`board.get_pads()` returns a flat list of all board pads **without a back‑reference** to the parent footprint. This is confirmed by the static test `static_pad_has_no_footprint_backreference`.  
To get pads of a specific footprint, we use `fp.definition.items` – the collection of all items of the footprint definition (graphics, pads, etc.), filtering only objects of type `Pad`.

**Risk:**  
The field `definition.items` is not an official public API, although it has been stable in all `kipy` versions and is widely used by the community.

**Alternative:**  
Geometric mapping (finding the nearest pad by coordinates) is unreliable, especially when components are close together.

**Protection:**  
The static test `static_footprint_definition_items_contains_pads` checks for the existence of this field, warning of possible changes.

---

## 3. Deprecated APIs

### `Net.code`

**Where used:**  
- `core_api/nets.py` – `build_net_map()` (only for debug output).

**Why:**  
The `build_net_map` function builds a dictionary `{code: name}` of all nets. This can be useful for diagnostics or backward compatibility with old code.

**Risk:**  
The `Net.code` property is marked in the `kipy` documentation as **deprecated** (will be removed in future versions). Clients are advised not to rely on net codes.

**Alternative:**  
Use direct `Net` objects by name – which is done in all main scenarios (search by name, pad binding). `build_net_map` is used only for debugging and is not critical.

**Protection:**  
The static test `static_net_code_deprecated_but_present` checks for the deprecation warning in the documentation, so we know when the property disappears.

---

## 4. Non‑standard Getter/Setter Behaviour

### Getters return copies (assigning to attributes is a no‑op)

**Where used:**  
This is not a direct usage, but a **warning** for developers.  
In the project code, **nowhere** is the construct `obj.attribute.x = value` used – everywhere we reassign the whole object (e.g., `fp.position = Vector2(...)`).

**Problem:**  
In `kipy`, getters (e.g., `.position`, `.net`) return a **copy** of the object, not a reference. Assigning to an attribute of that copy (e.g., `fp.position.x = 1000`) does **not** change the original – it is a silent no‑op. This error was present in early versions of `KiCadTemplateCloner` and has been fixed in the current project.

**Confirmation:**  
Static tests `static_getter_returns_copy_not_reference` and `static_net_assignment_via_attribute_is_noop` explicitly demonstrate this behaviour.

**Alternative:**  
Always reassign the whole object: `fp.position = Vector2.from_xy(...)`.

---

### Setter `FootprintInstance.orientation` does not accept `float`

**Where used:**  
In the project code, we always use `Angle.from_degrees()` or `Angle.from_radians()` to set orientation. We never pass a raw number.

**Problem:**  
The setter `.orientation` expects an `Angle` object. Passing a number (e.g., `math.radians(45)`) raises `TypeError`. This was identified in `KiCadTemplateCloner` as the cause of failure on the first component.

**Confirmation:**  
The static test `static_orientation_setter_rejects_raw_float` reproduces this error.

**Alternative:**  
Always use `Angle.from_degrees()`.

---

## 5. External Tools (outside IPC)

### `kicad-cli` for netlist export

**Where used:**  
- `tests/safe/test_cli_netlist.py` – netlist export via CLI.

**Why:**  
Netlist export is **not available** through the `kipy` IPC interface. The only way to obtain a netlist in an automated manner is to run `kicad-cli` as an external process.

**Risk:**  
- Dependency on having `kicad-cli` installed and available in `PATH`.
- The command‑line interface may change between KiCad versions.

**Alternative:**  
None within IPC.

**Protection:**  
- The `cli_utils.find_kicad_cli()` utility searches for the executable in several standard locations and via the `KICAD_CLI_PATH` environment variable.
- The `safe_cli_netlist` test logs errors if `kicad-cli` is not found or fails.

---

## Conclusion

The project **consciously** uses APIs that go beyond the stable public interface, because only this allows solving real automation and testing tasks. However, all such places are:

- **clearly documented** in code comments;
- **accompanied by static contract tests** (the `static` suite) that check the existence and behaviour of these APIs;
- **provided with workarounds** (e.g., reassigning objects instead of modifying attributes) to minimise risks.

Thus, the toolkit remains reliable even in the face of an unstable API, and when KiCad or `kipy` is updated, the static tests will timely signal potential problems.