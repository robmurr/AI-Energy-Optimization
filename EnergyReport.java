package demo;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.*;

/**
 * EnergyReport: Correlates method timing with power measurements.
 * 
 * PURPOSE:
 * Reads method_times.csv (from EnergyProfiler) and power.csv (from Intel Power Gadget)
 * to calculate energy consumption (Joules) for each method.
 * 
 * FORMULA:
 * Energy (J) = Power (W) × Time (s)
 * Method Energy = Total Energy × (Method Time / Total Time)
 * 
 * USAGE:
 * java -cp target/dl4j-profiler-demo.jar demo.EnergyReport \
 *      energy_results/method_times.csv \
 *      energy_results/power.csv
 * 
 * INPUT FILES:
 * 1. method_times.csv - Columns: method_name, total_time_ms, call_count, avg_time_ms
 * 2. power.csv - Columns: System Time, Processor Power_0(Watt), Cumulative Energy_0(Joules), ...
 * 
 * OUTPUT:
 * Console report showing energy per method in Joules and percentage of total.
 */
public class EnergyReport {
    
    /**
     * Main entry point.
     * @param args [0] method_times.csv path, [1] power.csv path
     */
    public static void main(String[] args) {
        if (args.length < 2) {
            System.err.println("Usage: java EnergyReport <method_times.csv> <power.csv>");
            System.err.println("Example: java EnergyReport energy_results/method_times.csv energy_results/power.csv");
            System.exit(1);
        }
        
        String methodTimesFile = args[0];
        String powerFile = args[1];
        
        try {
            // Load data from CSV files
            Map<String, Long> methodTimes = loadMethodTimes(methodTimesFile);
            double totalEnergyJoules = loadTotalEnergy(powerFile);
            
            // Calculate total execution time
            long totalTimeMs = methodTimes.values().stream()
                .mapToLong(Long::longValue)
                .sum();
            
            // Calculate energy per method
            Map<String, Double> methodEnergy = new HashMap<>();
            for (Map.Entry<String, Long> entry : methodTimes.entrySet()) {
                String method = entry.getKey();
                long timeMs = entry.getValue();
                
                // Proportional energy attribution
                double energyJoules = totalEnergyJoules * ((double) timeMs / totalTimeMs);
                methodEnergy.put(method, energyJoules);
            }
            
            // Print report
            printEnergyReport(methodTimes, methodEnergy, totalEnergyJoules, totalTimeMs);
            
        } catch (IOException e) {
            System.err.println("Error reading input files:");
            e.printStackTrace();
            System.exit(1);
        }
    }
    
    /**
     * Loads method timing data from CSV.
     * @param filename Path to method_times.csv
     * @return Map of method name → total time (ms)
     */
    private static Map<String, Long> loadMethodTimes(String filename) throws IOException {
        Map<String, Long> methodTimes = new HashMap<>();
        
        try (BufferedReader reader = new BufferedReader(new FileReader(filename))) {
            String line = reader.readLine(); // Skip header
            
            while ((line = reader.readLine()) != null) {
                String[] parts = line.split(",");
                if (parts.length >= 2) {
                    String methodName = parts[0].trim();
                    long timeMs = Long.parseLong(parts[1].trim());
                    methodTimes.put(methodName, timeMs);
                }
            }
        }
        
        System.out.println("[INFO] Loaded " + methodTimes.size() + " methods from " + filename);
        return methodTimes;
    }
    
    /**
     * Extracts total energy from Power Gadget CSV.
     * Reads the "Cumulative Processor Energy_0(Joules)" column.
     * 
     * @param filename Path to power.csv
     * @return Total energy consumed (Joules)
     */
    private static double loadTotalEnergy(String filename) throws IOException {
        double maxEnergy = 0.0;
        
        try (BufferedReader reader = new BufferedReader(new FileReader(filename))) {
            String headerLine = reader.readLine();
            if (headerLine == null) {
                throw new IOException("Empty power.csv file");
            }
            
            // Find column index for cumulative energy
            String[] headers = headerLine.split(",");
            int energyColumnIndex = -1;
            for (int i = 0; i < headers.length; i++) {
                if (headers[i].contains("Cumulative Processor Energy") && 
                    headers[i].contains("Joules")) {
                    energyColumnIndex = i;
                    break;
                }
            }
            
            if (energyColumnIndex == -1) {
                throw new IOException("Could not find energy column in power.csv");
            }
            
            // Read all rows and find maximum cumulative energy
            String line;
            while ((line = reader.readLine()) != null) {
                String[] parts = line.split(",");
                if (parts.length > energyColumnIndex) {
                    try {
                        double energy = Double.parseDouble(parts[energyColumnIndex].trim());
                        maxEnergy = Math.max(maxEnergy, energy);
                    } catch (NumberFormatException e) {
                        // Skip malformed rows
                    }
                }
            }
        }
        
        System.out.println("[INFO] Total energy from " + filename + ": " + 
                           String.format("%.2f", maxEnergy) + " Joules");
        return maxEnergy;
    }
    
    /**
     * Prints formatted energy report to console.
     */
    private static void printEnergyReport(Map<String, Long> methodTimes,
                                         Map<String, Double> methodEnergy,
                                         double totalEnergyJoules,
                                         long totalTimeMs) {
        System.out.println("\n" + "=".repeat(80));
        System.out.println("ENERGY ATTRIBUTION REPORT");
        System.out.println("=".repeat(80));
        System.out.println("Total Energy: " + String.format("%.2f", totalEnergyJoules) + " Joules");
        System.out.println("Total Time: " + totalTimeMs + " ms (" + (totalTimeMs / 1000.0) + " seconds)");
        System.out.println("=".repeat(80));
        System.out.printf("%-40s %12s %12s %12s%n", 
                          "Method", "Time (ms)", "Energy (J)", "% of Total");
        System.out.println("-".repeat(80));
        
        // Sort by energy (descending)
        methodEnergy.entrySet().stream()
            .sorted((e1, e2) -> Double.compare(e2.getValue(), e1.getValue()))
            .forEach(entry -> {
                String method = entry.getKey();
                double energyJ = entry.getValue();
                long timeMs = methodTimes.get(method);
                double percentage = (energyJ / totalEnergyJoules) * 100;
                
                System.out.printf("%-40s %12d %12.2f %11.1f%%%n",
                                  method, timeMs, energyJ, percentage);
            });
        
        System.out.println("=".repeat(80) + "\n");
    }
}