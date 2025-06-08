# Centralized Logging Architecture - Quick Reference

## 🏗️ **LOGGING SYSTEM VISUAL ARCHITECTURE**

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                CENTRALIZED LOGGING HUB                  │
                    │            centralized_logger/log_config.py            │
                    └─────────────────────┬───────────────────────────────────┘
                                          │
                    ┌─────────────────────┼───────────────────────────────────┐
                    │         GLOBAL RULES & TRAFFIC DIRECTION              │
                    │                                                       │
                    │  • Eastern Time (EST/EDT) formatting                 │
                    │  • mm/dd/yyyy HH:MM:SS AM/PM format                   │
                    │  • Universal logger configuration                    │
                    │  • Route post-logging to step modules                │
                    └─────────────────────┬───────────────────────────────────┘
                                          │
                                          ▼
        ┌─────────────────────────────────────────────────────────────────────┐
        │                        ROUTING TABLE                                │
        ├─────────────────────────────────────────────────────────────────────┤
        │                                                                     │
        │  step1, step2  ───────────────▶  step1-2_logging.py                │
        │  step3, step4  ───────────────▶  step3-4_logging.py  (future)      │
        │  stepX         ───────────────▶  stepX_logging.py    (extensible)  │
        │                                                                     │
        └─────────────────────────────────────────────────────────────────────┘

┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│     STEP 1       │    │     STEP 2       │    │   FUTURE STEPS   │
│    (step1.py)    │    │    (step2.py)    │    │   (stepX.py)     │
├──────────────────┤    ├──────────────────┤    ├──────────────────┤
│                  │    │                  │    │                  │
│ PHASE 1:         │    │ PHASE 1:         │    │ PHASE 1:         │
│ • initialize_    │    │ • initialize_    │    │ • initialize_    │
│   global_logging_│    │   global_logging_│    │   global_logging_│
│   for_step()     │    │   for_step()     │    │   for_step()     │
│ • apply_global_  │    │ • apply_global_  │    │ • apply_global_  │
│   format_to_     │    │   format_to_     │    │   format_to_     │
│   logger()       │    │   logger()       │    │   logger()       │
│                  │    │                  │    │                  │
│ PHASE 2:         │    │ PHASE 2:         │    │ PHASE 2:         │
│ • Business logic │    │ • Business logic │    │ • Business logic │
│ • Local logging  │    │ • Local logging  │    │ • Local logging  │
│                  │    │                  │    │                  │
│ PHASE 3:         │    │ PHASE 3:         │    │ PHASE 3:         │
│ • central_       │    │ • central_       │    │ • central_       │
│   logging_hub()  │    │   logging_hub()  │    │   logging_hub()  │
│                  │    │                  │    │                  │
└──────────┬───────┘    └──────────┬───────┘    └──────────┬───────┘
           │                       │                       │
           └───────────────────────┼───────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────────┐
                    │      POST-LOGGING ACTION MODULES       │
                    ├─────────────────────────────────────────┤
                    │                                         │
                    │  step1-2_logging.py                    │
                    │  • Handles step1 & step2 final logging │
                    │  • Maintains global formatting         │
                    │  • Step-specific logic                 │
                    │                                         │
                    │  stepX_logging.py (future modules)     │
                    │  • Pattern for extensibility           │
                    │  • Modular post-logging actions        │
                    │                                         │
                    └─────────────────────────────────────────┘
```

## 📋 **IMPLEMENTATION PATTERN FOR NEW STEPS**

### **Template for New Step File**

```python
#!/usr/bin/env python3
"""
STEP X - [PURPOSE DESCRIPTION]
=============================
"""

import logging
# ... other imports ...

# Import centralized logging
try:
    from centralized_logger.log_config import (
        initialize_global_logging_for_step,
        apply_global_format_to_logger,
        central_logging_hub
    )
    CENTRALIZED_LOGGING_AVAILABLE = True
except ImportError:
    # Fallback if centralized logger not available
    def initialize_global_logging_for_step(*args, **kwargs):
        return {}
    def apply_global_format_to_logger(logger, *args, **kwargs):
        return logger
    def central_logging_hub(*args, **kwargs):
        pass
    CENTRALIZED_LOGGING_AVAILABLE = False

def main():
    # PHASE 1: PRE-LOGGING SETUP
    global_config = initialize_global_logging_for_step("stepX")
    logger = logging.getLogger(__name__)
    apply_global_format_to_logger(logger)
    
    try:
        # PHASE 2: BUSINESS LOGIC WITH LOCAL LOGGING
        logger.info("Starting Step X processing...")
        
        # Your business logic here
        result = do_step_work()
        
        logger.info(f"Step X completed successfully: {result}")
        
        # PHASE 3: POST-LOGGING VIA CENTRAL HUB
        context_data = {
            "step": "stepX",
            "result": result,
            "timestamp": datetime.now().isoformat(),
            # Add any context needed for centralized logging
        }
        
        central_logging_hub("stepX", "post_logging", context_data)
        
    except Exception as e:
        logger.error(f"Step X failed: {e}")
        central_logging_hub("stepX", "error_logging", {"error": str(e)})
        raise

if __name__ == "__main__":
    main()
```

### **Template for New Logging Module**

Create `centralized_logger/stepX_logging.py`:

```python
#!/usr/bin/env python3
"""
Step X Centralized Logging Module
=================================

Handles post-logging actions for stepX.py through the central logging hub.
Called via central_logging_hub() routing from log_config.py.
"""

import logging
from datetime import datetime
import pytz

# Eastern Time zone for consistent logging
TZ = pytz.timezone("America/New_York")

def handle_stepX_logging(action: str, context_data: dict) -> bool:
    """
    Handle centralized logging actions for Step X.
    
    Args:
        action: The logging action type ("post_logging", "error_logging", etc.)
        context_data: Dictionary containing context information
        
    Returns:
        bool: True if logging was handled successfully, False otherwise
    """
    logger = logging.getLogger("stepX_centralized")
    
    try:
        if action == "post_logging":
            # Handle successful completion logging
            timestamp = datetime.now(TZ).strftime("%m/%d/%Y %I:%M:%S %p %Z")
            logger.info(f"[CENTRALIZED] Step X completed at {timestamp}")
            logger.info(f"[CENTRALIZED] Context: {context_data}")
            
        elif action == "error_logging":
            # Handle error logging
            timestamp = datetime.now(TZ).strftime("%m/%d/%Y %I:%M:%S %p %Z")
            logger.error(f"[CENTRALIZED] Step X error at {timestamp}")
            logger.error(f"[CENTRALIZED] Error details: {context_data}")
            
        else:
            logger.warning(f"[CENTRALIZED] Unknown action for Step X: {action}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"[CENTRALIZED] Failed to handle Step X logging: {e}")
        return False

# Make the function available for import
__all__ = ['handle_stepX_logging']
```

### **Update log_config.py Routing**

Add to the `central_logging_hub()` function in `log_config.py`:

```python
def central_logging_hub(step_name: str, action: str, context_data: dict = None) -> bool:
    """Central hub for routing post-logging actions to appropriate step modules."""
    
    # ... existing code ...
    
    elif step_name in ["stepX"]:
        try:
            from centralized_logger.stepX_logging import handle_stepX_logging
            return handle_stepX_logging(action, context_data or {})
        except ImportError as e:
            logger.error(f"Failed to import stepX logging module: {e}")
            return False
```

## 🎯 **QUICK ONBOARDING CHECKLIST**

For adding a new step to the centralized logging system:

- [ ] Create `stepX.py` using the template above
- [ ] Create `centralized_logger/stepX_logging.py` using the template above  
- [ ] Update routing in `centralized_logger/log_config.py`
- [ ] Test the 3-phase logging flow
- [ ] Verify Eastern Time formatting is applied
- [ ] Update this documentation

## 🔧 **DEBUGGING THE LOGGING SYSTEM**

### **Common Issues and Solutions**

1. **Import Error**: `ImportError: No module named 'centralized_logger'`
   ```python
   # Solution: Ensure fallback imports are in place
   try:
       from centralized_logger.log_config import ...
   except ImportError:
       # Fallback functions provided
   ```

2. **Routing Not Working**: Step not calling centralized logging
   ```python
   # Solution: Verify routing in log_config.py central_logging_hub()
   # Check step_name matches the routing logic
   ```

3. **Time Format Issues**: Logs not showing Eastern Time
   ```python
   # Solution: Ensure apply_global_format_to_logger() is called
   # Check that TZ = pytz.timezone("America/New_York") is used
   ```

### **Testing Commands**

```bash
# Test individual step logging
python3 -c "
import logging
from centralized_logger.log_config import initialize_global_logging_for_step, apply_global_format_to_logger
initialize_global_logging_for_step('test')
logger = logging.getLogger('test')
apply_global_format_to_logger(logger)
logger.info('Test message')
"

# Check log format
tail -f step1.log | grep -E "\d{2}/\d{2}/\d{4} \d{1,2}:\d{2}:\d{2} [AP]M"

# Verify routing
python3 -c "
from centralized_logger.log_config import central_logging_hub
result = central_logging_hub('step1', 'post_logging', {'test': 'data'})
print(f'Routing result: {result}')
"
```

This quick reference provides the essential patterns and templates for extending the centralized logging system to new steps while maintaining consistency and global formatting rules.
