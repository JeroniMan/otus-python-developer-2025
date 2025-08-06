import logging
import os
import queue
import signal
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any
import requests
from dotenv import load_dotenv
from google.cloud import storage
from google.oauth2 import service_account

from indexer.utils import (
    download_json_from_gcs,
    upload_json_to_gcs,
    upload_json_to_local,
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 5
INITIAL_BACKOFF = 10.0  # seconds


@dataclass
class SlotTask:
    """Represents a slot to be processed"""

    slot: int
    retry_count: int = 0
    assigned_at: Optional[float] = None
    worker_id: Optional[int] = None


class PersistentSlotQueueManager:
    """Queue manager with persistent state for recovery"""

    def __init__(self, start_slot: int, rpc_url: str, state_bucket: str, storage_client, rpc_check_interval: int = 60):
        self.start_slot = start_slot
        self.current_slot = start_slot
        self.rpc_url = rpc_url
        self.rpc_check_interval = rpc_check_interval
        self.state_bucket = state_bucket
        self.storage_client = storage_client

        # State files
        self.state_file = "queue_manager_state.json"
        self.completed_slots_file = "completed_slots.json"
        self.last_state_save = 0
        self.state_save_interval = 60  # Save state every minute

        # RPC tracking
        self.last_rpc_slot = None
        self.last_rpc_check = 0
        self.slots_behind = 0

        # Main queue for slots to be processed
        self.slot_queue = queue.Queue(maxsize=10000)

        # Track slots being processed
        self.processing_slots: Dict[int, SlotTask] = {}
        self.processing_lock = threading.Lock()

        # Track completed slots for gap detection
        self.completed_slots: Set[int] = set()
        self.completed_lock = threading.Lock()

        # Statistics
        self.stats_lock = threading.Lock()
        self.worker_stats: Dict[int, Dict[str, Any]] = {}  # worker_id -> {processed: int, errors: int}

        # Control flags
        self.running = True

        # Create session for RPC calls
        self.session = requests.Session()
        self.session.mount(
            "https://", requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=0)
        )

    def fetch_last_rpc_slot(self) -> Optional[int]:
        """Fetch the latest slot from RPC"""
        payload = {"jsonrpc": "2.0", "id": 1, "method": "getSlot"}

        try:
            resp = self.session.post(self.rpc_url, json=payload, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            result = data.get("result")

            if result:
                logger.info(f"Current RPC slot: {result}")
                return result
            return None
        except Exception as e:
            logger.error(f"Failed to fetch last RPC slot: {e}")
            return None

    def update_rpc_slot(self):
        """Update the last RPC slot if enough time has passed"""
        now = time.time()
        if now - self.last_rpc_check >= self.rpc_check_interval:
            new_slot = self.fetch_last_rpc_slot()
            if new_slot:
                self.last_rpc_slot = new_slot
                self.slots_behind = max(0, new_slot - self.current_slot)
                logger.info(f"RPC slot updated: {new_slot}, we are {self.slots_behind} slots behind")
            self.last_rpc_check = now

    def fill_queue(self, batch_size: int = 1000):
        """Fill the queue with new slots"""
        # Check RPC slot before filling
        self.update_rpc_slot()

        added = 0
        while added < batch_size and self.running:
            # Don't go beyond the last known RPC slot
            if self.last_rpc_slot and self.current_slot > self.last_rpc_slot:
                logger.info(f"Reached last RPC slot {self.last_rpc_slot}, waiting...")
                break

            # Don't overfill the queue
            if self.slot_queue.qsize() >= 5000:
                break

            self.slot_queue.put(SlotTask(slot=self.current_slot))
            self.current_slot += 1
            added += 1

        if added > 0:
            logger.info(f"Added {added} slots to queue. Current: {self.current_slot}, RPC: {self.last_rpc_slot}")

    def should_fill_queue(self) -> bool:
        """Determine if we should fill the queue"""
        # Update RPC slot to get latest info
        self.update_rpc_slot()

        # Fill if queue is getting low
        if self.slot_queue.qsize() < 1000:
            # But only if we're not already at the RPC limit
            if not self.last_rpc_slot or self.current_slot <= self.last_rpc_slot:
                return True
        return False

    def get_slot_batch(self, worker_id: int, batch_size: int, timeout: float = 1.0) -> List[SlotTask]:
        """Get a batch of slots for a worker"""
        batch: List[SlotTask] = []
        deadline = time.time() + timeout

        while len(batch) < batch_size and time.time() < deadline:
            try:
                remaining_time = deadline - time.time()
                if remaining_time <= 0:
                    break

                task = self.slot_queue.get(timeout=min(remaining_time, 0.1))
                task.assigned_at = time.time()
                task.worker_id = worker_id

                with self.processing_lock:
                    self.processing_slots[task.slot] = task

                batch.append(task)
            except queue.Empty:
                # If we have some slots, return what we have
                if batch:
                    break
                # Otherwise, continue waiting until timeout
                continue

        return batch

    def complete_slot(self, slot: int, worker_id: int, success: bool = True):
        """Mark a slot as completed"""
        with self.processing_lock:
            self.processing_slots.pop(slot, None)

        if success:
            with self.completed_lock:
                self.completed_slots.add(slot)

        with self.stats_lock:
            if worker_id not in self.worker_stats:
                self.worker_stats[worker_id] = {"processed": 0, "errors": 0}

            if success:
                self.worker_stats[worker_id]["processed"] += 1
            else:
                self.worker_stats[worker_id]["errors"] += 1

    def requeue_slot(self, slot: int, worker_id: int):
        """Requeue a failed slot"""
        with self.processing_lock:
            task = self.processing_slots.pop(slot, None)

        if task:
            task.retry_count += 1
            if task.retry_count < 3:  # Max retries
                logger.warning(f"Requeuing slot {slot} (retry {task.retry_count})")
                self.slot_queue.put(task)
            else:
                logger.error(f"Slot {slot} failed after {task.retry_count} retries")
                self.complete_slot(slot, worker_id, success=False)

    def check_stale_slots(self, timeout: float = 300):
        """Check for slots that have been processing too long"""
        now = time.time()
        stale_slots = []

        with self.processing_lock:
            for slot, task in self.processing_slots.items():
                if task.assigned_at and (now - task.assigned_at) > timeout:
                    stale_slots.append(slot)

        for slot in stale_slots:
            logger.warning(f"Slot {slot} is stale, requeuing")
            self.requeue_slot(slot, -1)  # -1 indicates system requeue

    def get_gaps(self) -> List[int]:
        """Find gaps in completed slots"""
        with self.completed_lock:
            if not self.completed_slots:
                return []

            min_slot = min(self.completed_slots)
            max_slot = max(self.completed_slots)
            expected = set(range(min_slot, max_slot + 1))
            gaps = sorted(expected - self.completed_slots)

        return gaps

    def get_progress(self) -> Dict:
        """Get current progress statistics"""
        with self.completed_lock:
            completed_count = len(self.completed_slots)
            min_completed = min(self.completed_slots) if self.completed_slots else None
            max_completed = max(self.completed_slots) if self.completed_slots else None

        with self.processing_lock:
            processing_count = len(self.processing_slots)

        # Calculate processing rate
        total_processed = 0
        if self.worker_stats:
            total_processed = sum(stats["processed"] for stats in self.worker_stats.values())

        return {
            "completed": completed_count,
            "processing": processing_count,
            "queued": self.slot_queue.qsize(),
            "current_slot": self.current_slot,
            "last_rpc_slot": self.last_rpc_slot,
            "slots_behind": self.slots_behind,
            "min_completed": min_completed,
            "max_completed": max_completed,
            "gaps": len(self.get_gaps()),
            "worker_stats": dict(self.worker_stats),
            "total_processed": total_processed
        }

    def save_state(self, force: bool = False):
        """Periodically save queue manager state"""
        now = time.time()
        if not force and (now - self.last_state_save) < self.state_save_interval:
            return

        try:
            # Save main state
            state = {
                "current_slot": self.current_slot,
                "last_rpc_slot": self.last_rpc_slot,
                "last_rpc_check": self.last_rpc_check,
                "timestamp": datetime.now().isoformat(),
                "stats": self.get_progress(),
                "worker_stats": {str(k): v for k, v in self.worker_stats.items()},
            }

            upload_json_to_gcs(self.state_bucket, self.state_file, state)

            # Save completed slots separately (can be large)
            with self.completed_lock:
                if self.completed_slots:
                    # Convert set to sorted list for efficient storage
                    completed_data = {
                        "slots": sorted(self.completed_slots),
                        "count": len(self.completed_slots),
                        "min": min(self.completed_slots),
                        "max": max(self.completed_slots),
                    }
                    upload_json_to_gcs(self.state_bucket, self.completed_slots_file, completed_data, compress=True)

            self.last_state_save = now
            logger.info(f"Saved queue manager state: current_slot={self.current_slot}")

        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def restore_state(self) -> Dict:
        """Restore queue manager state from GCS"""
        try:
            # Restore main state
            state = download_json_from_gcs(self.state_bucket, self.state_file, default={})

            if state:
                self.current_slot = state.get("current_slot", self.start_slot)
                self.last_rpc_slot = state.get("last_rpc_slot")
                self.last_rpc_check = state.get("last_rpc_check", 0)
                self.worker_stats = state.get("worker_stats", {})

                # Convert string keys back to integers
                worker_stats = state.get("worker_stats", {})
                self.worker_stats = {int(k): v for k, v in worker_stats.items()}

                logger.info(f"Restored queue state: current_slot={self.current_slot}")

            # Restore completed slots
            completed_data = download_json_from_gcs(self.state_bucket, self.completed_slots_file, default={})
            if completed_data and "slots" in completed_data:
                self.completed_slots = set(completed_data["slots"])
                logger.info(f"Restored {len(self.completed_slots)} completed slots")

            return state

        except Exception as e:
            logger.error(f"Failed to restore state: {e}")
            return {}

    def close(self):
        """Clean up resources"""
        self.running = False
        self.session.close()


class SolanaCollector:
    """
    Collector for fetching Solana blockchain data via RPC API with queue-based approach.
    """

    def __init__(self) -> None:
        # Thread management
        self.threads: List[threading.Thread] = []
        self.running: bool = True
        self.queue_manager: Optional[PersistentSlotQueueManager] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.queue_filler_thread: Optional[threading.Thread] = None

        # Load configuration
        self.rpc_url: str = os.getenv("RPC_URL", "")
        self.worker_count: int = int(os.getenv("WORKER_COUNT", "1"))
        self.start_slot: int = int(os.getenv("START_SLOT", "0"))
        self.batch_size: int = int(os.getenv("BATCH_SIZE", "10"))
        self.upload_batch_multiplier: int = int(os.getenv("UPLOAD_BATCH_MULTIPLIER", "10"))
        self.gcs_bucket_name: str = os.getenv("GCS_BUCKET_NAME", "")
        self.gcs_state_bucket_name: str = os.getenv("GCS_STATE_BUCKET_NAME", "")
        self.store_mode: str = os.getenv("STORE_MODE", "local")

        # Initialize GCS client
        creds_path = os.getenv("GCP_SERVICE_ACCOUNT_JSON", "")
        if creds_path:
            try:
                creds = service_account.Credentials.from_service_account_file(creds_path)
                project = os.getenv("GCP_PROJECT") or None
                self._storage_client = storage.Client(credentials=creds, project=project)
                logger.info("Initialized GCS client with service account %s", creds_path)
            except Exception as e:
                logger.error("Failed to load service account credentials: %s", e)
                self._storage_client = storage.Client()
        else:
            self._storage_client = storage.Client()

        # Create session for RPC calls
        self.session = requests.Session()
        self.session.mount(
            "https://",
            requests.adapters.HTTPAdapter(
                pool_connections=self.worker_count,
                pool_maxsize=self.worker_count * 2,
                max_retries=0,  # We handle retries manually
            ),
        )

        logger.info(
            "Collector initialized: rpc_url=%s, workers=%d, start_slot=%d, batch_size=%d",
            self.rpc_url,
            self.worker_count,
            self.start_slot,
            self.batch_size,
        )

    def fetch_blocks_batch(self, slots: List[int]) -> Dict[int, Dict]:
        """
        Fetch multiple blocks in a single RPC call.
        Returns dict mapping slot -> block data
        """
        # Build batch request
        batch_payload = []
        for i, slot in enumerate(slots):
            batch_payload.append(
                {
                    "jsonrpc": "2.0",
                    "id": i,
                    "method": "getBlock",
                    "params": [
                        slot,
                        {
                            "encoding": "jsonParsed",
                            "maxSupportedTransactionVersion": 0,
                            "rewards": True,
                            "transactionDetails": "full",
                        },
                    ],
                }
            )

        collected_at = int(datetime.now(timezone.utc).timestamp())

        # Send batch request
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug(f"Fetching batch of {len(slots)} slots (attempt {attempt})")
                resp = self.session.post(self.rpc_url, json=batch_payload, timeout=30)
                resp.raise_for_status()

                batch_results = resp.json()

                # Process batch response
                results = {}
                should_retry = False

                for i, result in enumerate(batch_results):
                    slot = slots[i]

                    if "error" in result:
                        err = result["error"]
                        code, msg = err.get("code"), err.get("message", "")

                        if code in (-32007, -32009):  # Slot skipped
                            results[slot] = {
                                "slot": slot,
                                "status": "skipped",
                                "collected_at": collected_at,
                                "blockTime": 0,
                                "code": code,
                                "message": msg,
                            }
                        elif code in (-32002, -32003, -32004, -32005, -32014, -32016, -32602):
                            # Transient error - retry the whole batch
                            should_retry = True
                            break
                        else:
                            results[slot] = {
                                "slot": slot,
                                "status": "error",
                                "collected_at": collected_at,
                                "code": code,
                                "message": msg,
                            }
                    else:
                        block_result = result.get("result")
                        if block_result is None:
                            results[slot] = {
                                "slot": slot,
                                "status": "empty",
                                "collected_at": collected_at,
                                "code": 200,
                                "message": "Empty result",
                            }
                        else:
                            block_result.update(
                                {
                                    "slot": slot,
                                    "status": "ok",
                                    "collected_at": collected_at,
                                    "code": 200,
                                    "message": "OK",
                                }
                            )
                            results[slot] = block_result

                if should_retry and attempt < MAX_RETRIES:
                    backoff = INITIAL_BACKOFF * (2 ** (attempt - 1))
                    logger.warning(f"Transient error in batch, retrying after {backoff}s")
                    time.sleep(backoff)
                    continue

                return results

            except requests.RequestException as e:
                logger.error(f"Network error in batch request: {e}")
                if attempt == MAX_RETRIES:
                    return {slot: {"slot": slot, "status": "network_error"} for slot in slots}
                time.sleep(INITIAL_BACKOFF * attempt)
            except Exception as e:
                logger.error(f"Unexpected error in batch request: {e}")
                return {slot: {"slot": slot, "status": "error"} for slot in slots}

        return {slot: {"slot": slot, "status": "max_retries_exceeded"} for slot in slots}

    def queue_filler_worker(self):
        """Worker that continuously fills the queue"""
        while self.running:
            try:
                # The queue manager handles RPC checking internally
                if self.queue_manager.should_fill_queue():
                    self.queue_manager.fill_queue(batch_size=2000)

                time.sleep(1)
            except Exception as e:
                logger.error(f"Queue filler error: {e}")
                time.sleep(5)

    def monitor_worker(self):
        """Monitor thread for stats and stale slots"""
        while self.running:
            try:
                # Check for stale slots
                self.queue_manager.check_stale_slots()

                # Save state periodically
                self.queue_manager.save_state()

                # Log progress
                progress = self.queue_manager.get_progress()
                logger.info(
                    f"Progress: Completed={progress['completed']}, "
                    f"Processing={progress['processing']}, "
                    f"Queued={progress['queued']}, "
                    f"Current={progress['current_slot']}, "
                    f"RPC={progress['last_rpc_slot']}, "
                    f"Behind={progress['slots_behind']}, "
                    f"Gaps={progress['gaps']}"
                )

                # Check for gaps and requeue if needed
                gaps = self.queue_manager.get_gaps()
                if gaps[:10]:  # Requeue first 10 gaps
                    logger.info(f"Found {len(gaps)} gaps, requeuing first 10")
                    for gap_slot in gaps[:10]:
                        self.queue_manager.slot_queue.put(SlotTask(slot=gap_slot))

                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(30)

    def worker(self, worker_id: int):
        """Updated worker with batch fetching from queue"""
        logger.info(f"Worker {worker_id} starting")
        batch: List[SlotTask] = []
        batch_slots: List[int] = []

        while self.running:
            try:
                # Get batch of slots from queue
                slot_tasks = self.queue_manager.get_slot_batch(
                    worker_id, batch_size=self.batch_size, timeout=1.0  # Use batch_size for RPC batching
                )

                if not slot_tasks:
                    # No slots available, check if we should upload partial batch
                    if batch and len(batch) >= (self.batch_size * self.upload_batch_multiplier) // 2:
                        self.upload_batch(worker_id, batch, batch_slots)
                        batch, batch_slots = [], []
                    continue

                # Extract slot numbers
                slots_to_fetch = [task.slot for task in slot_tasks]

                # Fetch all blocks in one RPC call
                results = self.fetch_blocks_batch(slots_to_fetch)

                # Process results
                for task in slot_tasks:
                    slot = task.slot
                    data = results.get(slot)

                    if data:
                        # Check for fatal errors
                        if data.get("status") == "error" and data.get("code") in (-32010, -32013, -32015):
                            logger.error(f"Worker {worker_id} stopping due to error on slot {slot}")
                            self.queue_manager.requeue_slot(slot, worker_id)
                            self.running = False
                            break

                        if data.get("status") != "network_error":
                            batch.append(data)
                            batch_slots.append(slot)
                            self.queue_manager.complete_slot(slot, worker_id, success=True)
                        else:
                            # Failed to fetch, requeue
                            self.queue_manager.requeue_slot(slot, worker_id)
                    else:
                        # Failed to fetch, requeue
                        self.queue_manager.requeue_slot(slot, worker_id)

                logger.info(f"[Worker {worker_id}] Fetched batch of {len(slot_tasks)} slots")

                # Upload when we have enough data
                if len(batch) >= self.batch_size * self.upload_batch_multiplier:
                    self.upload_batch(worker_id, batch, batch_slots)
                    batch, batch_slots = [], []

            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                time.sleep(1)

        # Upload any remaining batch
        if batch:
            self.upload_batch(worker_id, batch, batch_slots)

        logger.info(f"Worker {worker_id} stopped")

    def upload_batch(self, worker_id: int, batch: List[Dict], slots: List[int]):
        """Upload a batch of blocks"""
        if not batch:
            return

        # Sort by slot for consistent ordering
        sorted_data = sorted(zip(slots, batch), key=lambda x: x[0])
        batch = [item[1] for item in sorted_data]
        slots = [item[0] for item in sorted_data]

        first_slot = slots[0]
        last_slot = slots[-1]
        timestamp = int(time.time())

        # Extract block times
        slot_times = []
        for data in batch:
            slot_time = data.get("blockTime")
            if slot_time:
                slot_times.append(slot_time)

        first_time = min(slot_times) if slot_times else 0
        last_time = max(slot_times) if slot_times else 0

        # Generate filename
        blob = f"raw_data/slots_{first_slot}_{last_slot}_{first_time}_{last_time}_{timestamp}_{worker_id}.json"

        # Upload logic
        if self.store_mode == "local":
            result = upload_json_to_local("raw_data", blob, batch)
        elif self.store_mode == "gcs":
            result = upload_json_to_gcs(self.gcs_bucket_name, blob, batch, compress=True)
        else:
            result = False

        if result:
            logger.info(f"[Worker {worker_id}] Uploaded {len(batch)} blocks ({first_slot}-{last_slot})")

            # Save state
            state = {
                "worker_id": worker_id,
                "last_uploaded_slot": last_slot,
                "timestamp": timestamp,
                "batch_count": len(batch),
            }
            state_file = f"worker_{worker_id}.json"
            upload_json_to_gcs(self.gcs_state_bucket_name, state_file, state)
        else:
            logger.error(f"[Worker {worker_id}] Upload failed for {first_slot}-{last_slot}")
            # Requeue all slots in the failed batch
            for slot in slots:
                self.queue_manager.slot_queue.put(SlotTask(slot=slot))

    def reconcile_start_slot_improved(self):
        """Improved reconciliation that considers multiple data sources"""
        logger.info("Starting improved reconciliation...")

        # 1. Find the last uploaded slot across all workers
        last_uploaded_slots = []
        bucket = self._storage_client.bucket(self.gcs_state_bucket_name)

        for blob in bucket.list_blobs(prefix="worker_"):
            try:
                state = download_json_from_gcs(self.gcs_state_bucket_name, blob.name, default={})
                if "last_uploaded_slot" in state:
                    last_uploaded_slots.append(state["last_uploaded_slot"])
            except Exception as e:
                logger.error(f"Error reading worker state {blob.name}: {e}")

        # 2. Initialize and restore queue manager state
        self.queue_manager = PersistentSlotQueueManager(
            start_slot=self.start_slot,
            rpc_url=self.rpc_url,
            state_bucket=self.gcs_state_bucket_name,
            storage_client=self._storage_client,
        )

        queue_state = self.queue_manager.restore_state()

        # 3. Analyze all data files to find actual progress
        actual_max_slot = self.analyze_uploaded_files()

        # 4. Determine the best restart point
        restart_candidates = []

        if last_uploaded_slots:
            # Minimum of last uploaded (safe point)
            restart_candidates.append(min(last_uploaded_slots))

        if queue_state.get("current_slot"):
            # Queue manager's current slot
            restart_candidates.append(queue_state["current_slot"])

        if actual_max_slot:
            # Actual maximum slot found in files
            restart_candidates.append(actual_max_slot + 1)

        if self.queue_manager.completed_slots:
            # Maximum completed slot
            restart_candidates.append(max(self.queue_manager.completed_slots) + 1)

        # Choose the most conservative (minimum) restart point
        if restart_candidates:
            self.start_slot = min(restart_candidates)
            logger.info(f"Restart point determined: {self.start_slot}")
            logger.info(f"Candidates were: {restart_candidates}")
        else:
            logger.warning(f"No recovery data found, starting from {self.start_slot}")

        # 5. Fill gaps from previous run
        gaps = self.queue_manager.get_gaps()
        if gaps:
            logger.info(f"Found {len(gaps)} gaps from previous run: {gaps[:10]}...")
            # Add gaps to front of queue
            for gap in gaps:
                self.queue_manager.slot_queue.put(SlotTask(slot=gap, retry_count=0))

        # 6. Check for remaining queue slots from previous run
        try:
            remaining_data = download_json_from_gcs(
                self.gcs_state_bucket_name, "remaining_queue_slots.json", default={}
            )
            if remaining_data.get("slots"):
                logger.info(f"Found {len(remaining_data['slots'])} remaining queued slots from previous run")
                for slot in remaining_data["slots"]:
                    if slot not in self.queue_manager.completed_slots:
                        self.queue_manager.slot_queue.put(SlotTask(slot=slot))
        except Exception as e:
            logger.error(f"Error loading remaining queue slots: {e}")

        # 7. Set current slot for queue manager
        self.queue_manager.current_slot = self.start_slot

        logger.info(f"Reconciliation complete. Starting from slot {self.start_slot}")

    def analyze_uploaded_files(self) -> Optional[int]:
        """Analyze uploaded files to find the actual maximum slot processed"""
        try:
            bucket = self._storage_client.bucket(self.gcs_bucket_name)
            max_slot = None

            # List all data files
            for blob in bucket.list_blobs(prefix="raw_data/"):
                # Parse filename: slots_1000_2000_timestamp_worker.json
                parts = blob.name.split("_")
                if len(parts) >= 4 and "slots" in parts[0]:
                    try:
                        # Find the last slot number in the filename
                        for i, part in enumerate(parts):
                            if part.isdigit() and i > 0 and parts[i - 1].isdigit():
                                last_slot = int(part)
                                if max_slot is None or last_slot > max_slot:
                                    max_slot = last_slot
                                break

                    except ValueError:
                        continue

            if max_slot:
                logger.info(f"Found maximum uploaded slot: {max_slot}")

            return max_slot

        except Exception as e:
            logger.error(f"Error analyzing uploaded files: {e}")
            return None

    def run(self) -> None:
        """Start the collector with queue-based approach"""
        # Perform reconciliation
        self.reconcile_start_slot_improved()

        # Start queue filler thread
        self.queue_filler_thread = threading.Thread(target=self.queue_filler_worker, daemon=True, name="QueueFiller")
        self.queue_filler_thread.start()

        # Start monitor thread
        self.monitor_thread = threading.Thread(target=self.monitor_worker, daemon=True, name="Monitor")
        self.monitor_thread.start()

        # Start worker threads
        logger.info(f"Starting {self.worker_count} workers with batch size {self.batch_size}")
        for wid in range(self.worker_count):
            t = threading.Thread(target=self.worker, args=(wid,), daemon=True, name=f"Worker-{wid}")
            t.start()
            self.threads.append(t)

        logger.info("All threads started successfully")

    def stop(self) -> None:
        """Enhanced stop that saves final state"""
        logger.info("Stopping collector and saving final state...")
        self.running = False

        # Save final queue manager state
        if self.queue_manager:
            self.queue_manager.save_state(force=True)

            # Save any remaining queue contents
            remaining_slots = []
            try:
                while not self.queue_manager.slot_queue.empty():
                    task = self.queue_manager.slot_queue.get_nowait()
                    remaining_slots.append(task.slot)
            except queue.Empty:
                pass

            if remaining_slots:
                logger.info(f"Saving {len(remaining_slots)} remaining queued slots")
                upload_json_to_gcs(
                    self.gcs_state_bucket_name,
                    "remaining_queue_slots.json",
                    {"slots": remaining_slots, "timestamp": datetime.now().isoformat(), "reason": "shutdown"},
                )

            # Close queue manager resources
            self.queue_manager.close()

        # Close session
        if hasattr(self, "session"):
            self.session.close()

        # Wait for all threads to finish
        logger.info("Waiting for threads to finish...")

        threads_to_join = []
        if self.queue_filler_thread:
            threads_to_join.append(self.queue_filler_thread)
        if self.monitor_thread:
            threads_to_join.append(self.monitor_thread)
        threads_to_join.extend(self.threads)

        for t in threads_to_join:
            if t.is_alive():
                logger.info(f"Waiting for {t.name} to finish...")
                t.join(timeout=5.0)
                if t.is_alive():
                    logger.warning(f"{t.name} did not finish in time")

        logger.info("Collector stopped cleanly")

    def validate_recovery(self):
        """Validate recovery data makes sense"""
        if not self.queue_manager:
            return

        if self.start_slot > self.queue_manager.current_slot:
            logger.warning(
                f"Start slot ({self.start_slot}) ahead of queue current slot " f"({self.queue_manager.current_slot})!"
            )

        gaps = self.queue_manager.get_gaps()
        if len(gaps) > 1000:
            logger.warning(f"Large number of gaps detected: {len(gaps)}")
            logger.info("Consider running a dedicated gap-filling process")

        # Check worker states consistency
        if self.queue_manager.worker_stats:
            total_processed = sum(stats["processed"] for stats in self.queue_manager.worker_stats.values())
            logger.info(f"Total slots processed in previous run: {total_processed}")


def setup_signal_handlers(collector):
    """Setup graceful shutdown handlers"""

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        collector.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main entry point"""
    # Validate required environment variables
    required_vars = ["RPC_URL", "GCS_BUCKET_NAME", "GCS_STATE_BUCKET_NAME"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)

    # Create collector instance
    collector = SolanaCollector()

    # Setup signal handlers for graceful shutdown
    setup_signal_handlers(collector)

    try:
        # Start the collector
        collector.run()

        # Keep the main thread alive
        logger.info("Collector is running. Press Ctrl+C to stop.")
        while collector.running:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        # Ensure clean shutdown
        collector.stop()


if __name__ == "__main__":
    main()
