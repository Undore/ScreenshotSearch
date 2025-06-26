import os

ORIGINALS_FOLDER_NAME = "samples"
COMPARING_FOLDER_NAME = "anime"

LOGGING = {
    "frame_compiler": "INFO",
    "match_processor": "INFO",
    "search_processor": "INFO",
    "main": "DEBUG"
}

MAX_WORKERS = 10

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