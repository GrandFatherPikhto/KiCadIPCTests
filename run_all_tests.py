#!/usr/bin/env python3
"""
Точка входа для запуска всех тестов.
Просто импортирует и запускает test_all.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ipc_tests.tests.test_all import run_all_tests

if __name__ == "__main__":
    run_all_tests()