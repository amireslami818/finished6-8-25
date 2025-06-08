#!/usr/bin/env python3
"""
Quick Logger CLI
Simple command-line interface for logging user interactions
"""

import sys
import argparse
from user_interaction_logger import UserInteractionLogger

def main():
    parser = argparse.ArgumentParser(description='Log user interactions with AI assistant')
    parser.add_argument('text', nargs='*', help='Text to log (if not provided, will read from stdin)')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--search', type=str, help='Search for keyword in logs')
    parser.add_argument('--category', type=str, choices=['COMMAND', 'QUESTION', 'REQUEST'], 
                       help='Filter by category (use with --search)')
    parser.add_argument('--log-file', type=str, default='user_interactions.log', 
                       help='Log file path (default: user_interactions.log)')
    
    args = parser.parse_args()
    
    logger = UserInteractionLogger(args.log_file)
    
    if args.stats:
        stats = logger.get_stats()
        print("User Interaction Statistics:")
        print(f"Total interactions: {stats['total_interactions']}")
        print(f"Categories: {stats['categories']}")
        if stats['date_range']['first']:
            print(f"Date range: {stats['date_range']['first']} to {stats['date_range']['last']}")
        return
    
    if args.search:
        results = logger.search_logs(args.search, args.category)
        print(f"Found {len(results)} matching interactions:")
        for result in results[-10:]:  # Show last 10 results
            print(f"[{result['timestamp']}] {result['category']}: {result['cleaned_input']}")
        return
    
    # Log new interaction
    if args.text:
        text = ' '.join(args.text)
    else:
        print("Enter your command/question (press Ctrl+D when done):")
        text = sys.stdin.read().strip()
    
    if text:
        result = logger.log_interaction(text)
        print(f"✓ Logged as {result['category']}: {result['cleaned_input'][:80]}...")
        print(f"  Saved to: {args.log_file}")
    else:
        print("No text provided to log.")

if __name__ == "__main__":
    main()
