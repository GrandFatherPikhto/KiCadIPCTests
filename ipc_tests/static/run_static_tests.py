#!/usr/bin/env python3
"""
run_static_tests.py — запуск контракт-тестов против установленной
kicad-python (kipy) БЕЗ живого KiCad. См. ipc_tests/static/test_kipy_contract.py
для деталей и обоснования каждого теста.
"""
from ipc_tests.static.test_kipy_contract import run_all

if __name__ == "__main__":
    run_all()
