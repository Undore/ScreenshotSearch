import asyncio
import json
import os
from logging import Logger
from datetime import datetime

import cv2
from tqdm import tqdm

from settings import BASE_PATH, LOGGING
from src.logger import init_logger

logger: Logger = init_logger(LOGGING['main'], "[bold cyan]\\[SIZE][/bold cyan]")

def parse_time(t: str) -> float:
    try:
        t_obj = datetime.strptime(t, "%H:%M:%S.%f")
    except ValueError:
        t_obj = datetime.strptime(t, "%H:%M:%S")
    return t_obj.hour * 3600 + t_obj.minute * 60 + t_obj.second + (t_obj.microsecond / 1e6)

def sync_get_frame_size(video_path: str, timecode: str) -> int:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return 0

    seconds = parse_time(timecode)
    cap.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
    success, frame = cap.read()
    cap.release()

    if not success or frame is None:
        return 0

    height, width, channels = frame.shape
    return height * width * channels

from asyncio.exceptions import TimeoutError

async def estimate_size(entry: dict, min_score: float, semaphore: asyncio.Semaphore, progress_callback) -> int:
    score = entry.get('score', 0)
    if score < min_score:
        progress_callback()
        return 0

    video_path = entry['found_path']
    timecode = entry['time']

    async with semaphore:
        try:
            size = await asyncio.wait_for(
                asyncio.to_thread(sync_get_frame_size, video_path, timecode),
                timeout=5  # секунд
            )
        except TimeoutError:
            logger.warning(f"Timeout on file: {video_path} at {timecode}")
            size = 0
        except Exception as e:
            logger.warning(f"Error on file {video_path}: {e}")
            size = 0

    progress_callback()
    return size


RESULTS_FILENAME = 'parsed_results.json'
async def main(min_score: float = 0.4, max_concurrency: int = 12):
    results_path = os.path.join(BASE_PATH, RESULTS_FILENAME)

    with open(results_path, 'r') as f:
        results = json.load(f)

    all_entries = [res for protocol in results.values() for res in protocol]
    total_files = len(all_entries)

    pbar = tqdm(total=total_files, desc="Estimating result size")
    semaphore = asyncio.Semaphore(max_concurrency)

    total_estimated_size = 0
    skipped = 0

    def progress():
        pbar.update()

    tasks = [
        estimate_size(entry, min_score, semaphore, progress)
        for entry in all_entries
    ]

    sizes = await asyncio.gather(*tasks)

    total_estimated_size = sum(sizes)
    total_passed = sum(1 for s in sizes if s > 0)
    skipped = total_files - total_passed

    pbar.close()

    estimated_mb = total_estimated_size / (1024 * 1024)
    logger.info(f"Total estimated files: {total_passed}")
    logger.info(f"Skipped (score < {min_score} or read error): {skipped}")
    logger.info(f"Approx. total size: {estimated_mb:.2f} MB")

asyncio.run(main(min_score=0.45, max_concurrency=12))
