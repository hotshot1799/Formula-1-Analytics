"""
Centralized FastF1 configuration.

This module initializes the FastF1 cache *and* sets the Ergast API base
URL exactly once.  Importing it from multiple files is safe -- Python's
import system guarantees the top-level code runs only once.
"""
import os
import logging
import fastf1

# ── Cache ──
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "f1_dashboard")
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

# ── Ergast API base URL ──
try:
    fastf1.ergast.interface.BASE_URL = "https://api.jolpi.ca/ergast/f1"
except Exception as e:
    logging.warning(f"Could not set custom Ergast URL, using default: {e}")
