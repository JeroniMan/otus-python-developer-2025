import logging
import os
import time
from dotenv import load_dotenv
from prometheus_client import Gauge, start_http_server
from indexer.utils import calculate_files_queue, collect_gaps, get_collection_state, get_worker_gaps_count

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# ваши метрики
current_collector_progress = Gauge("collector_progress", "current_collector_progress")
current_collector_base_slot = Gauge("current_collector_base_slot", "current_collector_base_slot")
current_collector_min_slot = Gauge("current_collector_min_slot", "current_collector_min_slot")

raw_files_queue = Gauge("raw_files_queue", "raw_files_queue")
raw_min_progress = Gauge("raw_min_progress", "raw_min_progress")

processed_files_queue = Gauge("processed_files_queue", "processed_files_queue")
processed_min_progress = Gauge("processed_min_progress", "processed_min_progress")

worker_gaps = Gauge("worker_gaps", "worker_gaps", ["worker_index"])
total_gaps = Gauge("total_gaps", "Total number of gaps found")


def update_metrics():
    """Update all metrics with error handling for empty data."""
    try:
        # Get collection state
        progress, base_slot, min_slot = get_collection_state()
        current_collector_progress.set(progress)
        current_collector_base_slot.set(base_slot)
        current_collector_min_slot.set(min_slot)
        logger.info(f"Collector state: progress={progress}, base_slot={base_slot}, min_slot={min_slot}")
    except Exception as e:
        logger.error(f"Error getting collection state: {e}")
        # Set default values
        current_collector_progress.set(0)
        current_collector_base_slot.set(0)
        current_collector_min_slot.set(0)

    try:
        # Get file queues
        raw_queue, min_raw_progress = calculate_files_queue("raw_data/")
        raw_files_queue.set(raw_queue)
        raw_min_progress.set(min_raw_progress)
        logger.info(f"Raw files: count={raw_queue}, oldest_timestamp={min_raw_progress}")
    except Exception as e:
        logger.error(f"Error calculating raw files queue: {e}")
        raw_files_queue.set(0)
        raw_min_progress.set(0)

    try:
        processed_queue, min_processed_progress = calculate_files_queue("processed_data/")
        processed_files_queue.set(processed_queue)
        processed_min_progress.set(min_processed_progress)
        logger.info(f"Processed files: count={processed_queue}, oldest_timestamp={min_processed_progress}")
    except Exception as e:
        logger.error(f"Error calculating processed files queue: {e}")
        processed_files_queue.set(0)
        processed_min_progress.set(0)

    try:
        # Get gaps data
        gaps_list = collect_gaps()
        total_gaps.set(len(gaps_list))

        if gaps_list:
            logger.info(f"Found {len(gaps_list)} gaps in data")

            # Get worker-specific gap counts
            worker_gap_counts = get_worker_gaps_count()

            for worker_id, gap_count in worker_gap_counts.items():
                worker_gaps.labels(worker_index=f"worker_{worker_id}").set(gap_count)
                if gap_count > 0:
                    logger.info(f"Worker {worker_id} has {gap_count} missing slots")
        else:
            logger.info("No gaps found in data")
            # Reset all worker gap metrics to 0
            worker_count = int(os.getenv("WORKER_COUNT", 32))
            for i in range(worker_count):
                worker_gaps.labels(worker_index=f"worker_{i}").set(0)

    except Exception as e:
        logger.error(f"Error collecting gaps: {e}")
        total_gaps.set(0)


if __name__ == "__main__":
    # Запускаем HTTP-сервер, который отдаёт /metrics
    start_http_server(8000)
    print("Metrics available at http://0.0.0.0:8000/metrics")
    logger.info("Metrics service started successfully")

    # Начальное обновление метрик
    update_metrics()

    while True:
        try:
            update_metrics()
        except Exception as e:
            logger.error(f"Unexpected error in metrics loop: {e}")
        time.sleep(10)
