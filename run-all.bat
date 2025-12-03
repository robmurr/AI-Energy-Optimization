@echo off
REM ============================================================================
REM run-all.bat: Automated profiling workflow for Windows
REM ============================================================================
REM 
REM PURPOSE:
REM Automates the complete energy profiling workflow:
REM 1. Build Java application with Maven
REM 2. Start Intel Power Gadget logging
REM 3. Run DL4J demo with JFR enabled
REM 4. (Optional) Run VTune Profiler
REM 5. Generate energy report
REM 
REM REQUIREMENTS:
REM - Maven 3.9+ in PATH or at C:\Program Files\Maven\
REM - Java JDK 17+ in PATH
REM - Intel Power Gadget at C:\Program Files\Intel\Power Gadget 3.7\
REM - (Optional) VTune at C:\Program Files (x86)\Intel\oneAPI\vtune\
REM 
REM USAGE:
REM Double-click this file or run from command prompt:
REM   run-all.bat
REM 
REM OUTPUT:
REM All logs written to: energy_results\run.log
REM Window pauses at end to review results.
REM ============================================================================

setlocal enabledelayedexpansion

REM ============================================================================
REM CONFIGURATION
REM ============================================================================

REM Project directory (auto-detect from script location)
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

REM Output directory for all results
set "OUTPUT_DIR=energy_results"

REM Create output directory if it doesn't exist
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

REM Combined log file (all output goes here)
set "LOG_FILE=%OUTPUT_DIR%\run.log"

REM Tool paths (adjust if installed elsewhere)
set "MAVEN_BIN=C:\Program Files\Maven\apache-maven-3.9.11\bin\mvn.cmd"
set "POWER_GADGET=C:\Program Files\Intel\Power Gadget 3.7\PowerLog3.0.exe"
set "VTUNE_BIN=C:\Program Files (x86)\Intel\oneAPI\vtune\latest\bin64\vtune.exe"

REM Duration for Power Gadget logging (seconds)
set "POWER_DURATION=200"

REM JVM memory settings
set "JVM_HEAP_MIN=2g"
set "JVM_HEAP_MAX=3g"

REM ============================================================================
REM STARTUP BANNER
REM ============================================================================

echo ========================================================================
echo DL4J + VTune End-to-End Energy Profiling Runner
echo ========================================================================
echo Project: %PROJECT_DIR%
echo Output : %OUTPUT_DIR%
echo [LOG] Writing combined output to %LOG_FILE%
echo.

REM Clear previous log
echo [BOOT] Script started at %date% %time% > "%LOG_FILE%"

REM ============================================================================
REM STEP 1: BUILD PROJECT WITH MAVEN
REM ============================================================================

echo [1/5] Building shaded JAR with Maven...
echo [1/5] Building shaded JAR with Maven... >> "%LOG_FILE%" 2>&1

if not exist "%MAVEN_BIN%" (
    echo [ERROR] Maven not found at: %MAVEN_BIN%
    echo [ERROR] Please install Maven or update MAVEN_BIN path in this script.
    pause
    exit /b 1
)

REM Run Maven build (clean + package)
call "%MAVEN_BIN%" clean package -DskipTests >> "%LOG_FILE%" 2>&1

if errorlevel 1 (
    echo [ERROR] Maven build failed. See output above.
    echo [ERROR] Maven build failed. Check %LOG_FILE% for details. >> "%LOG_FILE%"
    pause
    exit /b 1
)

echo   [OK] JAR built: target\dl4j-profiler-demo.jar
echo   [OK] JAR built successfully >> "%LOG_FILE%"

REM ============================================================================
REM STEP 2: START INTEL POWER GADGET (OPTIONAL)
REM ============================================================================

echo.
echo [2/5] Starting Intel Power Gadget...
echo [2/5] Starting Intel Power Gadget... >> "%LOG_FILE%" 2>&1

if not exist "%POWER_GADGET%" (
    echo [WARN] Power Gadget not found at: %POWER_GADGET%
    echo [WARN] Skipping power measurement. Install from: https://www.intel.com/content/www/us/en/developer/articles/tool/power-gadget.html
    echo [WARN] Power Gadget not found, skipping >> "%LOG_FILE%"
) else (
    REM Start Power Gadget in background
    start /B "" "%POWER_GADGET%" -file "%OUTPUT_DIR%\power.csv" -duration %POWER_DURATION% -resolution 100
    echo   [OK] Power logging started (duration: %POWER_DURATION%s, output: %OUTPUT_DIR%\power.csv^)
    echo   [OK] Power logging started >> "%LOG_FILE%"
    
    REM Wait 2 seconds for Power Gadget to initialize
    timeout /t 2 /nobreak >nul
)

REM ============================================================================
REM STEP 3: RUN DL4J DEMO WITH JFR
REM ============================================================================

echo.
echo [3/5] Running DL4J demo with JFR enabled...
echo [3/5] Running DL4J demo with JFR enabled... >> "%LOG_FILE%" 2>&1

REM JFR configuration
set "JFR_FILE=%OUTPUT_DIR%\run.jfr"
set "JVM_OPTS=-XX:StartFlightRecording=duration=200s,filename=%JFR_FILE%"
set "JVM_OPTS=%JVM_OPTS% -XX:FlightRecorderOptions=stackdepth=128"
set "JVM_OPTS=%JVM_OPTS% -Xms%JVM_HEAP_MIN% -Xmx%JVM_HEAP_MAX%"

REM Run Java application
java %JVM_OPTS% -jar target\dl4j-profiler-demo.jar >> "%LOG_FILE%" 2>&1

if errorlevel 1 (
    echo [ERROR] Java application failed. See log for stack trace.
    echo [ERROR] Java application failed >> "%LOG_FILE%"
    pause
    exit /b 1
)

echo   [OK] Training complete. JFR data: %JFR_FILE%
echo   [OK] Training complete >> "%LOG_FILE%"

REM ============================================================================
REM STEP 4: RUN VTUNE PROFILER (OPTIONAL)
REM ============================================================================

echo.
echo [4/5] Running Intel VTune Profiler (optional)...
echo [4/5] Running Intel VTune Profiler... >> "%LOG_FILE%" 2>&1

if not exist "%VTUNE_BIN%" (
    echo [WARN] VTune not found at: %VTUNE_BIN%
    echo [WARN] Skipping VTune analysis. Install from: https://www.intel.com/content/www/us/en/developer/tools/oneapi/vtune-profiler.html
    echo [WARN] VTune not found, skipping >> "%LOG_FILE%"
) else (
    set "VTUNE_RESULT_DIR=%OUTPUT_DIR%\vtune_hotspots"
    
    REM Run VTune hotspots analysis
    "%VTUNE_BIN%" -collect hotspots -knob analyze-java=true -result-dir "%VTUNE_RESULT_DIR%" -- java -Xms%JVM_HEAP_MIN% -Xmx%JVM_HEAP_MAX% -jar target\dl4j-profiler-demo.jar >> "%LOG_FILE%" 2>&1
    
    if errorlevel 1 (
        echo [WARN] VTune analysis failed (may need administrator privileges^)
        echo [WARN] VTune analysis failed >> "%LOG_FILE%"
    ) else (
        echo   [OK] VTune results: %VTUNE_RESULT_DIR%
        echo   [OK] VTune analysis complete >> "%LOG_FILE%"
        
        REM Generate text report
        "%VTUNE_BIN%" -report hotspots -result-dir "%VTUNE_RESULT_DIR%" -format text -report-output "%OUTPUT_DIR%\vtune_hotspots.txt" >> "%LOG_FILE%" 2>&1
    )
)

REM ============================================================================
REM STEP 5: GENERATE ENERGY REPORT
REM ============================================================================

echo.
echo [5/5] Generating energy attribution report...
echo [5/5] Generating energy attribution report... >> "%LOG_FILE%" 2>&1

REM Check if power.csv exists
if exist "%OUTPUT_DIR%\power.csv" (
    REM Run EnergyReport post-processor
    java -cp target\dl4j-profiler-demo.jar demo.EnergyReport "%OUTPUT_DIR%\method_times.csv" "%OUTPUT_DIR%\power.csv" >> "%LOG_FILE%" 2>&1
    
    if errorlevel 1 (
        echo [WARN] Energy report generation failed
        echo [WARN] Energy report generation failed >> "%LOG_FILE%"
    ) else (
        echo   [OK] Energy report generated
        echo   [OK] Energy report generated >> "%LOG_FILE%"
    )
) else (
    echo [WARN] power.csv not found. Cannot calculate energy attribution.
    echo [WARN] Run with Intel Power Gadget to enable energy calculations.
    echo [WARN] power.csv not found >> "%LOG_FILE%"
)

REM ============================================================================
REM COMPLETION
REM ============================================================================

echo.
echo ========================================================================
echo PROFILING COMPLETE
echo ========================================================================
echo Output files:
echo   - Method timing: %OUTPUT_DIR%\method_times.csv
echo   - Event log:     %OUTPUT_DIR%\method_events.csv
echo   - Power data:    %OUTPUT_DIR%\power.csv
echo   - JFR recording: %OUTPUT_DIR%\run.jfr
echo   - Combined log:  %OUTPUT_DIR%\run.log
echo ========================================================================
echo.
echo Next steps:
echo   1. Review %OUTPUT_DIR%\run.log for any errors
echo   2. Open %OUTPUT_DIR%\run.jfr in JDK Mission Control for detailed analysis
echo   3. Import CSV files into Excel/Python for visualization
echo ========================================================================

REM Pause to review results
pause