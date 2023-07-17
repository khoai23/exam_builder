import os, io, csv 
from src.reader import HEADERS, process_field

from typing import Optional, List, Tuple, Any, Union, Dict

def reparse_csv(filepath: str, headers: Optional[List[str]]=None):
    # read a file from `filepath` into a dict. Should at minimum has `question`, `answer1-4`, and `correct_id`
    correct_data, failed_data = [], []
    with io.open(filepath, "r", encoding="utf-8") as rf:
        reader = csv.DictReader(rf, fieldnames=headers)
        for row in reader:
            try:
                process_field(row)
                correct_data.append(row)
            except Exception as e:
                failed_data.append(row)
    base, ext = os.path.splitext(filepath)
    with io.open(base + "_correct" + ext, "w", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=HEADERS + ["explanation", "url"], dialect="unix") 
        writer.writeheader()
        for row in correct_data:
            writer.writerow(row)
    with io.open(base + "_failed" + ext, "w", encoding="utf-8") as ff:
        writer = csv.DictWriter(ff, fieldnames=HEADERS + ["explanation", "url"], dialect="unix") 
        writer.writeheader()
        for row in failed_data:
            writer.writerow(row)
    
if __name__ == "__main__":
    # target = sys.argv[1]
    import sys
    reparse_csv(sys.argv[1])