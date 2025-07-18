import os

ORIGINALS_FOLDER_NAME = "samples"
COMPARING_FOLDER_NAME = "video"

LOGGING = {
    "frame_compiler": "INFO",
    "match_processor": "INFO",
    "search_processor": "INFO",
    "main": "DEBUG"
}

BUFFER_IMAGES = False  # Store all frames in a temp folder before scanning
CLEAR_TEMP = False #  Clear cache after exiting

PROTOCOLS = {
    "ssim": {
        "similarity": 0.95,
        "use": False
    },
    "phash": {
        "similarity": 0.95,
        "use": False
    },
    "template": {
        "similarity": 0.395,
        "use": True
    }
}


BASE_PATH = os.path.abspath(os.path.dirname(__file__))