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
        Search for original/comparing matches and yield every result

        Yields a tuple of [original, foundComparison, usedProtocol, comparisonTimeCode]

        :return: a generator
        """
        # search_bar = tqdm(total=len(self.originals), desc=f"Processing search")

        for original_path in self.originals:
            self.logger.debug(f"Searching original [bold cyan]{original_path.split('/')[-1]}[/bold cyan] for comparisons")

            original_pbar = tqdm(total=len(self.originals), desc=f"Processing search: {original_path}")

            original = Image.open(original_path)
            original = np.array(original)

            for compare_path in self.comparing:
                self.logger.debug(f"Comparing {compare_path}")

                async with FrameCompiler(compare_path) as frame_compiler:
                    frame_compiler: FrameCompiler
                    total_frames = frame_compiler.total_frames

                    self.logger.debug(f"Total frames to process: {total_frames} [gray](This will take some time)")

                    frames_pbar = tqdm(total=total_frames, desc=f"Processing comparison {compare_path}", leave=False)

                    async for frame_index, frame in frame_compiler.iterate_frames():
                        match_processor = FrameMatchProcessor(original, frame)

                        ssim = PROTOCOLS['ssim']
                        phash = PROTOCOLS['phash']
                        template = PROTOCOLS['template']

                        seconds = frame_index / frame_compiler.fps
                        timecode = timedelta(seconds=seconds)

                        if ssim['use'] and match_processor.compare_ssim(ssim['similarity']):
                            yield original_path, compare_path, "SSIM", timecode

                        if phash['use'] and match_processor.compare_phash(ssim['similarity']):
                            yield original_path, compare_path, "PHASH", timecode

                        if template['use'] and match_processor.compare_template(template['similarity']):
                            yield original_path, compare_path, "TEMPLATE", timecode

                        frames_pbar.update()

                frames_pbar.close()
                original_pbar.update()
                await asyncio.sleep(1)

            # original_pbar.close()