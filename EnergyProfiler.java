package demo;

import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * EnergyProfiler: Lightweight method-level timing instrumentation.
 * 
 * PURPOSE:
 * Records start/end timestamps and total execution time for code sections ("spans").
 * Used to correlate software execution phases with external power measurements.
 * 
 * USAGE:
 * 1. Call EnergyProfiler.startSession("sessionName") at program start
 * 2. Wrap code sections with try-with-resources:
 *    try (var span = EnergyProfiler.span("methodName")) {
 *        // Your code here
 *    }
 * 3. Call EnergyProfiler.endSession() at program end
 * 4. Call EnergyProfiler.writeCSV("output.csv") to save results
 * 
 * OUTPUT FILES:
 * - method_times.csv: Aggregated time per method
 * - method_events.csv: Detailed BEGIN/END event log with timestamps
 * 
 * THREAD SAFETY:
 * Uses ConcurrentHashMap and AtomicLong for safe multi-threaded access.
 */
public class EnergyProfiler {
    
    // ===================================================================
    // DATA STRUCTURES
    // ===================================================================
    
    /**
     * Stores total execution time (in milliseconds) for each method.
     * Key: method name (e.g., "trainModel")
     * Value: cumulative time across all invocations
     */
    private static final Map<String, Long> methodTimes = new ConcurrentHashMap<>();
    
    /**
     * Stores invocation count for each method.
     * Key: method name
     * Value: number of times the method was called
     */
    private static final Map<String, AtomicLong> methodCalls = new ConcurrentHashMap<>();
    
    /**
     * Stores detailed event log (BEGIN/END pairs with timestamps).
     * Each entry: "timestamp_ms,event_type,method_name"
     */
    private static final java.util.List<String> eventLog = new java.util.concurrent.CopyOnWriteArrayList<>();
    
    /**
     * Session start time (milliseconds since epoch).
     * Used as reference point for relative timestamps.
     */
    private static long sessionStartTime = 0;
    
    /**
     * Session name (e.g., "dl4j-training").
     * Used for grouping related profiling runs.
     */
    private static String sessionName = "default";
    
    // ===================================================================
    // SESSION MANAGEMENT
    // ===================================================================
    
    /**
     * Starts a profiling session.
     * Call this at the beginning of your program.
     * 
     * @param name Session identifier (appears in output files)
     */
    public static void startSession(String name) {
        sessionName = name;
        sessionStartTime = System.currentTimeMillis();
        System.out.println("[PROFILER] Session started: " + name);
        System.out.println("[PROFILER] Start time: " + sessionStartTime + " ms since epoch");
        
        // Record session start event
        eventLog.add(sessionStartTime + ",SESSION_START," + name);
    }
    
    /**
     * Ends the profiling session.
     * Call this at the end of your program, before writeCSV().
     */
    public static void endSession() {
        long endTime = System.currentTimeMillis();
        long durationMs = endTime - sessionStartTime;
        
        System.out.println("[PROFILER] Session ended: " + sessionName);
        System.out.println("[PROFILER] Total duration: " + durationMs + " ms (" + 
                           (durationMs / 1000.0) + " seconds)");
        
        // Record session end event
        eventLog.add(endTime + ",SESSION_END," + sessionName);
    }
    
    // ===================================================================
    // SPAN CREATION (Core API)
    // ===================================================================
    
    /**
     * Creates a profiling span for a code section.
     * Use with try-with-resources for automatic timing:
     * 
     * try (var span = EnergyProfiler.span("loadData")) {
     *     // Your code here
     * } // Span auto-closes, records elapsed time
     * 
     * @param methodName Identifier for this code section
     * @return AutoCloseable span object
     */
    public static ProfileSpan span(String methodName) {
        return new ProfileSpan(methodName);
    }
    
    /**
     * ProfileSpan: Represents a timed code section.
     * Automatically records start/end when used with try-with-resources.
     */
    public static class ProfileSpan implements AutoCloseable {
        private final String methodName;
        private final long startNanos;  // High-resolution timestamp
        private final long startMillis; // Wall-clock time for event log
        
        /**
         * Constructor: Records start time.
         * @param methodName Identifier for this span
         */
        private ProfileSpan(String methodName) {
            this.methodName = methodName;
            this.startNanos = System.nanoTime();        // For duration calculation
            this.startMillis = System.currentTimeMillis(); // For event log
            
            // Record BEGIN event
            eventLog.add(startMillis + ",BEGIN," + methodName);
        }
        
        /**
         * Called automatically when try-with-resources block exits.
         * Records elapsed time and updates statistics.
         */
        @Override
        public void close() {
            long endNanos = System.nanoTime();
            long endMillis = System.currentTimeMillis();
            long elapsedMs = (endNanos - startNanos) / 1_000_000; // Convert ns to ms
            
            // Update aggregated time (thread-safe merge)
            methodTimes.merge(methodName, elapsedMs, Long::sum);
            
            // Update call count (thread-safe increment)
            methodCalls.computeIfAbsent(methodName, k -> new AtomicLong(0))
                       .incrementAndGet();
            
            // Record END event
            eventLog.add(endMillis + ",END," + methodName);
            
            // Optional: Print to console for real-time monitoring
            System.out.println("[PROFILER] " + methodName + " completed in " + 
                               elapsedMs + " ms");
        }
    }
    
    // ===================================================================
    // OUTPUT GENERATION
    // ===================================================================
    
    /**
     * Writes profiling results to CSV files.
     * Creates two files:
     * 1. method_times.csv - Aggregated time per method
     * 2. method_events.csv - Detailed event log
     * 
     * @param baseFilename Base filename (e.g., "energy_results/profiling")
     * @throws IOException If file write fails
     */
    public static void writeCSV(String baseFilename) throws IOException {
        // Extract directory path and create if needed
        Path basePath = Paths.get(baseFilename);
        Path directory = basePath.getParent();
        if (directory != null) {
            Files.createDirectories(directory);
        }
        
        // Write method_times.csv (aggregated data)
        String timesFile = baseFilename.replace(".csv", "_times.csv");
        writeMethodTimes(timesFile);
        
        // Write method_events.csv (detailed event log)
        String eventsFile = baseFilename.replace(".csv", "_events.csv");
        writeMethodEvents(eventsFile);
        
        System.out.println("[PROFILER] Results written to:");
        System.out.println("  - " + timesFile);
        System.out.println("  - " + eventsFile);
    }
    
    /**
     * Writes aggregated method times to CSV.
     * Format: method_name,total_time_ms,call_count,avg_time_ms
     */
    private static void writeMethodTimes(String filename) throws IOException {
        try (PrintWriter writer = new PrintWriter(new FileWriter(filename))) {
            // CSV header
            writer.println("method_name,total_time_ms,call_count,avg_time_ms");
            
            // Sort by total time (descending) for easier analysis
            methodTimes.entrySet().stream()
                .sorted((e1, e2) -> Long.compare(e2.getValue(), e1.getValue()))
                .forEach(entry -> {
                    String method = entry.getKey();
                    long totalTime = entry.getValue();
                    long callCount = methodCalls.getOrDefault(method, new AtomicLong(0)).get();
                    double avgTime = callCount > 0 ? (double) totalTime / callCount : 0.0;
                    
                    writer.printf("%s,%d,%d,%.2f%n", method, totalTime, callCount, avgTime);
                });
        }
    }
    
    /**
     * Writes detailed event log to CSV.
     * Format: timestamp_ms,event_type,method_name
     * Event types: SESSION_START, BEGIN, END, SESSION_END
     */
    private static void writeMethodEvents(String filename) throws IOException {
        try (PrintWriter writer = new PrintWriter(new FileWriter(filename))) {
            // CSV header
            writer.println("timestamp_ms,event_type,method_name");
            
            // Write all events in chronological order
            for (String event : eventLog) {
                writer.println(event);
            }
        }
    }
    
    // ===================================================================
    // CONSOLE REPORTING
    // ===================================================================
    
    /**
     * Prints a summary table to the console.
     * Useful for quick inspection without opening CSV files.
     */
    public static void printSummary() {
        System.out.println("\n" + "=".repeat(70));
        System.out.println("ENERGY PROFILER SUMMARY");
        System.out.println("=".repeat(70));
        System.out.printf("%-40s %10s %10s%n", "Method", "Time (ms)", "Calls");
        System.out.println("-".repeat(70));
        
        // Sort by total time (descending)
        methodTimes.entrySet().stream()
            .sorted((e1, e2) -> Long.compare(e2.getValue(), e1.getValue()))
            .forEach(entry -> {
                String method = entry.getKey();
                long totalTime = entry.getValue();
                long callCount = methodCalls.getOrDefault(method, new AtomicLong(0)).get();
                
                System.out.printf("%-40s %10d %10d%n", method, totalTime, callCount);
            });
        
        System.out.println("=".repeat(70) + "\n");
    }
}