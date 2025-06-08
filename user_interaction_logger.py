#!/usr/bin/env python3
"""
User Interaction Logger
Logs user commands and questions with timestamps for review
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import re

class UserInteractionLogger:
    def __init__(self, log_file: str = "user_interactions.log"):
        self.log_file = log_file
        self.json_log_file = log_file.replace('.log', '.json')
        
    def clean_text(self, text: str) -> str:
        """Clean and normalize user input text"""
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
        text = re.sub(r'`(.*?)`', r'\1', text)        # Code
        
        return text.strip()
    
    def categorize_input(self, text: str) -> str:
        """Categorize the user input as command or question"""
        text_lower = text.lower()
        
        # Command indicators
        command_keywords = [
            'create', 'delete', 'run', 'execute', 'install', 'remove',
            'update', 'modify', 'edit', 'add', 'fix', 'check', 'test',
            'build', 'deploy', 'start', 'stop', 'restart', 'configure'
        ]
        
        # Question indicators
        question_keywords = [
            'what', 'how', 'why', 'when', 'where', 'which', 'who',
            'can you', 'could you', 'would you', 'should', 'is it',
            'are there', 'do you', 'does it', 'will it', 'explain'
        ]
        
        if any(keyword in text_lower for keyword in command_keywords):
            return "COMMAND"
        elif any(keyword in text_lower for keyword in question_keywords) or text.endswith('?'):
            return "QUESTION"
        else:
            return "REQUEST"
    
    def log_interaction(self, user_input: str) -> Dict:
        """Log a user interaction with timestamp and categorization"""
        timestamp = datetime.now()
        cleaned_input = self.clean_text(user_input)
        category = self.categorize_input(cleaned_input)
        
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "date": timestamp.strftime("%Y-%m-%d"),
            "time": timestamp.strftime("%H:%M:%S"),
            "category": category,
            "original_input": user_input,
            "cleaned_input": cleaned_input,
            "character_count": len(cleaned_input),
            "word_count": len(cleaned_input.split())
        }
        
        # Write to text log
        self._write_text_log(log_entry)
        
        # Write to JSON log
        self._write_json_log(log_entry)
        
        return log_entry
    
    def _write_text_log(self, log_entry: Dict):
        """Write to human-readable text log"""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"TIMESTAMP: {log_entry['timestamp']}\n")
            f.write(f"CATEGORY:  {log_entry['category']}\n")
            f.write(f"INPUT:     {log_entry['cleaned_input']}\n")
            f.write(f"STATS:     {log_entry['word_count']} words, {log_entry['character_count']} chars\n")
    
    def _write_json_log(self, log_entry: Dict):
        """Write to JSON log for programmatic access"""
        # Load existing entries
        entries = []
        if os.path.exists(self.json_log_file):
            try:
                with open(self.json_log_file, 'r', encoding='utf-8') as f:
                    entries = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                entries = []
        
        # Add new entry
        entries.append(log_entry)
        
        # Write back to file
        with open(self.json_log_file, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    
    def get_stats(self) -> Dict:
        """Get statistics about logged interactions"""
        if not os.path.exists(self.json_log_file):
            return {"total_interactions": 0, "categories": {}, "recent_activity": []}
        
        with open(self.json_log_file, 'r', encoding='utf-8') as f:
            entries = json.load(f)
        
        categories = {}
        for entry in entries:
            cat = entry['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        recent = sorted(entries, key=lambda x: x['timestamp'], reverse=True)[:10]
        
        return {
            "total_interactions": len(entries),
            "categories": categories,
            "recent_activity": recent,
            "date_range": {
                "first": entries[0]['date'] if entries else None,
                "last": entries[-1]['date'] if entries else None
            }
        }
    
    def search_logs(self, keyword: str, category: Optional[str] = None) -> List[Dict]:
        """Search through logged interactions"""
        if not os.path.exists(self.json_log_file):
            return []
        
        with open(self.json_log_file, 'r', encoding='utf-8') as f:
            entries = json.load(f)
        
        results = []
        for entry in entries:
            if keyword.lower() in entry['cleaned_input'].lower():
                if category is None or entry['category'] == category:
                    results.append(entry)
        
        return results


def main():
    """Demo/test function"""
    logger = UserInteractionLogger()
    
    # Test with sample interactions
    test_inputs = [
        "can you create a log where any time i chat a command or a question for you",
        "run the test suite",
        "what is the current status of the project?",
        "delete the old backup files",
        "how do I configure the database connection?"
    ]
    
    print("Logging test interactions...")
    for test_input in test_inputs:
        result = logger.log_interaction(test_input)
        print(f"Logged: {result['category']} - {result['cleaned_input'][:50]}...")
    
    print("\nStatistics:")
    stats = logger.get_stats()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
