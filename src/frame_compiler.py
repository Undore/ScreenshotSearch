import base64
import os.path
import re
import shutil
from datetime import datetime
from functools import cached_property
from logging import Logger
from typing import Generator, AsyncGenerator, Any

import cv2
import numpy as np
from PIL import Image
from tqdm import tqdm

from settings import LOGGING, BUFFER_IMAGES, BASE_PATH, CLEAR_TEMP
from src.logger import init_logger


class FrameCompiler:
    """
    Frame compiler class splits given video into frames and stores them in a temp folder.
    Use only with async context (async with)
    """

    logger: Logger = init_logger(LOGGING['frame_compiler'], "[cyan]\[FRAME-COMPILER][/cyan]")

    vidcap: cv2.VideoCapture
    temp_path: str

    def __init__(self, video_path: str):
        self.video_path = video_path

    async def __aenter__(self):
        self.vidcap = cv2.VideoCapture(self.video_path)

        self.temp_path = os.path.join(BASE_PATH, 'temp')
        os.makedirs(self.temp_path, exist_ok=True)
        await self.clear_temp()

        if BUFFER_IMAGES:
            await self.buffer_frames()

        self.logger.debug(f"[bold green]Compiler initialized for video {self.video_path}")
        return self


    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.clear_temp()
        return None

    @cached_property
    def total_frames(self):
        return int(self.vidcap.get(cv2.CAP_PROP_FRAME_COUNT))

    @cached_property
    def fps(self):
        return self.vidcap.get(cv2.CAP_PROP_FPS)

    async def clear_temp(self):
        if not CLEAR_TEMP:
            return

        self.logger.debug("Clearing temp files")
        shutil.rmtree(self.temp_path)

    def encode_path(self, path: str) -> str:
        """
        Encode path to safe B64
        :param path: Path to encode
        :return: OS Safe B64 String
        """
        path_bytes = path.encode()
        b64 = base64.urlsafe_b64encode(path_bytes).decode('ascii').rstrip('=')
        return b64

    def decode_path(self, encoded: str) -> str:
        """
        Decode B64 path
        :param encoded: Encoded OS Safe path
        :return: Decoded full path
        """
        padding = '=' * (-len(encoded) % 4)
        encoded_padded = encoded + padding
        path_bytes = base64.urlsafe_b64decode(encoded_padded)
        return path_bytes.decode()


    async def buffer_frames(self) -> None:
        """
        Buffer all frames to the temp dir
        :return: None
        """
        buffering_pbar = tqdm(total=self.total_frames,
                              desc=f"Buffering frames",
                              leave=False)
        safe_path = self.encode_path(self.video_path)
        path = os.path.join(self.temp_path, safe_path)

        if os.path.exists(path):
            if len(os.listdir(path)) >= self.total_frames:
                return

            self.logger.debug(f"[bold yellow]Detected existing buffer, but not frames are captured. Removing tree ({path})")
            shutil.rmtree(path)

        findx = -1
        async for findx, frame in self.read_frames():
            os.makedirs(path, exist_ok=True)
            frame_path = os.path.join(path, f"frame_{findx:06d}.jpg")

            image = Image.fromarray(frame)
            try:
                image.save(frame_path, format="JPEG", quality=85)
            except OSError as e:
                if e.errno == 28:
                    self.logger.error(f"[bold red]Not enough space on disk! Unable to use buffer for {self.video_path}")
                    shutil.rmtree(path)
                    return
                else:
                    raise
            buffering_pbar.update()

        buffering_pbar.close()
        self.logger.debug(f"Buffered {findx + 1} frames successfully")

    async def read_buffer(self):
        """
        Read and iterate buffered frames if available
        Yields a tuple of [frameNumber, frameArray]
        :return: Generator
        """
        buffering_path = os.path.join(self.temp_path, self.encode_path(self.video_path))
        if not os.path.exists(buffering_path):
            self.logger.warning(f"No buffer found for {self.video_path}. Reading frames")
            async for fix, f in self.read_frames():
                yield fix, f
            return

        self.logger.debug("Yielding buffered frames")

        files = [f for f in os.listdir(buffering_path) if f.endswith('.jpg')]

        def extract_frame_number(filename: str) -> int:
            match = re.search(r'(\d+)', filename)
            return int(match.group(1)) if match else -1

        files.sort(key=extract_frame_number)

        for filename in files:
            frame_number = int(re.search(r'(\d+)', filename).group(1))
            file_path = os.path.join(buffering_path, filename)

            image = Image.open(file_path).convert("RGB")
            frame_array = np.array(image)

            yield frame_number, frame_array

    async def read_frames(self):
        """
        Read and iterate video frames.
        Does not use buffering
        Yields a tuple of [frameNumber, frameArray]
        :return: Generator
        """

        success, frame = self.vidcap.read()
        frame_count = 0

        while success:
            frame_count += 1

            yield frame_count, frame

            success, frame = self.vidcap.read()

    async def iterate_frames(self) -> AsyncGenerator[tuple[Any, Any], None]:
        """
        Iterate video frames.
        Use buffering if enabled in settings.
        Yields a tuple of [frameNumber, frameArray]
        :return: Generator
        """

        if BUFFER_IMAGES:
            coro = self.read_buffer()
        else:
            coro = self.read_frames()

        async for fi, f in coro:
            yield fi, f

    def get_frame_at_time(self, time_str: str) -> np.ndarray:
        """
        Get frame at specific timecode.

        :param time_str: Time string, e.g. "0:00:09.080000"
        :return: Frame as ndarray
        """
        if not self.vidcap.isOpened():
            raise RuntimeError(f"Video {self.video_path} is not opened")

        try:
            if '.' in time_str:
                dt = datetime.strptime(time_str, "%H:%M:%S.%f")
            else:
                dt = datetime.strptime(time_str, "%H:%M:%S")
        except ValueError:
            raise ValueError(f"Invalid time format: {time_str}")

        total_seconds = dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1_000_000

        frame_index = int(round(total_seconds * self.fps))

        if frame_index >= self.total_frames:
            frame_index = self.total_frames - 1

        self.vidcap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

        success, frame = self.vidcap.read()
        if not success:
            raise RuntimeError(f"Could not read frame at {time_str} (frame {frame_index})")

        return frame
