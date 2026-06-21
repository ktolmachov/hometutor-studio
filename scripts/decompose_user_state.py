import ast
import os

CORE_FILE = 'app/user_state_core.py'
LINEAGE_FILE = 'app/user_state_lineage.py'
GOALS_FILE = 'app/user_state_goals.py'

LINEAGE_SYMBOLS = {
    "_LEARNER_STATE_GENERATION_KV_KEY",
    "_LEARNER_STATE_INDEX_VERSION_KV_KEY",
    "_LEARNER_STATE_MIGRATED_AT_KV_KEY",
    "_ARCHIVE_STATE_TABLES",
    "_ALLOWED_ARCHIVE_STATE_TABLES",
    "_normalize_archive_state_table",
    "_read_kv_row",
    "_upsert_kv_row",
    "_insert_learner_profile_migration_log",
    "get_current_learner_state_lineage",
    "_active_concept_ids_for_lineage",
    "_facade_override",
    "_lineage_sync_action",
    "_archive_spaced_repetition_row",
    "_archive_quiz_mastery_row",
    "sync_current_learner_state_lineage",
    "run_learner_state_lineage_sync",
    "get_learner_state_diagnostics",
    "list_learner_profile_migration_log",
    "_archive_rows_for_filters",
    "list_archived_learner_state",
    "restore_archived_learner_state",
    "purge_archived_learner_state",
}

GOALS_SYMBOLS = {
    "_LEARNER_GOAL_SNAPSHOT_SCHEMA_VERSION",
    "LEARNER_GOAL_SNAPSHOT_SCHEMA_VERSION",
    "_LEARNER_GOAL_SNAPSHOT_STUB",
    "normalize_learner_goal_snapshot_payload",
    "get_learner_goal_snapshot",
    "upsert_learner_goal_snapshot",
    "clear_learner_goal_snapshot",
    "learner_goal_snapshot_api_empty",
    "_iso_week_id",
    "increment_weekly_progress",
    "get_weekly_goals_state",
    "_normalize_learner_profile",
    "get_learner_profile",
    "save_learner_profile",
    "get_preferred_style",
    "set_preferred_style",
}

def extract_funcs(filepath, symbol_lists):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    node = ast.parse(content)
    
    ranges_to_remove = []
    
    extracted_contents = []
    
    lines = content.split('\n')
    
    for _ in range(len(symbol_lists)):
        extracted_contents.append([])
    
    for n in node.body:
        matched = -1
        
        if isinstance(n, ast.FunctionDef):
            for i, symbols in enumerate(symbol_lists):
                if n.name in symbols:
                    matched = i
                    break
        elif isinstance(n, ast.Assign):
            targets = [t.id for t in n.targets if isinstance(t, ast.Name)]
            for i, symbols in enumerate(symbol_lists):
                if any(t in symbols for t in targets):
                    matched = i
                    break
        
        if matched != -1:
            start = n.lineno - 1
            if hasattr(n, 'decorator_list') and getattr(n, 'decorator_list', None):
                start = n.decorator_list[0].lineno - 1
            end = n.end_lineno
            ranges_to_remove.append((start, end))
            extracted_contents[matched].append('\n'.join(lines[start:end]))
    
    ranges_to_remove.sort(key=lambda x: x[0], reverse=True)
    
    for start, end in ranges_to_remove:
        del lines[start:end]
        
    new_content = '\n'.join(lines)
    return new_content, ['\n\n\n'.join(c) for c in extracted_contents]

COMMON_IMPORTS = """import json
import logging
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, TypeVar

from app.user_state_core import _with_db, _utc_now_iso, _coerce_optional_int
from app.logging_config import setup_logging

logger = setup_logging()

"""

if __name__ == '__main__':
    new_core, extracted = extract_funcs(CORE_FILE, [LINEAGE_SYMBOLS, GOALS_SYMBOLS])
    
    with open(CORE_FILE, 'w', encoding='utf-8') as f:
        f.write(new_core)
        
    with open(LINEAGE_FILE, 'w', encoding='utf-8') as f:
        f.write(COMMON_IMPORTS + extracted[0] + '\n')
        
    with open(GOALS_FILE, 'w', encoding='utf-8') as f:
        f.write(COMMON_IMPORTS + extracted[1] + '\n')
    
    print("Decomposed successfully.")
    
    with open('app/user_state.py', 'r', encoding='utf-8') as f:
        us_content = f.read()
    us_content = us_content.replace('from app.user_state_sync import *', 
                                    'from app.user_state_sync import *\nfrom app.user_state_lineage import *\nfrom app.user_state_goals import *')
    with open('app/user_state.py', 'w', encoding='utf-8') as f:
        f.write(us_content)

