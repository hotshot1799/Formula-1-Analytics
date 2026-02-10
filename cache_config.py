"""
Centralized FastF1 cache configuration.

This module initializes the FastF1 cache exactly once using a fixed,
persistent directory (~/.cache/f1_dashboard/). Importing this module
from multiple files is safe — Python's import system guarantees the
top-level code runs only once.
"""
import os
import fastf1

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "f1_dashboard")
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)
