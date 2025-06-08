# FILTERED CALL GRAPH ANALYSIS

## Core Project Functions and Their Usage

### Functions in step1.py:
132:def signal_handler(signum, frame):
139:def create_pid_file():
165:def remove_pid_file():
172:def pid_lock():
180:def get_daily_match_counter():

### Functions in step2.py:
37:def extract_summary_fields(match: dict) -> dict:
83:def extract_odds(match: dict) -> dict:
114:def extract_environment(match: dict) -> dict:
125:def extract_events(match: dict) -> list:
142:def merge_and_summarize(live_data: dict, payload_data: dict) -> dict:

### Functions in step7.py:
25:def get_eastern_time() -> str:
30:def get_status_description(status_id: int) -> str:
53:def setup_logger() -> logging.Logger:
71:def log_and_print(message: str):
81:def get_daily_fetch_count() -> int:

