#!/usr/bin/env python3
"""
Filter odds data to only keep entries with minute fields between "2" and "6"
"""

import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def filter_odds_by_minutes(odds_data, min_minute="2", max_minute="6"):
    """
    Filter odds arrays to only keep entries where the minute field (second field) 
    is between min_minute and max_minute (inclusive).
    
    Args:
        odds_data: The odds data structure (dict with asia, bs, eu, cr arrays)
        min_minute: Minimum minute value to keep (as string)
        max_minute: Maximum minute value to keep (as string)
    
    Returns:
        Filtered odds data
    """
    filtered_odds = {}
    
    for odds_type in ['asia', 'bs', 'eu', 'cr']:
        if odds_type in odds_data:
            filtered_arrays = []
            
            for array in odds_data[odds_type]:
                # Check if the array has at least 2 elements and the second element is the minute field
                if len(array) >= 2:
                    minute_field = str(array[1])  # Convert to string for comparison
                    
                    # Only keep if minute field is between min and max (inclusive)
                    if minute_field >= min_minute and minute_field <= max_minute:
                        filtered_arrays.append(array)
            
            filtered_odds[odds_type] = filtered_arrays
    
    return filtered_odds

def main():
    """Main function to filter step2.json"""
    try:
        # Load step2.json
        logger.info("Loading step2.json...")
        with open('/root/6-4-2025/step2.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Count initial odds entries
        initial_count = 0
        for summary in data.get('summaries', []):
            if 'odds' in summary:
                for company_id, odds_data in summary['odds'].items():
                    for odds_type in ['asia', 'bs', 'eu', 'cr']:
                        if odds_type in odds_data:
                            initial_count += len(odds_data[odds_type])
        
        logger.info(f"Initial odds entries: {initial_count}")
        
        # Filter odds for each match summary
        filtered_count = 0
        for summary in data.get('summaries', []):
            if 'odds' in summary:
                for company_id, odds_data in summary['odds'].items():
                    # Apply the filter
                    filtered_odds = filter_odds_by_minutes(odds_data)
                    summary['odds'][company_id] = filtered_odds
                    
                    # Count filtered entries
                    for odds_type in ['asia', 'bs', 'eu', 'cr']:
                        if odds_type in filtered_odds:
                            filtered_count += len(filtered_odds[odds_type])
        
        logger.info(f"Filtered odds entries: {filtered_count}")
        logger.info(f"Removed {initial_count - filtered_count} entries")
        
        # Save filtered data back to step2.json
        logger.info("Saving filtered data to step2.json...")
        with open('/root/6-4-2025/step2.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info("Filtering complete!")
        
    except FileNotFoundError:
        logger.error("step2.json not found")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    main()
