"""
Basic code to read data from a csv file.
"""
import io, csv 
import openpyxl

from typing import Optional, List, Tuple, Any, Union

DEFAULT_FILE_PATH = "test/sample.xlsx"

def read_file(filepath: str, headers: Optional[List[str]]=None, strict: bool=False):
    if(".csv" in filepath):
        return read_file_csv(filepath, headers=headers, strict=strict)
    elif(".xlsx" in filepath):
        return read_file_xlsx(filepath, headers=headers, strict=strict)
    else:
        raise ValueError("Unusable filepath: {}; check the extension (must be .csv/.xlsx)".format(filepath))

def read_file_csv(filepath: str, headers: Optional[List[str]]=None, strict: bool=False):
    # read a file from `filepath` into a dict. Should at minimum has `question`, `answer1-4`, and `correct_id`
    data = []
    with io.open(filepath, "r", encoding="utf-8") as rf:
        reader = csv.DictReader(rf, fieldnames=headers)
        for row in reader:
            data.append(process_field(row))
    if(strict):
        fields = ("question", "correct_id", "answer1", "answer2", "answer3", "answer4")
        valid_data = lambda row: all(field in row for field in fields)
        assert all(valid_data(row) for row in data), "Read data missing field; exiting: {}".format(data)
    return data

def read_file_xlsx(filepath: str, headers: Optional[List[str]]=None, strict: bool=False):
    workbook = openpyxl.load_workbook(filepath)
    data_sheet = workbook[workbook.sheetnames[0]]
    print("Expecting the first sheet to contain the data; which is: {}".format(workbook.sheetnames[0]))
    data = []
    for i, row in enumerate(data_sheet.iter_rows(values_only=True)):
        if(i == 0 and headers is None):
            # if header is None, load it from the excel 
            headers = row;
            continue 
        # only add the data field in when value is not empty 
        # have to re-convert back to string right now; TODO code to skip this
        data.append(process_field({header: str(value) for header, value in zip(headers, row) if value is not None }))
    if(strict):
        fields = ("question", "correct_id", "answer1", "answer2", "answer3", "answer4")
        valid_data = lambda row: all(field in row for field in fields)
        assert all(valid_data(row) for row in data), "Read data missing field; exiting: {}".format(data)
    return data

SPECIAL_TAGS = ["is_multiple_choice", "is_dynamic_key", "is_fixed_equation", "is_single_equation"]
def process_field(row, lowercase_field: bool=True, delimiter: str=","):
    """All processing of fields is done here."""
    new_data = {"is_multiple_choice": False}
    for k, v in row.items():
        v = v.strip()
        if(lowercase_field):
            k = k.lower()
        if(k == "tag"):
            # for tag field, split it by delimiter 
            v = [] if v == "" else [v.strip()] if delimiter not in v else [t.strip() for t in v.split(delimiter)]
#            print("Tag: ", v)
            # backward compatibility
            for st in SPECIAL_TAGS:
                if(st in v):
                    v.remove(st)
                    new_data[st] = True
        if(k == "special"):
            # if has tag for multiple choice, swap it to is_multiple_choice
            # TODO enforce mutual exclusivity
            for st in SPECIAL_TAGS:
                if(st in v):
                    new_data[st] = True
        if(k == "correct_id"): 
            try:
                if("," in v):
                    new_data["is_multiple_choice"] = True 
                    v = tuple(int(iv) for iv in v.split(","))
                    assert all(( 0 < iv <= 4 for iv in v)), "Correct_id is fixed to [1, 4] for now, but received: {}".format(v)
                else:
                    v = int(v)
                    assert 0 < v <= 4, "Correct_id is fixed to [1, 4] for now, but received: {}".format(v)
            except ValueError as e:
                print("The correct id `{}` cannot be parsed".format(v))
                raise e
        new_data[k] = v
    # assert no duplicate answers.
    answers = [v for k, v in new_data.items() if "answer" in k]
    # fixed equation only has answer1; TODO if there is answer2/3/4 then fire a warning
    assert new_data.get("is_single_equation", False) or len(set(answers)) == len(answers), "There are duplicates in the list of answers of: {}".format(new_data)
    # if multiple-choice question with only a single selection, convert it to list 
    if(new_data["is_multiple_choice"] and isinstance(new_data["correct_id"], int)):
        new_data["correct_id"] = (new_data["correct_id"],)
    return new_data

if __name__ == "__main__":
    print(read_file("test/sample.xlsx"))
