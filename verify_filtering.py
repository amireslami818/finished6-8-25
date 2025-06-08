#!/usr/bin/env python3
"""
Verify that the odds filtering worked correctly
"""

import json

def verify_filtering():
    """Check that all odds entries have minute fields between 2 and 6"""
    with open('/root/6-4-2025/step2.json', 'r') as f:
        data = json.load(f)
    
    print("Verifying filtered data...")
    print("-" * 50)
    
    total_entries = 0
    minute_counts = {}
    invalid_entries = []
    
    for i, summary in enumerate(data.get('summaries', [])):
        if 'odds' in summary:
            for company_id, odds_data in summary['odds'].items():
                for odds_type in ['asia', 'bs', 'eu', 'cr']:
                    if odds_type in odds_data:
                        for entry in odds_data[odds_type]:
                            total_entries += 1
                            if len(entry) >= 2:
                                minute = entry[1]
                                try:
                                    minute_num = int(minute) if minute != "" else -1
                                    
                                    # Count occurrences
                                    if minute_num not in minute_counts:
                                        minute_counts[minute_num] = 0
                                    minute_counts[minute_num] += 1
                                    
                                    # Check if it's outside our range
                                    if minute_num < 2 or minute_num > 6:
                                        invalid_entries.append({
                                            'match': i,
                                            'company': company_id,
                                            'type': odds_type,
                                            'minute': minute,
                                            'entry': entry
                                        })
                                except:
                                    pass
    
    print(f"Total odds entries: {total_entries}")
    print(f"\nMinute distribution:")
    for minute in sorted(minute_counts.keys()):
        print(f"  Minute {minute}: {minute_counts[minute]} entries")
    
    if invalid_entries:
        print(f"\nWARNING: Found {len(invalid_entries)} entries outside 2-6 range:")
        for entry in invalid_entries[:5]:  # Show first 5
            print(f"  Match {entry['match']}, {entry['type']}, minute: {entry['minute']}")
    else:
        print("\n✓ All entries are within minutes 2-6!")
    
    # Show a sample entry
    print("\nSample filtered entry:")
    for summary in data.get('summaries', []):
        if 'odds' in summary:
            for company_id, odds_data in summary['odds'].items():
                if 'asia' in odds_data and odds_data['asia']:
                    print(f"Company {company_id} asia odds:")
                    for entry in odds_data['asia'][:3]:  # Show first 3
                        print(f"  Minute {entry[1]}: {entry}")
                    return

if __name__ == "__main__":
    verify_filtering()
