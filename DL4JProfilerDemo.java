package demo;

import org.deeplearning4j.datasets.iterator.impl.MnistDataSetIterator;
import org.deeplearning4j.nn.conf.MultiLayerConfiguration;
import org.deeplearning4j.nn.conf.NeuralNetConfiguration;
import org.deeplearning4j.nn.conf.layers.DenseLayer;
import org.deeplearning4j.nn.conf.layers.OutputLayer;
import org.deeplearning4j.nn.multilayer.MultiLayerNetwork;
import org.deeplearning4j.nn.weights.WeightInit;
import org.deeplearning4j.optimize.listeners.ScoreIterationListener;
import org.nd4j.evaluation.classification.Evaluation;
import org.nd4j.linalg.activations.Activation;
import org.nd4j.linalg.dataset.api.iterator.DataSetIterator;
import org.nd4j.linalg.learning.config.Adam;
import org.nd4j.linalg.lossfunctions.LossFunctions;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * DL4jProfilerDemo: Neural network energy profiling demonstration.
 * 
 * PURPOSE:
 * Trains a simple neural network on MNIST digit classification while
 * recording method-level timing data for energy attribution.
 * 
 * WORKFLOW:
 * 1. Initialize profiler session
 * 2. Build neural network architecture (3 layers)
 * 3. Load MNIST dataset (60k training, 10k test images)
 * 4. Train model for 3 epochs
 * 5. Evaluate accuracy on test set
 * 6. Generate profiling reports
 * 
 * EXTERNAL PROFILING:
 * Run with Intel Power Gadget and JFR enabled:
 * 
 * PowerLog3.0.exe -file energy_results\power.csv -duration 180
 * java -XX:StartFlightRecording=filename=energy_results\run.jfr \
 *      -Xms2g -Xmx3g \
 *      -jar target/dl4j-profiler-demo.jar
 * 
 * EXPECTED RUNTIME:
 * - First run: 5-10 minutes (includes MNIST download ~50MB)
 * - Subsequent runs: 2-3 minutes
 * 
 * NEURAL NETWORK ARCHITECTURE:
 * Input:  784 neurons (28x28 pixels, flattened)
 * Hidden: 784 → 256 (ReLU) → 128 (ReLU)
 * Output: 128 → 10 (Softmax, digits 0-9)
 * Loss:   Negative Log Likelihood
 * Optimizer: Adam (learning rate 0.001)
 */
public class DL4jProfilerDemo {
    
    // ===================================================================
    // CONFIGURATION CONSTANTS
    // ===================================================================
    
    /** Batch size: Number of images processed simultaneously */
    private static final int BATCH_SIZE = 128;
    
    /** Number of training epochs (full passes through dataset) */
    private static final int NUM_EPOCHS = 3;
    
    /** Random seed for reproducibility */
    private static final int RANDOM_SEED = 123;
    
    /** Output directory for profiling results */
    private static final String OUTPUT_DIR = "energy_results";
    
    // ===================================================================
    // MAIN ENTRY POINT
    // ===================================================================
    
    public static void main(String[] args) {
        try {
            // Print startup banner
            printBanner();
            
            // ═══════════════════════════════════════════════════════════
            // PHASE 0: Environment Setup
            // ═══════════════════════════════════════════════════════════
            System.out.println("\n[PHASE 0/5] Setting up environment...");
            setupEnvironment();
            
            // Start profiling session (records start timestamp)
            EnergyProfiler.startSession("dl4j-mnist-training");
            long programStartMs = System.currentTimeMillis();
            System.out.println("Program start time: " + programStartMs + " ms (for Power Gadget sync)");
            
            // ═══════════════════════════════════════════════════════════
            // PHASE 1: Neural Network Initialization
            // ═══════════════════════════════════════════════════════════
            System.out.println("\n[PHASE 1/5] Initializing neural network...");
            MultiLayerNetwork model;
            try (var span = EnergyProfiler.span("initModel")) {
                model = buildModel();
                System.out.println("✓ Model initialized: " + model.numParams() + " parameters");
            }
            
            // ═══════════════════════════════════════════════════════════
            // PHASE 2: Dataset Loading
            // ═══════════════════════════════════════════════════════════
            System.out.println("\n[PHASE 2/5] Loading MNIST dataset...");
            DataSetIterator trainIterator;
            DataSetIterator testIterator;
            try (var span = EnergyProfiler.span("loadData")) {
                trainIterator = new MnistDataSetIterator(BATCH_SIZE, true, RANDOM_SEED);
                testIterator = new MnistDataSetIterator(BATCH_SIZE, false, RANDOM_SEED);
                System.out.println("✓ Dataset loaded: 60,000 training + 10,000 test images");
            }
            
            // ═══════════════════════════════════════════════════════════
            // PHASE 3: Training Loop
            // ═══════════════════════════════════════════════════════════
            System.out.println("\n[PHASE 3/5] Training model...");
            for (int epoch = 0; epoch < NUM_EPOCHS; epoch++) {
                System.out.println("\n╔════════════════════════════════════╗");
                System.out.println("║   EPOCH " + (epoch + 1) + "/" + NUM_EPOCHS + "                      ║");
                System.out.println("╚════════════════════════════════════╝");
                
                try (var span = EnergyProfiler.span("trainEpoch" + epoch)) {
                    model.fit(trainIterator);
                    trainIterator.reset(); // Reset for next epoch
                }
            }
            
            // ═══════════════════════════════════════════════════════════
            // PHASE 4: Model Evaluation
            // ═══════════════════════════════════════════════════════════
            System.out.println("\n[PHASE 4/5] Evaluating model accuracy...");
            Evaluation evaluation;
            try (var span = EnergyProfiler.span("evaluate")) {
                evaluation = model.evaluate(testIterator);
            }
            
            System.out.println("\n" + "=".repeat(60));
            System.out.println("FINAL ACCURACY: " + String.format("%.2f%%", evaluation.accuracy() * 100));
            System.out.println("=".repeat(60));
            System.out.println(evaluation.stats());
            
            // ═══════════════════════════════════════════════════════════
            // PHASE 5: Report Generation
            // ═══════════════════════════════════════════════════════════
            System.out.println("\n[PHASE 5/5] Generating profiling reports...");
            EnergyProfiler.endSession();
            EnergyProfiler.printSummary();
            
            // Write CSV files
            String outputPath = OUTPUT_DIR + "/method";
            EnergyProfiler.writeCSV(outputPath);
            
            // Print next steps
            printNextSteps();
            
        } catch (Exception e) {
            System.err.println("\n[ERROR] Program failed:");
            e.printStackTrace();
            System.exit(1);
        }
    }
    
    // ===================================================================
    // NEURAL NETWORK CONSTRUCTION
    // ===================================================================
    
    /**
     * Builds a 3-layer feed-forward neural network for MNIST classification.
     * 
     * ARCHITECTURE:
     * Layer 0 (Input):  784 neurons (28x28 pixels)
     * Layer 1 (Hidden): 256 neurons, ReLU activation
     * Layer 2 (Hidden): 128 neurons, ReLU activation
     * Layer 3 (Output): 10 neurons, Softmax activation (digit classes 0-9)
     * 
     * TOTAL PARAMETERS: ~235,000 weights + biases
     * 
     * @return Initialized MultiLayerNetwork ready for training
     */
    private static MultiLayerNetwork buildModel() {
        System.out.println("  • Building 3-layer architecture...");
        
        MultiLayerConfiguration config = new NeuralNetConfiguration.Builder()
            // Random seed for weight initialization (reproducibility)
            .seed(RANDOM_SEED)
            
            // Weight initialization strategy (Xavier for better gradient flow)
            .weightInit(WeightInit.XAVIER)
            
            // Optimizer: Adam with learning rate 0.001
            .updater(new Adam(0.001))
            
            // Layer definitions
            .list()
            
            // Hidden Layer 1: 784 → 256 neurons
            .layer(0, new DenseLayer.Builder()
                .nIn(784)  // Input: flattened 28x28 image
                .nOut(256) // Output: 256 feature detectors
                .activation(Activation.RELU) // ReLU: max(0, x)
                .build())
            
            // Hidden Layer 2: 256 → 128 neurons
            .layer(1, new DenseLayer.Builder()
                .nIn(256)
                .nOut(128)
                .activation(Activation.RELU)
                .build())
            
            // Output Layer: 128 → 10 neurons (digit classes)
            .layer(2, new OutputLayer.Builder(LossFunctions.LossFunction.NEGATIVELOGLIKELIHOOD)
                .nIn(128)
                .nOut(10)  // 10 classes (digits 0-9)
                .activation(Activation.SOFTMAX) // Softmax: convert to probabilities
                .build())
            
            .build();
        
        MultiLayerNetwork model = new MultiLayerNetwork(config);
        model.init();
        
        // Print training progress every 100 iterations (optional)
        model.setListeners(new ScoreIterationListener(100));
        
        System.out.println("  • Total parameters: " + model.numParams());
        System.out.println("  • Memory estimate: ~" + (model.numParams() * 4 / 1_000_000) + " MB");
        
        return model;
    }
    
    // ===================================================================
    // ENVIRONMENT SETUP
    // ===================================================================
    
    /**
     * Sets up required directories and validates environment.
     * Creates: energy_results/ directory for output files.
     * Validates: Write permissions, disk space.
     */
    private static void setupEnvironment() throws IOException {
        // Create output directory
        Path outputPath = Paths.get(OUTPUT_DIR);
        Files.createDirectories(outputPath);
        System.out.println("  ✓ Output directory: " + outputPath.toAbsolutePath());
        
        // Validate write permissions
        File testFile = new File(OUTPUT_DIR, ".write_test");
        if (!testFile.createNewFile()) {
            throw new IOException("Cannot write to output directory: " + OUTPUT_DIR);
        }
        testFile.delete();
        System.out.println("  ✓ Write permissions verified");
        
        // Ensure DL4J data directory exists (MNIST downloads here)
        String dl4jHome = System.getProperty("user.home") + "/.deeplearning4j";
        Path dl4jPath = Paths.get(dl4jHome);
        Files.createDirectories(dl4jPath);
        System.out.println("  ✓ DL4J cache directory: " + dl4jPath.toAbsolutePath());
    }
    
    // ===================================================================
    // USER INTERFACE
    // ===================================================================
    
    /**
     * Prints startup banner with system info.
     */
    private static void printBanner() {
        System.out.println("\n" + "=".repeat(70));
        System.out.println("  DL4J ENERGY PROFILING DEMO");
        System.out.println("  Neural Network Training with Method-Level Energy Attribution");
        System.out.println("=".repeat(70));
        System.out.println("System Info:");
        System.out.println("  • Java Version: " + System.getProperty("java.version"));
        System.out.println("  • OS: " + System.getProperty("os.name") + " " + System.getProperty("os.arch"));
        System.out.println("  • Available Processors: " + Runtime.getRuntime().availableProcessors());
        System.out.println("  • Max Memory: " + (Runtime.getRuntime().maxMemory() / 1_000_000) + " MB");
        System.out.println("=".repeat(70));
    }
    
    /**
     * Prints next steps for energy analysis.
     */
    private static void printNextSteps() {
        System.out.println("\n" + "=".repeat(70));
        System.out.println("NEXT STEPS FOR ENERGY ANALYSIS");
        System.out.println("=".repeat(70));
        System.out.println("1. Check profiling output:");
        System.out.println("   • " + OUTPUT_DIR + "/method_times.csv");
        System.out.println("   • " + OUTPUT_DIR + "/method_events.csv");
        System.out.println();
        System.out.println("2. If Intel Power Gadget was running, correlate with:");
        System.out.println("   • " + OUTPUT_DIR + "/power.csv");
        System.out.println("   • Use EnergyReport.java to calculate Joules per method");
        System.out.println();
        System.out.println("3. If JFR was enabled, analyze with:");
        System.out.println("   • jfr print --events jdk.ExecutionSample " + OUTPUT_DIR + "/run.jfr");
        System.out.println("   • Open " + OUTPUT_DIR + "/run.jfr in JDK Mission Control");
        System.out.println();
        System.out.println("4. Experiment with hyperparameters:");
        System.out.println("   • Change BATCH_SIZE (64, 128, 256) → affects memory & energy");
        System.out.println("   • Change NUM_EPOCHS (1, 3, 5) → affects total energy");
        System.out.println("   • Modify network layers → affects computation intensity");
        System.out.println("=".repeat(70));
    }
}