from prometheus_client import start_http_server, Counter, Gauge
import time
from dotenv import load_dotenv
from utils import get_collection_state, collect_gaps, calculate_files_queue
from itertools import groupby



# Load environment variables
load_dotenv()

# ваши метрики
current_collector_progress = Gauge('collector_progress', 'current_collector_progress')
current_collector_base_slot  = Gauge('current_collector_base_slot',  'current_collector_base_slot')
current_collector_min_slot = Gauge('current_collector_min_slot', 'current_collector_min_slot')

raw_files_queue = Gauge('raw_files_queue', 'raw_files_queue')
raw_min_progress = Gauge('raw_min_progress', 'raw_min_progress')

processed_files_queue = Gauge('processed_files_queue', 'processed_files_queue')
processed_min_progress = Gauge('processed_min_progress', 'processed_min_progress')

worker_gaps = Gauge('worker_gaps', 'worker_gaps', ['worker_index'])


def update_metrics():
    progress, base_slot, min_slot = get_collection_state()
    current_collector_progress.set(progress)
    current_collector_base_slot.set(base_slot)
    current_collector_min_slot.set(min_slot)

    raw_queue, min_raw_progress = calculate_files_queue('raw_data/')
    processed_queue, min_processed_progress = calculate_files_queue('processed_data/')

    raw_files_queue.set(raw_queue)
    raw_min_progress.set(min_raw_progress)
    processed_files_queue.set(processed_queue)
    processed_min_progress.set(min_raw_progress)

    data = collect_gaps()
    grouped_counts = {key: len(list(group)) for key, group in
                      groupby(sorted(data, key=lambda x: x['index']), key=lambda x: x['index'])}
    print(grouped_counts)

    for name, value in grouped_counts.items():
        worker_gaps.labels(worker_index=f"worker_{name}").set(value)


if __name__ == '__main__':
    # Запускаем HTTP-сервер, который отдаёт /metrics
    start_http_server(8000)
    print("Metrics available at http://0.0.0.0:8000/metrics")
    while True:
        update_metrics()
        time.sleep(10)