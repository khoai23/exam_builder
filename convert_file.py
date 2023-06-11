"""Converting file from txt to formatted table.
For now just try to catch keys denoted as A. - D., deciding the cutoff of the D by the amount of endline from prior options."""

import io, re 

from typing import Optional, Dict, List, Tuple, Any, Union, Pattern, IO

def read_and_convert_file(text_filepath: Union[str, IO], **kwargs):
    if(isinstance(text_filepath, str)):
        with io.open(text_filepath, "r", encoding="utf-8") as tf:
            text = tf.read()
    else:
        text = text_filepath.read()
    return read_and_convert(text, **kwargs)

def read_and_convert(text: str, question_cue: Optional[Union[str, Pattern]]=None, answer_cues: List[Union[str, Pattern]]=(r"A\.", r"B\.", r"C\.", r"D\."), keep_question_cue: bool=False, keep_answer_cue: bool=False, question_bw_endline: int=5):
    """Find all possible section, and return data in an iterative manner.
    Data will be re-vetted by an user, so this can have some wiggle room."""
    # find all positions of first answer (A.) in the text 
    first_cue, second_cue, third_cue, fourth_cue = answer_cues
    anchor_indices = [m.start() for m in re.finditer(first_cue, text)]
    endline_indices = [m.start() for m in re.finditer("\n", text)][::-1]
    # start organizing problems right now
    problems = []
    if(question_cue):
        # has cue; search backward from each anchor to get the extend of the questions 
        question_indices = [m.start() if keep_question_cue else m.end() for m in re.finditer(question_cue, text)][::-1]
        # find closest questions to each anchor 
        for aidx in anchor_indices:
            qidx = next((qi for qi in question_indices if qi < aidx), 0)
            problems.append({"question": text[qidx:aidx].strip(), "qidx": qidx, "aidx": aidx})
    else:
        # no cue; search upward until 5 endline text, without encountering any answer cues
        for aidx in anchor_indices:
            prior_endlines = [ei for ei in endline_indices if ei < aidx][::-1][:question_bw_endline]
            if len(prior_endlines) < question_bw_endline:
                # have less than 5, add 0 as first instance 
                prior_endlines.append(0)
            current_qidx = aidx
            for pei in prior_endlines:
                if(any((ac in text[pei:current_qidx] for ac in answer_cues))):
                    # there is an answer cue in this line; do not use 
                    break
                else:
                    # no answer cue; can safely put into 
                    current_qidx = pei 
            # after check, put into the rest
            problems.append({"question": text[current_qidx:aidx].strip(), "qidx": current_qidx, "aidx": aidx})
    # print(problems, anchor_indices, answer_cues)
    # on answers; A. -> C. will be ranged by nearest indices of next question 
    # D. will be decided by maximum num of endline in A., B. and C., minimum to 1
    # print(answer_cues)  
    answer_i1, answer_i2, answer_i3, answer_i4 = answer_indices = [anchor_indices] + [ [m.start() for m in re.finditer(ac, text)] for ac in answer_cues[1:] ]
#    print("Section indices: ",  list(zip(*answer_indices)))
    endline_indices = endline_indices[::-1] # revert back to front-first
    for problem in problems:
        aidx = problem["aidx"]
        # bind nearest i2, i3, i4 to this answer 
        a1_end = a2_start = next((i for i in answer_i2 if i > aidx), None)
        a2_end = a3_start = next((i for i in answer_i3 if i > aidx), None)
        a3_end = a4_start = next((i for i in answer_i4 if i > aidx), None)
        # handle case where 1st and 3rd are on one line, 2nd and 4th on the next (a3_start > a2_start)
        if(a3_start < a2_start):
            a1_end = a3_start; a3_end = a2_start; a2_end = a4_start
        if(a1_end is None or a2_end is None or a3_end is None):
            print("Failed finding endpoint for answer 1/2/3: {} {} {}; aborting for this question".format(a1_end, a2_end, a3_end))
            continue 
        problem.update(answer1=text[aidx:a1_end].strip(), answer2=text[a2_start:a2_end].strip(), answer3=text[a3_start:a3_end].strip())
        # with a1/2/3 regioned; a4 will be decided by the endline 
        max_endline_count = max(1, len(re.findall("\n", problem["answer1"])), len(re.findall("\n", problem["answer2"])), len(re.findall("\n", problem["answer3"])))
        a4_end = None 
        after_a4_endline = (i for i in endline_indices if i > a4_start)
        next_question_index = min((p["qidx"] for p in problems if p["qidx"] > problem["qidx"]), default=len(text))
        for _ in range(max_endline_count):
            endpoint = next(after_a4_endline, None)
            print("Checking endpoint {} for q: {}, qidx {} vs nextqidx {}".format(endpoint, problem["question"], problem["qidx"], next_question_index))
            if(endpoint is None):
                # no more endline after a4; use current 
                break  
            elif(endpoint > next_question_index):
                # ran into next question; breakout 
                break
            a4_end = endpoint 
        problem.update(answer4=text[a4_start:] if a4_end is None else text[a4_start:a4_end])
        
        for aprt, aname in zip(answer_cues, ["answer1", "answer2", "answer3", "answer4"]):
            if(not keep_answer_cue):
                problem[aname] = re.sub(aprt, "", problem[aname])
            problem[aname] = problem[aname].strip()
    return problems
        
blank_regex = "\s{2,}"
if __name__ == "__main__":
    path = "test/test_mini.txt"
    problems = read_and_convert_file(path, question_cue="Câu")
    for p in problems:
        print("Question: " + re.sub(blank_regex, " ", p["question"]).strip())
        print("Answer 1: " + re.sub(blank_regex, " ", p["answer1"]).strip())
        print("Answer 2: " + re.sub(blank_regex, " ", p["answer2"]).strip())
        print("Answer 3: " + re.sub(blank_regex, " ", p["answer3"]).strip())
        print("Answer 4: " + re.sub(blank_regex, " ", p["answer4"]).strip())
        print("------\n\n\n")
