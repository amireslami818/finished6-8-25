# 🔍 LOGGING FUNCTION ANALYZER & CONSISTENCY CHECKER

A comprehensive toolkit for analyzing logging functions and identifying inconsistencies in Python pipeline files.

## 📋 QUICK ANALYSIS CHECKPOINTS

### ✅ CHECKPOINT 1: IDENTIFY ALL LOGGING FUNCTIONS
Run this grep command to find all logging-related functions:

```bash
# Find all logging function definitions
grep -n "def.*log\|def.*print\|def.*header\|def.*footer\|def.*setup.*logger" [filename].py

# Find logger setup/initialization 
grep -n "logging\.\|Logger\|FileHandler\|StreamHandler\|getLogger" [filename].py

# Find print statements (potential logging candidates)
grep -n "print(" [filename].py
```

### ✅ CHECKPOINT 2: ANALYZE LOGGING PATTERNS
Check for these common patterns:

```bash
# Pattern 1: Direct print + log (GOOD)
grep -A 3 -B 1 "def.*log_and_print" [filename].py

# Pattern 2: Manual print + logger.info + flush (NEEDS CLEANUP)
grep -A 5 "print.*\n.*logger\.info\|logger\.info.*\n.*print" [filename].py

# Pattern 3: Dual logging calls
grep -A 3 -B 1 "flush()" [filename].py
```

### ✅ CHECKPOINT 3: TIME FUNCTION CONSISTENCY
Check for time function naming inconsistencies:

```bash
# Find all time-related functions
grep -n "def.*time\|def.*ny\|def.*eastern" [filename].py

# Check for timezone function usage
grep -n "get_.*time\|eastern\|ny.*time" [filename].py
```

### ✅ CHECKPOINT 4: LOGGER INDEPENDENCE
Verify each file has independent logging:

```bash
# Check for centralized imports (BAD)
grep -n "from.*centralized\|import.*centralized" [filename].py

# Check for independent logger setup (GOOD)
grep -n "logging\.getLogger\|setup_logger\|FileHandler\|StreamHandler" [filename].py
```

## 🛠️ AUTOMATED ANALYSIS SCRIPT

Save this as `analyze_logging.py` and run it on any file:

```python
#!/usr/bin/env python3
"""
Logging Function Analyzer - Automated analysis of logging patterns
Usage: python analyze_logging.py <filename.py>
"""

import sys
import re
from collections import defaultdict

def analyze_logging_functions(filepath):
    """Analyze logging functions and patterns in a Python file."""
    
    print(f"\n🔍 ANALYZING LOGGING FUNCTIONS IN {filepath}")
    print("=" * 60)
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            lines = content.split('\n')
    except FileNotFoundError:
        print(f"❌ ERROR: File {filepath} not found")
        return
    
    results = {
        'logging_functions': [],
        'logger_setup': [],
        'time_functions': [],
        'print_statements': [],
        'inconsistencies': [],
        'patterns': defaultdict(list)
    }
    
    # 1. Find logging function definitions
    for i, line in enumerate(lines, 1):
        # Logging functions
        if re.search(r'def.*(log|print|header|footer|setup.*logger)', line, re.IGNORECASE):
            results['logging_functions'].append((i, line.strip()))
        
        # Logger setup
        if re.search(r'logging\.|Logger|FileHandler|StreamHandler|getLogger', line):
            results['logger_setup'].append((i, line.strip()))
        
        # Time functions
        if re.search(r'def.*(time|ny|eastern)', line, re.IGNORECASE):
            results['time_functions'].append((i, line.strip()))
        
        # Print statements
        if 'print(' in line:
            results['print_statements'].append((i, line.strip()))
    
    # 2. Pattern Analysis
    analyze_patterns(lines, results)
    
    # 3. Generate Report
    generate_report(results, filepath)
    
    return results

def analyze_patterns(lines, results):
    """Analyze logging patterns for consistency."""
    
    content = '\n'.join(lines)
    
    # Pattern 1: log_and_print pattern (GOOD)
    if 'def log_and_print' in content:
        results['patterns']['log_and_print'].append("✅ Found log_and_print pattern")
    
    # Pattern 2: Manual flush pattern (NEEDS CLEANUP)
    if re.search(r'handler\.flush\(\)|flush\(\)', content):
        results['patterns']['manual_flush'].append("❌ Manual flush operations found")
    
    # Pattern 3: Mixed logging patterns
    if re.search(r'print.*logger\.info|logger\.info.*print', content, re.DOTALL):
        results['patterns']['mixed_logging'].append("❌ Mixed print/logger patterns found")
    
    # Pattern 4: Centralized imports (BAD)
    if re.search(r'from.*centralized|import.*centralized', content):
        results['patterns']['centralized'].append("❌ Centralized logging imports found")
    
    # Pattern 5: Independent logging (GOOD)
    if re.search(r'logging\.getLogger|setup_logger', content):
        results['patterns']['independent'].append("✅ Independent logging setup found")

def generate_report(results, filepath):
    """Generate comprehensive analysis report."""
    
    print(f"\n📋 LOGGING FUNCTIONS ANALYSIS REPORT")
    print("-" * 50)
    
    # Logging Functions
    if results['logging_functions']:
        print(f"\n✅ LOGGING FUNCTIONS IDENTIFIED:")
        print(f"{'Function':<40} {'Line':<6} {'Definition'}")
        print("-" * 80)
        for line_num, line_content in results['logging_functions']:
            func_name = extract_function_name(line_content)
            print(f"{func_name:<40} {line_num:<6} {line_content}")
    
    # Logger Setup
    if results['logger_setup']:
        print(f"\n🔧 LOGGER SETUP LINES:")
        for line_num, line_content in results['logger_setup'][:5]:  # Show first 5
            print(f"Line {line_num}: {line_content}")
    
    # Time Functions
    if results['time_functions']:
        print(f"\n⏰ TIME FUNCTIONS:")
        for line_num, line_content in results['time_functions']:
            func_name = extract_function_name(line_content)
            print(f"Line {line_num}: {func_name}")
    
    # Pattern Analysis
    print(f"\n⚠️ PATTERN ANALYSIS:")
    for pattern_type, issues in results['patterns'].items():
        for issue in issues:
            print(f"  {issue}")
    
    # Recommendations
    generate_recommendations(results)

def extract_function_name(line):
    """Extract function name from function definition line."""
    match = re.search(r'def\s+(\w+)', line)
    return match.group(1) if match else "Unknown"

def generate_recommendations(results):
    """Generate cleanup recommendations."""
    
    print(f"\n🎯 CLEANUP RECOMMENDATIONS:")
    print("-" * 40)
    
    recommendations = []
    
    # Check for mixed patterns
    if results['patterns']['mixed_logging']:
        recommendations.append("1. Standardize to log_and_print() pattern for all header/footer functions")
    
    # Check for manual flushing
    if results['patterns']['manual_flush']:
        recommendations.append("2. Remove manual flush() calls if log_and_print() handles flushing")
    
    # Check for time function consistency
    time_funcs = [extract_function_name(line) for _, line in results['time_functions']]
    if len(set(time_funcs)) > 1:
        recommendations.append("3. Standardize time function naming (e.g., get_ny_time_str)")
    
    # Check for centralized imports
    if results['patterns']['centralized']:
        recommendations.append("4. Remove centralized logging imports - use independent logging")
    
    if not recommendations:
        recommendations.append("✅ No major issues found - logging patterns look consistent!")
    
    for rec in recommendations:
        print(f"  {rec}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze_logging.py <filename.py>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    analyze_logging_functions(filepath)
```

## 🚀 QUICK USAGE EXAMPLES

### Analyze step7.py:
```bash
python analyze_logging.py step7.py
```

### Analyze all pipeline files:
```bash
for file in step*.py; do
    echo "Analyzing $file..."
    python analyze_logging.py "$file"
    echo ""
done
```

### Quick Manual Check:
```bash
# Check for logging functions
grep -n "def.*log\|def.*print\|def.*header\|def.*footer" step7.py

# Check for inconsistent patterns
grep -A 3 -B 1 "flush()" step7.py
```

## 📊 EXPECTED OUTPUT FORMAT

The analyzer will provide:

```
🔍 ANALYZING LOGGING FUNCTIONS IN step7.py
============================================================

📋 LOGGING FUNCTIONS ANALYSIS REPORT
--------------------------------------------------

✅ LOGGING FUNCTIONS IDENTIFIED:
Function                                 Line   Definition
--------------------------------------------------------------------------------
setup_logger                             53     def setup_logger() -> logging.Logger:
log_and_print                           71     def log_and_print(message: str):
write_main_header                       187    def write_main_header():
write_main_footer                       206    def write_main_footer():
write_competition_group_header          239    def write_competition_group_header():

⚠️ PATTERN ANALYSIS:
  ✅ Found log_and_print pattern
  ❌ Manual flush operations found
  ❌ Mixed print/logger patterns found
  ✅ Independent logging setup found

🎯 CLEANUP RECOMMENDATIONS:
----------------------------------------
  1. Standardize to log_and_print() pattern for all header/footer functions
  2. Remove manual flush() calls if log_and_print() handles flushing
  3. Standardize time function naming (e.g., get_ny_time_str)
```

## 🔧 CONSISTENCY STANDARDS TO ENFORCE

### ✅ GOOD PATTERNS:
- **Single log_and_print() function** for all print+log operations
- **Independent logging setup** per file (no centralized imports)
- **Consistent time function naming** (e.g., `get_ny_time_str()`)
- **Single completion_summary** structure in JSON outputs
- **Log summaries printed AFTER JSON dumps** (not in JSON)

### ❌ PATTERNS TO AVOID:
- Mixed print() + logger.info() calls
- Manual handler.flush() operations
- Centralized logging imports
- Multiple time function names for same timezone
- Legacy/duplicate summary keys in JSON
- Log summaries included in JSON data

## 📝 AUDIT CHECKLIST

Before marking a file as "logging consistent":

- [ ] All logging uses consistent pattern (preferably log_and_print)
- [ ] No manual flush() operations (handled by log_and_print)
- [ ] No centralized logging imports
- [ ] Time functions use consistent naming
- [ ] Independent logger setup
- [ ] Single completion_summary in JSON output
- [ ] Log summaries printed after JSON (not in JSON)
- [ ] Documentation updated to reflect current logging logic

---

**Save this file and use it as your go-to tool for maintaining logging consistency across all pipeline files!** 🎯
