#!/usr/bin/env python3
import sys
print(f"Testing analyzer with {sys.argv[1] if len(sys.argv) > 1 else 'no args'}")

if len(sys.argv) > 1:
    filepath = sys.argv[1]
    print(f"Reading file: {filepath}")
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        print(f"File has {len(lines)} lines")
        
        # Test regex
        import re
        logging_funcs = []
        for i, line in enumerate(lines, 1):
            if re.search(r'def.*(log|print|header|footer|setup.*logger)', line, re.IGNORECASE):
                logging_funcs.append((i, line.strip()))
        
        print(f"Found {len(logging_funcs)} logging functions:")
        for line_num, line_content in logging_funcs:
            print(f"  Line {line_num}: {line_content}")
            
    except Exception as e:
        print(f"Error: {e}")
