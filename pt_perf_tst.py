import time
import random
import matplotlib.pyplot as plt
from PieceTable import PieceTable  # Assumes PieceTable.py is in the same dir

# --- Test Parameters ---
INITIAL_TEXT_SIZE = 2048  # Start with 2KB of text
NUM_OPERATIONS = 10000  # Total operations to perform
BATCH_SIZE = 100  # How many ops to average before recording a data point
INSERT_CHAR = "a large piece of text, qwertyuiopasdfghjklzxcvbnm,"  # Character to insert


# -----------------------

def run_performance_test():
    """
    Runs a fragmentation test on the PieceTable and plots the results.
    """
    print(f"Starting performance test...")
    print(f"Initial Size: {INITIAL_TEXT_SIZE}, Total Ops: {NUM_OPERATIONS}, Batch Size: {BATCH_SIZE}")

    # 1. Initialize
    initial_text = "a" * INITIAL_TEXT_SIZE
    pt = PieceTable(initial_text)

    results = []  # List to store (piece_count, avg_op_time)
    batch_times = []
    current_op_count = 0

    # 2. Fragment in a loop
    while current_op_count < NUM_OPERATIONS:
        if len(pt) == 0:
            # Document is empty, we must insert
            op_type = 'insert'
        else:
            # 3. Randomize operation
            op_type = random.choice(['insert', 'delete'])

        # 4. Random location
        if op_type == 'insert':
            # Can insert at any position, including the very end
            index = random.randint(0, len(pt))

            start_time = time.perf_counter()
            pt.insert(index, INSERT_CHAR)
            end_time = time.perf_counter()

        elif op_type == 'delete':
            # Can only delete from a valid position
            index = random.randint(0, len(pt) - 1)

            start_time = time.perf_counter()
            pt.delete(index, 1)
            end_time = time.perf_counter()

        batch_times.append(end_time - start_time)
        current_op_count += 1

        # 5. & 6. Measure and Record in Batches
        if current_op_count % BATCH_SIZE == 0:
            avg_time = sum(batch_times) / len(batch_times)
            piece_count = len(pt.pieces)

            results.append((piece_count, avg_time))
            print(
                f"Ops: {current_op_count:>5}/{NUM_OPERATIONS} | Pieces: {piece_count:>5} | Avg. Time: {avg_time:.8f}s")

            # Reset for next batch
            batch_times = []

    print("Test finished. Generating plot...")

    # 7. Plot
    if not results:
        print("No results to plot.")
        return

    x_pieces = [r[0] for r in results]
    y_time = [r[1] for r in results]

    plt.figure(figsize=(10, 6))
    plt.plot(x_pieces, y_time, 'o-')
    plt.title(f'PieceTable Performance (Linear Search) - {NUM_OPERATIONS} Ops')
    plt.xlabel('Number of Pieces in Table')
    plt.ylabel(f'Average Operation Time (s) (Batch Size={BATCH_SIZE})')
    plt.grid(True)
    plt.tight_layout()

    output_filename = 'piecetable_performance.png'
    plt.savefig(output_filename)
    print(f"Plot saved to {output_filename}")


if __name__ == "__main__":
    run_performance_test()