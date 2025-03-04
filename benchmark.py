import time
import subprocess

LOG_FILE = "speed_comparison.log"
RUNS = 5  # Number of runs

with open(LOG_FILE, "w") as log_file:
    log_file.write("Running benchmark...\n")

    for i in range(1, RUNS + 1):
        log_file.write(f"Run #{i}\n")
        
        start_time = time.perf_counter()  # High-precision timer
        
        # Run the script and suppress output
        process = subprocess.run(["python", "test.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        end_time = time.perf_counter()
        duration = (end_time - start_time) * 1000  # Convert to milliseconds

        log_file.write(f"Execution Time: {duration:.3f} ms\n")

    log_file.write("Benchmark complete. Results saved in speed_comparison.log\n")

print("Benchmark complete. Results saved in speed_comparison.log")