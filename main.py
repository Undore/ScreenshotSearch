import asyncio
import json
import os.path
from logging import Logger

from settings import LOGGING, ORIGINALS_FOLDER_NAME, BASE_PATH, COMPARING_FOLDER_NAME, MAX_WORKERS
from src.folder_reader import FolderReader
from src.logger import init_logger
from src.search_processor import SearchProcessor


logger: Logger = init_logger(LOGGING['main'], "[bold red]\[CORE][/bold red]")

async def main():
    logger.info("[bold cyan]Initializing")

    ORIGINALS_FOLDER = os.path.join(BASE_PATH, ORIGINALS_FOLDER_NAME)
    COMPARING_FOLDER = os.path.join(BASE_PATH, COMPARING_FOLDER_NAME)

    os.makedirs(ORIGINALS_FOLDER, exist_ok=True)
    os.makedirs(COMPARING_FOLDER, exist_ok=True)

    ORIGINALS: list[str] = FolderReader.walk_files(ORIGINALS_FOLDER)
    COMPARING: list[str] = FolderReader.walk_files(COMPARING_FOLDER)

    logger.info(f"Found {len(ORIGINALS)} originals files")
    logger.info(f"Found {len(COMPARING)} comparing files")

    logger.info("[bold yellow]Starting search")


    async def search(worker_id, worker_originals, worker_comparing) -> dict:
        if not any((worker_originals, worker_comparing)):
            return

        worker_results = {}
        search_engine = SearchProcessor(worker_originals, worker_comparing)

        async for result in search_engine.search():
            original_file, comparing_file, protocol, timecode = result

            if worker_results.get(original_file):
                if timecode.seconds in [i[3].seconds for i in worker_results[original_file]]:
                    continue

                worker_results[original_file].append((*result, worker_id))
                continue

            worker_results[original_file] = [(*result, worker_id)]

        return worker_results

    originals_per_worker = len(ORIGINALS) // MAX_WORKERS
    originals_overflow = len(ORIGINALS) % MAX_WORKERS

    workers = []
    originals_offset = 0

    worker_id = 0
    for worker_id in range(MAX_WORKERS):
        workers.append(search(worker_id, ORIGINALS[originals_offset:originals_offset + originals_per_worker], COMPARING))
        originals_offset += originals_per_worker

    if originals_overflow > 0:
        workers.append(search(worker_id + 1, ORIGINALS[originals_offset:originals_offset + originals_overflow], COMPARING))

    results: list[dict] = await asyncio.gather(*workers)

    all_results = []
    for worker_result in results:
        if not worker_result:
            continue
        for original_path, founds in worker_result.items():
            for (orig, found_path, protocol, timecode, worker_id) in founds:
                all_results.append({
                    "original_path": original_path,
                    "found_path": found_path,
                    "time": str(timecode),
                    "protocol": protocol,
                    "worker_id": worker_id
                })

    with open("results.json", "w+", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=4)

    logger.info("[bold green]Done! Results saved to results.json[/bold green]")

asyncio.run(main())
