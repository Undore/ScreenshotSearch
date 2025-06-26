from logging import Logger

import cv2
import imagehash
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

from settings import LOGGING
from src.logger import init_logger


class FrameMatchProcessor:
    logger: Logger = init_logger(LOGGING['match_processor'], "[bold magenta]\[MATCH-PROCESSOR][/bold magenta]")

    def __init__(self, original: np.array, comparing: np.array):
        self.original: np.array = original
        self.comparing: np.array = comparing


    def compare_ssim(self, similarity: float = 0.95) -> bool:
        """
        Compare instance frames using SSIM
        :param similarity: How similar frames should be to return True
        :return: True if matching, False if not
        """
        # Resize to same shape
        h, w = self.original.shape[:2]
        comparing_resized = cv2.resize(self.comparing, (w, h))

        gray_original = cv2.cvtColor(self.original, cv2.COLOR_BGR2GRAY)
        gray_comparing = cv2.cvtColor(comparing_resized, cv2.COLOR_BGR2GRAY)

        score, _ = ssim(gray_original, gray_comparing, full=True)

        self.logger.debug(f"SSIM score: {score:.2f}")

        return score >= similarity

    def compare_phash(self, similarity: float = 0.95) -> bool:
        """
        Compare instance frames using PHash
        :param similarity: How similar frames should be to return True
        :return: True if similar
        """
        img1 = Image.fromarray(cv2.cvtColor(self.original, cv2.COLOR_BGR2RGB))
        img2 = Image.fromarray(cv2.cvtColor(self.comparing, cv2.COLOR_BGR2RGB))

        hash1 = imagehash.phash(img1)
        hash2 = imagehash.phash(img2)

        max_distance = 64
        threshold_distance = max_distance * (1 - similarity)

        self.logger.debug(f"PHash score: {(hash1 - hash2)} out of {threshold_distance} ({round((hash1 - hash2) / threshold_distance, 2):.2f}%)")

        return (hash1 - hash2) <= threshold_distance

    def compare_template(self, threshold: float = 0.9) -> bool:
        """
        Match a template image inside a larger frame.
        :param threshold: Similarity threshold [0..1]
        :return: True if match found
        """
        frame_gray = cv2.cvtColor(self.comparing, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(self.original, cv2.COLOR_BGR2GRAY)

        res = cv2.matchTemplate(frame_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        self.logger.debug(f"Template match score: {max_val:.2f}")

        return max_val >= threshold
