import asyncio
from datetime import timedelta
from logging import Logger
from typing import Generator

import numpy as np
from PIL import Image
from tqdm import tqdm

from settings import LOGGING, PROTOCOLS
from src.frame_compiler import FrameCompiler
from src.logger import init_logger
from src.match_processor import FrameMatchProcessor


class SearchProcessor:
    logger: Logger = init_logger(LOGGING['search_processor'], "[bold yellow]\[SEARCH-PROCESSOR][/bold yellow]")


    def __init__(self, originals: list[str], comparing: list[str]):
        self.originals = originals
        self.comparing = comparing

    async def search(self) -> Generator[tuple[str, str, str, timedelta], None, None]:
        """
        Search for original/comparing matches and yield every result.

        Yields:
            tuple: (original_path, compare_path, protocol_name, timecode)
        """
        global_pbar = tqdm(
            total=len(self.originals),
            desc="Processing originals"
        )

        for original_path in self.originals:
            self.logger.debug(
                f"Searching original [bold cyan]{original_path.split('/')[-1]}[/bold cyan] for comparisons"
            )

            original = Image.open(original_path)
            original = np.array(original)

            compare_pbar = tqdm(
                total=len(self.comparing),
                desc=f"Searching all comparisons for {original_path.split('/')[-1]}",
                leave=False
            )

            for compare_path in self.comparing:
                self.logger.debug(f"Comparing {compare_path}")

                async with FrameCompiler(compare_path) as frame_compiler:
                    total_frames = frame_compiler.total_frames

                    self.logger.debug(
                        f"Total frames to process: {total_frames} [gray](This will take some time)"
                    )

                    cpath = compare_path.split('/')[-1].split('\\')[-1]
                    frames_pbar = tqdm(
                        total=total_frames,
                        desc=f"Processing frames: {cpath}",
                        leave=False
                    )

                    async for frame_index, frame in frame_compiler.iterate_frames():
                        match_processor = FrameMatchProcessor(original, frame)

                        ssim = PROTOCOLS["ssim"]
                        phash = PROTOCOLS["phash"]
                        template = PROTOCOLS["template"]

                        seconds = frame_index / frame_compiler.fps
                        timecode = timedelta(seconds=seconds)

                        if ssim["use"] and match_processor.compare_ssim(ssim["similarity"]):
                            yield original_path, compare_path, "SSIM", timecode

                        if phash["use"] and match_processor.compare_phash(phash["similarity"]):
                            yield original_path, compare_path, "PHASH", timecode

                        if template["use"] and match_processor.compare_template(template["similarity"]):
                            yield original_path, compare_path, "TEMPLATE", timecode

                        frames_pbar.update()

                    frames_pbar.close()
                compare_pbar.update()
                await asyncio.sleep(1)

            compare_pbar.close()
            global_pbar.update()

        global_pbar.close()