import asyncio
import json
import os.path
from logging import Logger

from settings import LOGGING, ORIGINALS_FOLDER_NAME, BASE_PATH, COMPARING_FOLDER_NAME
from src.folder_reader import FolderReader
from src.logger import init_logger
from src.search_processor import SearchProcessor


logger: Logger = init_logger(LOGGING['main'], "[bold red]\\[CORE][/bold red]")

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

    search_engine = SearchProcessor(ORIGINALS, COMPARING)

    results = {}
    async for result in search_engine.search():
        original_file, comparing_file, protocol, timecode = result

        if results.get(original_file):
            if timecode.seconds in [i[3].seconds for i in results[original_file]]:
                continue

            results[original_file].append(result)
            continue

        results[original_file] = [result]

    all_results = []
    for original_path, founds in results.items():
        for orig, found_path, protocol, timecode in founds:
            all_results.append({
                "original_path": original_path,
                "found_path": found_path,
                "time": str(timecode),
                "protocol": protocol
            })

    with open("results.json", "w+", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=4)

    logger.info("[bold green]Done! Results saved to results.json[/bold green]")


asyncio.run(main())
