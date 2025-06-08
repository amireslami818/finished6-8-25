#!/usr/bin/env python3
"""
Auto Logger Wrapper
Automatically logs all user interactions
"""

import sys
import os
from datetime import datetime
from user_interaction_logger import UserInteractionLogger

# Initialize logger
logger = UserInteractionLogger()

def auto_log(user_input: str):
    """Automatically log user input"""
    try:
        result = logger.log_interaction(user_input)
        # Optionally print confirmation (can be disabled for silent logging)
        if os.getenv('VERBOSE_LOGGING', 'false').lower() == 'true':
            print(f"[AUTO-LOG] {result['category']}: {result['cleaned_input'][:60]}...")
        return result
    except Exception as e:
        print(f"[AUTO-LOG ERROR] Failed to log interaction: {e}")
        return None

# Auto-log this script execution if called directly
if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_input = ' '.join(sys.argv[1:])
        auto_log(user_input)
    else:
        print("Usage: python3 auto_logger.py 'your command or question here'")
        print("Or import auto_log function to use programmatically")
