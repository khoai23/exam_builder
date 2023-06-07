"""
Basic code to read data from a csv file.
"""
import io, csv 

from typing import Optional, List, Tuple, Any, Union

DEFAULT_FILE_PATH = "test/sample.csv"

def read_file(filepath: str, headers: Optional[List[str]]=None, strict: bool=False):
    # read a file from `filepath` into a dict. Should at minimum has `question`, `answer1-4`, and `correct_id`
    data = []
    with io.open(filepath, "r") as rf:
        reader = csv.DictReader(rf, fieldnames=headers)
        for row in reader:
            data.append(process_field(row))
    if(strict):
        fields = ("question", "correct_id", "answer1", "answer2", "answer3", "answer4")
        valid_data = lambda row: all(field in row for field in fields)
        assert all(valid_data(row) for row in data), "Read data missing field; exiting: {}".format(data)
    return data

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
            # if has tag for multiple choice, swap it to is_multiple_choice
            if("is_multiple_choice" in v):
                v.remove("is_multiple_choice")
                new_data["is_multiple_choice"] = True 
            if("is_dynamic_key" in v):
                v.remove("is_dynamic_key")
                new_data["is_dynamic_key"] = True 
            elif("is_fixed_equation" in v):
                v.remove("is_fixed_equation")
                new_data["is_fixed_equation"] = True
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
    assert len(set(answers)) == len(answers), "There are duplicates in the list of answers of: {}".format(new_data)
    # if multiple-choice question with only a single selection, convert it to list 
    if(new_data["is_multiple_choice"] and isinstance(new_data["correct_id"], int)):
        new_data["correct_id"] = (new_data["correct_id"],)
    return new_data

if __name__ == "__main__":
    print(read_file("test/sample.csv"))
