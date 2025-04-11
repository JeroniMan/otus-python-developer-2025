#!/usr/bin/env python3
import argparse
import gzip
import json
import logging
import os
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from io import TextIOWrapper
from string import Template
from typing import IO, Optional, Tuple, cast

import structlog

# -------------------- DEFAULT CONFIGURATION --------------------
DEFAULT_CONFIG = {
    "REPORT_SIZE": 100,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./logs",
    "LOG_FILE": None,  # If not provided, logs go to stdout
    "ERRORS_THRESHOLD": 10,  # Allowed parse errors in percent (e.g., 10 means 10%)
    "TEMPLATE_PATH": "reports/report.html",
    "CONFIG_PATH": "config/config.json",
}


# -------------------- CONFIGURATION READING --------------------
def read_config(config_path: str) -> dict:
    """
    Reads configuration from a file. If the file does not exist or cannot be parsed,
    the script exits with an error. The resulting configuration is a merge of the default
    config and the file config (with file config taking precedence).
    """
    if not os.path.exists(config_path):
        logging.error("Config file %s does not exist.", config_path)
        sys.exit(1)

    try:
        with open(config_path, "r") as f:
            content = f.read().strip()
            user_config = json.loads(content) if content else {}
    except Exception as e:
        logging.error("Error parsing config file %s: %s", config_path, e, exc_info=True)
        sys.exit(1)

    config = DEFAULT_CONFIG.copy()
    config.update(user_config)
    return config


# -------------------- LOGGER SETUP --------------------
def setup_logger(log_path: str, level: str):
    """
    Configures structured logging using structlog. Logs are written to the file specified by log_path,
    or to stdout if log_path is not provided.
    """
    log_level = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "error": logging.ERROR,
    }.get(level.lower(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=open(log_path, "a") if log_path else sys.stdout,
        level=log_level,
    )
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
    )


# -------------------- LOG FILE CHECKING --------------------
def check_logs(log_dir: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Scans the log directory for files matching:
      nginx-access-ui.log-YYYYMMDD(.gz)?
    and returns the full path of the latest log (by date in the file name)
    and the date formatted as 'YYYY.MM.DD'.
    """
    pattern = r"nginx-access-ui\.log-(\d{8})(\.gz)?"
    latest_log = None
    latest_date = None

    if not os.path.isdir(log_dir):
        logging.error("LOG_DIR '%s' does not exist or is not a directory.", log_dir)
        return (None, None)

    for log_file in os.listdir(log_dir):
        match = re.match(pattern, log_file)
        if match:
            log_date = match.group(1)
            try:
                file_date = datetime.strptime(log_date, "%Y%m%d")
                if latest_date is None or file_date > latest_date:
                    latest_date = file_date
                    latest_log = log_file
            except ValueError:
                continue

    if latest_log:
        latest_log_path = os.path.join(log_dir, latest_log)
        if latest_date is None:
            return (None, None)
        date_str = latest_date.strftime("%Y.%m.%d")
        logging.info("Latest log file is %s, date %s", latest_log_path, date_str)
        return latest_log_path, date_str
    else:
        return (None, None)


# -------------------- LOG PARSING AS A GENERATOR --------------------
def iter_log_records(log_data: str):
    """
    Generator that parses each log line using the nginx log format.
    Yields a dictionary with keys 'url' and 'time' if the line is parsed successfully;
    otherwise yields None.
    """
    log_pattern = re.compile(
        r"(?P<remote_addr>\S+)\s+"
        r"(?P<remote_user>\S+)\s+"
        r"(?P<http_x_real_ip>\S+)\s+"
        r"\[(?P<time_local>[^\]]+)]\s+"
        r'"(?P<request>[^"]+)"\s+'
        r"(?P<status>\d+)\s+"
        r"(?P<body_bytes_sent>\S+)\s+"
        r'"(?P<http_referer>[^"]*)"\s+'
        r'"(?P<http_user_agent>[^"]*)"\s+'
        r'"(?P<http_x_forwarded_for>[^"]*)"\s+'
        r'"(?P<http_X_REQUEST_ID>[^"]*)"\s+'
        r'"(?P<http_X_RB_USER>[^"]*)"\s+'
        r"(?P<request_time>[\d.]+)"
    )

    for line in log_data.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        match = log_pattern.match(line)
        if not match:
            yield None
            continue
        request_str = match.group("request")
        parts = request_str.split()
        if len(parts) < 2:
            yield None
            continue
        url = parts[1]
        try:
            req_time = float(match.group("request_time"))
        except ValueError:
            yield None
            continue
        yield {"url": url, "time": req_time}


def aggregate_records(record_iter, errors_threshold: float) -> dict:
    """
    Consumes the generator of parsed log records.
    Aggregates statistics by URL and counts parse errors.
    If the ratio of errors to total lines exceeds errors_threshold, logs an error and exits.
    Returns a dictionary of aggregated statistics.
    """
    total_lines = 0
    error_lines = 0
    aggregated = defaultdict(list)
    total_request_count = 0
    total_time = 0.0

    for record in record_iter:
        total_lines += 1
        if record is None:
            error_lines += 1
        else:
            aggregated[record["url"]].append(record["time"])
            total_request_count += 1
            total_time += record["time"]

    if total_lines:
        error_ratio = error_lines / total_lines
        if error_ratio > errors_threshold:
            logging.error(
                "Parsing error ratio %.2f exceeds the allowed threshold %.2f "
                "(errors: %d, total: %d). Aborting.",
                error_ratio,
                errors_threshold,
                error_lines,
                total_lines,
                exc_info=True,
            )
            sys.exit(1)
        else:
            logging.info(
                "Parsing completed. Successfully parsed %d out of %d lines (error ratio: %.2f).",
                total_request_count,
                total_lines,
                error_ratio,
            )
    else:
        logging.error("No lines to parse in the log data.")
        sys.exit(1)

    stats = {}
    for url, times in aggregated.items():
        count = len(times)
        time_sum = sum(times)
        stats[url] = {
            "url": url,
            "count": count,
            "count_perc": (
                round(100.0 * count / total_request_count, 3)
                if total_request_count
                else 0
            ),
            "time_sum": round(time_sum, 3),
            "time_perc": round(100.0 * time_sum / total_time, 3) if total_time else 0,
            "time_avg": round(statistics.mean(times), 3) if times else 0,
            "time_max": round(max(times), 3) if times else 0,
            "time_med": round(statistics.median(times), 3) if times else 0,
        }
    return stats


def process_log_file(latest_log: str, errors_threshold: float) -> dict:
    """
    Reads the log file (using gzip.open if needed), obtains the log data,
    calls the log record generator, and aggregates the records.
    Returns the aggregated statistics dictionary.
    """

    def open_text_file(path: str) -> IO[str]:
        if path.endswith(".gz"):
            binary_stream = cast(IO[bytes], gzip.open(path, "rb"))
            return TextIOWrapper(binary_stream, encoding="utf-8")
        else:
            return open(path, "r", encoding="utf-8")

    try:
        with open_text_file(latest_log) as fp:
            log_data = fp.read()
        record_iter = iter_log_records(log_data)
        return aggregate_records(record_iter, errors_threshold)
    except Exception as e:
        logging.error("Error reading file %s: %s", latest_log, e, exc_info=True)
        sys.exit(1)


# -------------------- REPORT GENERATION --------------------
def generate_report(stats: dict, report_size: int) -> str:
    """
    Generates a JSON report (table data) containing the top report_size URLs,
    sorted in descending order by total request time (time_sum).
    """
    stats_list = list(stats.values())
    stats_sorted = sorted(stats_list, key=lambda d: d["time_sum"], reverse=True)
    top_stats = stats_sorted[:report_size]
    return json.dumps(top_stats, indent=2)


def create_report(
    report_dir: str, report_filename: str, template_path: str, table_json: str
) -> bool:
    """
    Renders the HTML report template with the JSON table by using string.Template
    for substitution, and writes the report file.
    """
    try:
        with open(template_path, "r", encoding="utf-8") as fp:
            template = fp.read()
    except IOError as error:
        logging.error(
            "Can't read template file %s: %s", template_path, error, exc_info=True
        )
        return False

    if not os.path.isdir(report_dir):
        try:
            os.mkdir(report_dir)
        except Exception as e:
            logging.error(
                "Cannot create report directory %s: %s", report_dir, e, exc_info=True
            )
            return False

    report_filepath = os.path.join(report_dir, report_filename)
    try:
        with open(report_filepath, "w", encoding="utf-8") as f_out:
            # Use string.Template to render without manual line iteration.
            f_out.write(Template(template).safe_substitute(table_json=table_json))
        logging.info("Report successfully created: %s", report_filepath)
        return True
    except IOError as error:
        logging.error(
            "Can't write report file %s: %s", report_filepath, error, exc_info=True
        )
        return False


# -------------------- MAIN FUNCTION --------------------
def main():
    parser = argparse.ArgumentParser(
        description="Process nginx logs and generate report"
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG["CONFIG_PATH"],
        help="Path to configuration file",
    )
    args = parser.parse_args()

    config = read_config(args.config)
    setup_logger(config.get("LOG_FILE"), level="info")

    latest_log, latest_date = check_logs(config["LOG_DIR"])
    if not latest_log:
        logging.info("No logs to process in %s", config["LOG_DIR"])
        sys.exit(0)

    # Report filename based on the date in the log file name
    report_filename = f"report-{latest_date}.html"
    report_filepath = os.path.join(config["REPORT_DIR"], report_filename)
    # If the report already exists, do not process again.
    if os.path.exists(report_filepath):
        logging.info("Report already exists: %s. Exiting.", report_filepath)
        sys.exit(0)

    # Allowed error fraction: convert percentage threshold to fraction (e.g., 10 → 0.10)
    errors_threshold = config["ERRORS_THRESHOLD"] / 100.0
    stats_by_url = process_log_file(latest_log, errors_threshold)
    if not stats_by_url:
        logging.error("Failed to compute log statistics.")
        sys.exit(1)

    report_json = generate_report(stats_by_url, config["REPORT_SIZE"])
    if not create_report(
        config["REPORT_DIR"], report_filename, config["TEMPLATE_PATH"], report_json
    ):
        logging.error("Failed to create report file.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.error("Script interrupted by user (KeyboardInterrupt).", exc_info=True)
        sys.exit(1)
    except Exception:
        logging.exception("Unhandled exception occurred:")
        sys.exit(1)
