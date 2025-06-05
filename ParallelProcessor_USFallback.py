import os
import subprocess
import csv
import threading
import sys
import datetime  # ADDED – for timestamps
import pathlib   # ADDED – for automatic run log

# ------------------------------------------------------------------- #
# 1)  open a dated log-file that will receive *everything* we print   #
# ------------------------------------------------------------------- #
LOGFILE = pathlib.Path(                       # ADDED
    f"run_{datetime.datetime.now():%Y%m%d_%H%M%S}.log"
).open("a", encoding="utf-8")                 # ADDED

# Lock to synchronize console output from multiple threads
print_lock = threading.Lock()

def safe_print(message: str) -> None:
    """Thread-safe print helper that prefixes [hh:mm:ss]
       and duplicates the line into LOGFILE."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")  # ADDED
    line = f"[{timestamp}] {message}"                          # ADDED
    with print_lock:
        print(line, flush=True)                                # CHANGED
        LOGFILE.write(line + "\n")                             # ADDED

def read_output(process, idx, eid):
    # Read stdout
    for raw in process.stdout:
        text = raw.rstrip()
        safe_print(f"[Worker #{idx + 1}: EID {eid}] -> {text}")
    # Read stderr
    for raw in process.stderr:
        text = raw.rstrip()
        safe_print(f"[Worker #{idx + 1}: EID {eid} ERROR] -> {text}")

def main():
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Path to the CSV file
    eids_file = os.path.join(script_dir, 'eids_fallback.csv')

    # Read EIDs from CSV
    eids = []
    with open(eids_file, 'r', newline='') as fh:               # CHANGED (newline)
        for row in csv.reader(fh):
            if row and row[0].strip():
                eids.append(row[0].strip())

    if not eids:
        safe_print("No EIDs found – exiting.")
        return

    # Path to TealUS.py
    tealus_path = os.path.join(script_dir, 'TealUS_fallback.py')

    # Start subprocesses for each EID
    processes = []
    for idx, eid in enumerate(eids):
        process = subprocess.Popen(
            [sys.executable, tealus_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=script_dir
        )
        process.stdin.write(f"{eid}\n")
        process.stdin.flush()
        process.stdin.close()

        t = threading.Thread(target=read_output, args=(process, idx, eid))
        t.start()
        processes.append((process, eid, t))

    # Gather results
    results = {}
    for process, eid, t in processes:
        return_code = process.wait()
        t.join()
        status = 'PASS' if return_code == 0 else 'FAIL'
        results[eid] = status

    # Summary
    safe_print("\nSummary of EID Processing:")
    for eid, status in results.items():
        safe_print(f"{eid}: {status}")

    LOGFILE.close()                                            # ADDED

if __name__ == '__main__':
    main()
