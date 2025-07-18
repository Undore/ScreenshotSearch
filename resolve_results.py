import asyncio
import json
import os
from logging import Logger

import cv2
import numpy as np
from tqdm import tqdm

from src.folder_reader import FolderReader
from src.frame_compiler import FrameCompiler
from src.logger import init_logger
from settings import BASE_PATH, LOGGING, ORIGINALS_FOLDER_NAME, COMPARING_FOLDER_NAME, PROTOCOLS
from src.match_processor import FrameMatchProcessor

logger: Logger = init_logger(LOGGING['main'], "[bold red]\\[CORE][/bold red]")

async def process_result(result: dict) -> list[dict]:
    ORIGINAL = result['original_path']
    FOUND_VIDEO = result['found_path']
    TIMECODE = result['time']

    if result.get('score'):  # No need to process the result if already processed before
        return [result]

    if not os.path.exists(FOUND_VIDEO) or not os.path.exists(ORIGINAL):
        return []

    async with FrameCompiler(FOUND_VIDEO) as frame_compiler:
        frame = await asyncio.to_thread(frame_compiler.get_frame_at_time, TIMECODE)
        frame = np.array(frame)

    original_frame = await asyncio.to_thread(cv2.imread, ORIGINAL)
    if original_frame is None:
        return []

    match_processor = FrameMatchProcessor(original_frame, frame)

    score: dict[str,  float | None] = {
        "SSIM": None,
        "PHASH": None,
        "TEMPLATE": None,
    }

    if PROTOCOLS["ssim"]["use"]:
        score["SSIM"] = await asyncio.to_thread(
            match_processor.compare_ssim,
            PROTOCOLS["ssim"]["similarity"],
            True
        )
    if PROTOCOLS["phash"]["use"]:
        score["PHASH"] = await asyncio.to_thread(
            match_processor.compare_phash,
            PROTOCOLS["phash"]["similarity"],
            True
        )
    if PROTOCOLS["template"]["use"]:
        score["TEMPLATE"] = await asyncio.to_thread(
            match_processor.compare_template,
            PROTOCOLS["template"]["similarity"],
            True
        )

    output = []
    for k, v in score.items():
        if v is None:
            continue
        r = result.copy()
        r["score"] = v
        r["score_protocol"] = k
        output.append(r)

    return output

RESULTS_FILENAME = "results.json"

async def main():
    logger.info("[bold cyan]Initializing result resolver")

    RESULTS_PATH = os.path.join(BASE_PATH, RESULTS_FILENAME)

    logger.info(f"Results file: {RESULTS_PATH}")
    logger.info(f"Output: parsed_results.json")

    if not os.path.exists(RESULTS_PATH):
        logger.error(f"Result file not found in {RESULTS_PATH}")
        exit()

    with open(RESULTS_PATH, "r") as f:
        results: list[dict] = json.load(f)

    logger.info(f"Found {len(results)} results")
    logger.debug("Converting paths")

    fixed_results = []
    for result in results:
        if not os.path.exists(result["original_path"]):
            result["original_path"] = os.path.join(
                BASE_PATH,
                FolderReader.convert_path(ORIGINALS_FOLDER_NAME, result["original_path"])
            )
        if not os.path.exists(result["found_path"]):
            result["found_path"] = os.path.join(
                BASE_PATH,
                FolderReader.convert_path(COMPARING_FOLDER_NAME, result["found_path"])
            )
        fixed_results.append(result)

    results = fixed_results.copy()

    logger.debug("[green]Paths converted successfully")

    logger.info("[cyan]Comparing search results (This will take a while)")

    sem = asyncio.Semaphore(4)

    async def limited_task(r):
        async with sem:
            return await process_result(r)

    tasks = [limited_task(r) for r in results]

    all_results = []
    for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Processing results"):
        res = await coro
        all_results.extend(res)

    compared_results = {}
    for item in all_results:
        protocol = item["score_protocol"]
        compared_results.setdefault(protocol, []).append(item)

    logger.info("[green]Comparing search results finished successfully. Dumping results")

    with open("parsed_results.json", "w+") as f:
        json.dump(compared_results, f, indent=4)

    logger.info("[green]Done!")

asyncio.run(main())
