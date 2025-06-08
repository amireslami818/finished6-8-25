# Complete Pipeline Data Flow and Logging Architecture Map

## Overview

This document provides a comprehensive visual map of the entire data pipeline, showing how data flows from start to finish, how all components interact, and how the centralized logging system orchestrates the process.

---

## 🏗️ **PIPELINE ARCHITECTURE DIAGRAM**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           PIPELINE ORCHESTRATION                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐    ┌─────────────────┐    ┌──────────────────────────────────┐ │
│  │   start.sh   │───▶│   Virtual ENV   │───▶│         step1.py                │ │
│  │              │    │   Dependencies  │    │      (Main Pipeline)           │ │
│  │ • Creates    │    │   Installation  │    │    --continuous mode           │ │
│  │   venv       │    │ • requests      │    │     60-second cycles           │ │
│  │ • Installs   │    │ • python-dotenv │    │                                │ │
│  │   deps       │    │ • pytz          │    │                                │ │
│  │ • Manages    │    │ • aiohttp       │    │                                │ │
│  │   PID        │    └─────────────────┘    └──────────────────────────────────┘ │
│  └──────────────┘                                                               │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                             DATA PROCESSING FLOW                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐    ┌─────────────────┐    ┌──────────────────────────────────┐ │
│  │   STEP 1     │───▶│   step1.json    │───▶│            STEP 2                │ │
│  │              │    │                 │    │                                  │ │
│  │ • API calls  │    │ • Live matches  │    │ • import step2                   │ │
│  │ • Data       │    │ • Match details │    │ • step2.run_step2()              │ │
│  │   fetching   │    │ • Match odds    │    │ • Direct in-memory call          │ │
│  │ • JSON save  │    │ • Team info     │    │ • Flattening & summarization     │ │
│  │ • Triggers   │    │ • Competition   │    │                                  │ │
│  │   Step 2     │    │   info          │    │                                  │ │
│  └──────────────┘    └─────────────────┘    └──────────────────────────────────┘ │
│                                                                                 │
│                      ┌─────────────────┐    ┌──────────────────────────────────┐ │
│                      │   step2.json    │───▶│            STEP 7                │ │
│                      │                 │    │                                  │ │
│                      │ • Flattened     │    │ • import step7                   │ │
│                      │   summaries     │    │ • step7.filter_in_play()         │ │
│                      │ • Historical    │    │ • Status filtering (2-7)         │ │
│                      │   tracking      │    │ • Pretty-print formatting        │ │
│                      │ • Processing    │    │                                  │ │
│                      │   metadata      │    │                                  │ │
│                      └─────────────────┘    └──────────────────────────────────┘ │
│                                                                                 │
│                                             ┌──────────────────────────────────┐ │
│                                             │      step7_matches.log           │ │
│                                             │                                  │ │
│                                             │ • Filtered match results         │ │
│                                             │ • Formatted output               │ │
│                                             │ • Human-readable logs            │ │
│                                             └──────────────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                          CENTRALIZED LOGGING SYSTEM                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                    centralized_logger/log_config.py                     │   │
│  │                           (GLOBAL HUB)                                  │   │
│  │                                                                          │   │
│  │  ┌─────────────────────┐  ┌────────────────────┐  ┌─────────────────────┐│   │
│  │  │   PRE-LOGGING       │  │   GLOBAL RULES     │  │   POST-LOGGING      ││   │
│  │  │                     │  │                    │  │     ROUTING         ││   │
│  │  │ • initialize_       │  │ • Eastern Time     │  │                     ││   │
│  │  │   global_logging_   │  │ • mm/dd/yyyy       │  │ • central_logging_  ││   │
│  │  │   for_step()        │  │ • AM/PM format     │  │   hub()             ││   │
│  │  │ • apply_global_     │  │ • EST/EDT zones    │  │ • Routes to step    ││   │
│  │  │   format_to_        │  │ • Consistent       │  │   modules           ││   │
│  │  │   logger()          │  │   formatting       │  │                     ││   │
│  │  └─────────────────────┘  └────────────────────┘  └─────────────────────┘│   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                centralized_logger/step1-2_logging.py                    │   │
│  │                      (POST-LOGGING ACTIONS)                             │   │
│  │                                                                          │   │
│  │ • Handles centralized logging for step1.py and step2.py                 │   │
│  │ • Called via central_logging_hub() routing                              │   │
│  │ • Contains step-specific post-logging logic                             │   │
│  │ • Maintains global formatting rules                                     │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 **STEP-BY-STEP EXECUTION FLOW**

### **Phase 1: Pipeline Initialization**

1. **User runs**: `./start.sh start`
2. **start.sh**:
   - Creates virtual environment (if needed)
   - Installs dependencies from `requirements.txt`
   - Launches `step1.py --continuous` in background
   - Creates `step1.pid` for process management
   - Returns control to user

### **Phase 2: Continuous Data Processing Loop (60-second cycles)**

#### **Step 1 Execution** (`step1.py`)
```
┌─────────────────────────────────────────────────────────────────┐
│                       STEP 1 PROCESS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. initialize_global_logging_for_step("step1")                 │
│ 2. apply_global_format_to_logger(logger)                       │
│ 3. API calls to TheSports API:                                 │
│    • /matches/live                                             │
│    • /matches/{id}/details                                     │
│    • /matches/{id}/odds                                        │
│    • /teams/{id}/info                                          │
│    • /competitions/{id}/info                                   │
│ 4. Data aggregation and JSON structure creation                │
│ 5. Save to step1.json                                          │
│ 6. central_logging_hub("step1", "post_logging", ...)           │
│ 7. TRIGGER STEP 2: step2.run_step2()                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### **Step 2 Execution** (`step2.py` via import)
```
┌─────────────────────────────────────────────────────────────────┐
│                       STEP 2 PROCESS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. initialize_global_logging_for_step("step2")                 │
│ 2. apply_global_format_to_logger(logger)                       │
│ 3. Read step1.json data                                        │
│ 4. Extract and flatten match summaries                         │
│ 5. Merge with historical data                                  │
│ 6. Save to step2.json with metadata                            │
│ 7. central_logging_hub("step2", "post_logging", ...)           │
│ 8. TRIGGER STEP 7: step7.filter_in_play()                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### **Step 7 Execution** (`step7.py` via import)
```
┌─────────────────────────────────────────────────────────────────┐
│                       STEP 7 PROCESS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. Reads step2.json summaries                                  │
│ 2. Filters matches with status in {2, 3, 4, 5, 6, 7}           │
│ 3. Pretty-prints results with formatting                       │
│ 4. Saves to step7_matches.log                                  │
│ 5. Updates pipeline timing in both JSON files                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### **Phase 3: Testing and Monitoring**

#### **Integration Testing** (`test_pipeline_flow.py`)
```
┌─────────────────────────────────────────────────────────────────┐
│                    INTEGRATION TEST FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. ./start.sh start (launch pipeline)                          │
│ 2. Monitor step1.json creation (60s timeout)                   │
│ 3. Monitor step2.json creation (60s timeout)                   │
│ 4. Monitor step7_matches.log creation (60s timeout)            │
│ 5. Verify continuous operation (120s for second cycle)         │
│ 6. ./start.sh stop (graceful shutdown)                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 **FILE INTERACTION MATRIX**

| File | Purpose | Reads From | Writes To | Triggers | Triggered By |
|------|---------|------------|-----------|----------|--------------|
| `start.sh` | Pipeline orchestration | ENV, CLI args | `start.log`, `step1.pid` | `step1.py` | User command |
| `step1.py` | API data collection | API endpoints, ENV | `step1.json`, logs | `step2.py` | `start.sh` |
| `step2.py` | Data flattening | `step1.json` | `step2.json`, logs | `step7.py` | `step1.py` |
| `step7.py` | Match filtering | `step2.json` | `step7_matches.log` | None | `step2.py` |
| `test_pipeline_flow.py` | Integration testing | All output files | Test logs | `start.sh` | Manual execution |
| `log_config.py` | Global logging hub | None | Logs via routing | Step loggers | All steps |
| `step1-2_logging.py` | Step-specific logging | Log data | Step logs | None | `log_config.py` |

---

## 🌐 **LOGGING ARCHITECTURE FLOW**

### **3-Phase Logging Pattern**

Each step follows this standardized logging pattern:

```
┌─────────────────────────────────────────────────────────────────┐
│                      PHASE 1: PRE-LOGGING                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Step File (e.g., step1.py):                                    │
│ 1. initialize_global_logging_for_step("step1")                 │
│ 2. apply_global_format_to_logger(local_logger)                 │
│                                                                 │
│ Result: Logger configured with global Eastern Time formatting   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      PHASE 2: LOCAL LOGGING                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Step File:                                                      │
│ • Performs its own business logic                               │
│ • Uses local logger with global formatting                     │
│ • Creates step-specific log entries                            │
│ • Maintains step autonomy                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     PHASE 3: POST-LOGGING                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Step File:                                                      │
│ central_logging_hub("step1", "post_logging", context_data)     │
│                                                                 │
│ log_config.py routes to:                                       │
│ step1-2_logging.py for centralized final logging               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 **EXTENSIBILITY GUIDE**

### **Adding New Steps**

#### **Option A: Independent New Step**

1. Create `stepX.py` with:
   ```python
   from centralized_logger.log_config import (
       initialize_global_logging_for_step,
       apply_global_format_to_logger,
       central_logging_hub
   )
   
   # Phase 1: Pre-logging
   initialize_global_logging_for_step("stepX")
   logger = logging.getLogger(__name__)
   apply_global_format_to_logger(logger)
   
   # Phase 2: Your business logic with local logging
   # ... your code ...
   
   # Phase 3: Post-logging
   central_logging_hub("stepX", "post_logging", context_data)
   ```

2. Create `centralized_logger/stepX_logging.py`
3. Update `log_config.py` routing in `central_logging_hub()`

#### **Option B: Integrate into Existing Pipeline**

1. Add call to existing step (e.g., in `step2.py`):
   ```python
   import stepX
   stepX.run_stepX()
   ```

2. Follow same logging pattern as Option A

### **Alternative Architectures**

The system supports multiple pipeline configurations:

- **Linear**: step1 → step2 → step7 (current)
- **Branched**: step1 → [step2, stepX] → step7
- **Extended**: step1 → step2 → step7 → stepX → stepY

---

## 📊 **MONITORING AND OBSERVABILITY**

### **Key Log Files**

| File | Content | Frequency | Monitoring |
|------|---------|-----------|------------|
| `step1.log` | API calls, data processing | Every 60s | Real-time |
| `step1.json` | Structured API data | Every 60s | File watcher |
| `step2.json` | Flattened summaries | Every 60s | File watcher |
| `step7_matches.log` | Filtered results | Every 60s | Tail monitoring |
| `start.log` | Pipeline orchestration | On events | Error tracking |

### **Health Monitoring Commands**

```bash
# Check if pipeline is running
./start.sh status

# View real-time logs
tail -f step1.log

# Monitor data flow
watch -n 5 'ls -la *.json'

# Run integration test
./test_pipeline_flow.py

# Check log file sizes
du -h *.log *.json
```

---

## 🔧 **TROUBLESHOOTING GUIDE**

### **Common Issues**

1. **Pipeline Won't Start**
   - Check `start.log` for environment issues
   - Verify API_KEY in `.env` file
   - Ensure network connectivity

2. **Missing JSON Files**
   - Check step1.log for API errors
   - Verify file permissions
   - Monitor disk space

3. **Logging Issues**
   - Verify centralized_logger module import
   - Check log file rotation settings
   - Monitor log directory permissions

4. **Step Integration Problems**
   - Review import statements
   - Check function call sequences
   - Verify data format expectations

### **Debug Commands**

```bash
# Test individual steps
python3 step1.py
python3 step2.py

# Check dependencies
pip list | grep -E "requests|pytz|aiohttp"

# Monitor process
ps aux | grep step1

# Check logs for errors
grep -i error *.log
```

---

## 📈 **PERFORMANCE METRICS**

### **Expected Timing**

- **Step 1 (API calls)**: 3-8 seconds
- **Step 2 (processing)**: 1-3 seconds  
- **Step 7 (filtering)**: <1 second
- **Total cycle time**: 5-15 seconds
- **Cycle interval**: 60 seconds

### **Resource Usage**

- **Memory**: ~50-100MB during processing
- **CPU**: Low, burst during API calls
- **Network**: 1-5MB per cycle (API data)
- **Disk**: ~1-10MB per cycle (JSON files)

---

This comprehensive map documents the complete pipeline architecture, data flow, logging system, and extensibility patterns for current and future development.
