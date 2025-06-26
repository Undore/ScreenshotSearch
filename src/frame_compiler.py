from functools import cached_property
from logging import Logger
from typing import Generator

import cv2
import numpy as np

from settings import LOGGING
from src.logger import init_logger


class FrameCompiler:
    """
    Frame compiler class splits given video into frames and stores them in a temp folder.
    Use only with async context (async with)
    """

    logger: Logger = init_logger(LOGGING['frame_compiler'], "[cyan]\[FRAME-COMPILER][/cyan]")

    vidcap: cv2.VideoCapture

    def __init__(self, video_path: str):
        self.video_path = video_path

    async def __aenter__(self):
        self.vidcap = cv2.VideoCapture(self.video_path)

        self.logger.debug(f"[bold green]Compiler initialized for video {self.video_path}")
        return self


    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    @cached_property
    def total_frames(self):
        return int(self.vidcap.get(cv2.CAP_PROP_FRAME_COUNT))

    @cached_property
    def fps(self):
        return self.vidcap.get(cv2.CAP_PROP_FPS)

    async def iterate_frames(self) -> Generator[tuple[int, np.array], None, None]:
        """
        Iterate video frames.
        Yields a tuple of [frameNumber, frameArray]
        :return: Generator
        """

        success, frame = self.vidcap.read()
        frame_count = 0

        while success:
            frame_count += 1

            yield frame_count, frame

            success, frame = self.vidcap.read()
