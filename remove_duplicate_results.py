from collections import defaultdict
from datetime import datetime
import os
import json
from tqdm import tqdm

from settings import BASE_PATH, LOGGING
from src.logger import init_logger

logger = init_logger(LOGGING['main'], "[bold red]\\[CORE][/bold red]")

TIME_THRESHOLD_MS = 1000
MIN_SCORE = 0.5
RESULTS_FILENAME = "parsed_results.json"

def parse_time_to_ms(t: str) -> int:
    try:
        t_obj = datetime.strptime(t, "%H:%M:%S.%f")
    except ValueError:
        t_obj = datetime.strptime(t, "%H:%M:%S")
    return int(t_obj.hour * 3600_000 + t_obj.minute * 60_000 + t_obj.second * 1000 + t_obj.microsecond // 1000)

def result_key(result: dict) -> tuple:
    return (
        os.path.basename(result["original_path"]),
        os.path.basename(result["found_path"]),
        result["score_protocol"],
    )

def get_time_ms(result: dict) -> int:
    return parse_time_to_ms(result["time"])

def main():
    RESULTS_PARSED_PATH = os.path.join(BASE_PATH, RESULTS_FILENAME)
    RESULTS_CLEANED_PATH = os.path.join(BASE_PATH, 'results.cleaned.json')

    logger.info(f"Results file: {RESULTS_PARSED_PATH}")
    logger.info(f"Output: results.cleaned.json")

    with open(RESULTS_PARSED_PATH, 'r') as f:
        results = json.load(f)

    total_before = sum(len(results[k]) for k in results)
    pbar = tqdm(total=total_before, desc="Cleaning result duplicates")

    cleaned_results = {}
    duplicates_removed = 0
    low_scores_removed = 0

    for protocol, entries in results.items():
        cleaned = []
        grouped_by_key = defaultdict(list)

        for result in entries:
            if result['score'] < MIN_SCORE:
                pbar.update()
                low_scores_removed += 1
                continue

            grouped_by_key[result_key(result)].append(result)

        for key, group in grouped_by_key.items():
            group.sort(key=lambda r: get_time_ms(r))
            deduped = []

            for r in group:
                time_ms = get_time_ms(r)
                if not deduped:
                    deduped.append(r)
                else:
                    prev = deduped[-1]
                    prev_time_ms = get_time_ms(prev)
                    if abs(time_ms - prev_time_ms) < TIME_THRESHOLD_MS:
                        if r["score"] > prev["score"]:
                            deduped[-1] = r
                            duplicates_removed += 1
                        else:
                            duplicates_removed += 1
                    else:
                        deduped.append(r)

                pbar.update()

            cleaned.extend(deduped)

        cleaned_results[protocol] = cleaned

    pbar.close()

    total_after = sum(len(cleaned_results[k]) for k in cleaned_results)

    with open(RESULTS_CLEANED_PATH, 'w') as f:
        json.dump(cleaned_results, f, indent=4)

    logger.info(f"Deleted duplicates: {duplicates_removed}")
    logger.info(f"Cleaned low scores: {low_scores_removed}")
    logger.info(f"Unique frames left: {total_after}")
    logger.info(f"Dist: {RESULTS_CLEANED_PATH}")

if __name__ == '__main__':
    main()
