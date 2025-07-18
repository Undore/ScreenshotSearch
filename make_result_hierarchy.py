import asyncio
import json
import os
from logging import Logger

import cv2
import numpy as np
from tqdm import tqdm

from settings import BASE_PATH, LOGGING
from src.logger import init_logger
from src.frame_compiler import FrameCompiler

DIST_BASE_PATH = BASE_PATH


PATH_V2 = False  # Dev tool

def save_result(score: float, original_file_name: str, found_file_name: str, timecode: str, image: np.ndarray):
    if PATH_V2:
        folder_path = os.path.join(DIST_BASE_PATH, 'dist', str(original_file_name), str(score) , str(found_file_name))
    else:
        folder_path = os.path.join(DIST_BASE_PATH, 'dist', str(score), str(original_file_name), str(found_file_name))
    os.makedirs(folder_path, exist_ok=True)

    safe_timecode = timecode.replace(":", "-")
    file_path = os.path.join(folder_path, safe_timecode + '.jpg')

    cv2.imwrite(file_path, image)


logger: Logger = init_logger(LOGGING['main'], "[bold red]\\[CORE][/bold red]")

RESULTS_FILENAME = 'results.cleaned.json'
MIN_SCORE = 0.4

async def main():
    if os.path.exists(os.path.join(DIST_BASE_PATH, 'dist')):
        raise RuntimeError(f"Dist already exists on {BASE_PATH}")

    RESULTS_PARSED_PATH = os.path.join(BASE_PATH, RESULTS_FILENAME)

    logger.info(f"Results file: {RESULTS_PARSED_PATH}")

    with open(RESULTS_PARSED_PATH, 'r') as f:
        results = json.load(f)

    total = sum(len(results[k]) for k in results)
    pbar = tqdm(total=total, desc="Saving matched frames")

    for protocol in results:
        for result in results[protocol]:
            if result['score'] < MIN_SCORE:
                pbar.update()
                continue

            found_path = result['found_path']
            timecode = result['time']

            if not os.path.exists(found_path):
                pbar.update()
                continue

            async with FrameCompiler(found_path) as frame_compiler:
                frame = await asyncio.to_thread(frame_compiler.get_frame_at_time, timecode)
                if frame is None:
                    pbar.update()
                    continue

                save_result(
                    score=round(result['score'], 4),
                    original_file_name=os.path.basename(result['original_path']),
                    found_file_name=os.path.basename(found_path),
                    timecode=timecode,
                    image=np.array(frame)
                )

            pbar.update()

    pbar.close()


asyncio.run(main())
