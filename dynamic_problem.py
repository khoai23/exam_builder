"""
Formatting and handling dynamic problem 
Dynamic problems come in two forms:
- fixed_equation: in which results are calculateable, hence allowing a generating mechanism to continuously yielding completely different problems
- dynamic_key: in which keys can be interchanged (e.g ABC vs CDE) 
"""
import re
import random
import ast

from typing import Optional, List, Tuple, Any, Union, Dict

VALID_ALPHABET_KEY = "ABCDEFGHIJKLMNOPQRSTUWVZ"
alphabet_regex = re.compile(r"{alpha_\d}")
def convert_dynamic_key_problem(problem: Dict, generator_mode=False):
    """Designated alphabet format (e.g geometric) will be `{alpha_n}`, n ranging from 0 to 9
        generator_mode: if true, this function will act as a generator"""
    # find all instance of keys
    all_alphabet = set(re.findall(alphabet_regex, problem["question"]))
    assert len(all_alphabet) > 0, "Dynamic key problem must have at least one {alpha_n} key"
    # match random alphabet to each of possible key 
    # TODO generator mode
    matcher = {k: v for k, v in zip(list(all_alphabet), random.sample(VALID_ALPHABET_KEY, len(all_alphabet)))}
    # create a version with substitution
    new_problem = dict(problem)
    for field in ["question", "answer1", "answer2", "answer3", "answer4"]:
        for plh, rpl in matcher.items(): # placeholder & replacement 
            new_problem[field] = new_problem[field].replace(plh, rpl)
    return new_problem

var_exp_regex = re.compile(r"{(.+?)}")
def convert_fixed_equation_problem(problem: Dict, separator="|||", generator_mode=False):
    """Designated fixed-equation format (e.g algebraic) will be `{variable}` and `{expression}` with the same 4 answers format, expression can only uses the designated variables.
    Currently enforced listing all variables at the start of the question; separated by "|||".
    TODO catch variables dynamically instead
        generator_mode: see above"""
    # find all instances of curly brackets 
    variable_section, question_section = problem["question"].split(separator)
    answer_section = "\n".join(problem["answer{}".format(i)] for i in range(1, 5))
    variables = set([catch for catch in re.findall(var_exp_regex, variable_section)])
    expressions = set([catch for catch in re.findall(var_exp_regex, question_section + "\n" + answer_section)])
    # assign value to variables; TODO add value designation (e.g x_int, y_square_int, z_prime etc.)
    assigned_variables = {k: random.randint(1, 100) for k in variables}
    # TODO enforce expression type
    assigned_expressions = {("{" + exp + "}"): str(eval(exp, None, assigned_variables)) for exp in expressions}
    # replace all the assigned expression with transfered values 
    new_problem = dict(problem)
    for field in ["question", "answer1", "answer2", "answer3", "answer4"]:
        if(field == "question"):
            new_problem[field] = question_section # remove the front half
        for plh, rpl in assigned_expressions.items(): # placeholder & replacement 
            new_problem[field] = new_problem[field].replace(plh, rpl)
    return new_problem

def convert_single_equation_problem(problem: Dict, separator="|||", generator_mode=True):
    """Designated single-equation format (e.g chemistry), will have similar format for fixed_equation; except that only have one correct answer by expression. Use 4 different variable formats & generator mode by default."""
    variable_section, question_section = problem["question"].split(separator)
    variables = set([catch for catch in re.findall(var_exp_regex, variable_section)])
    # answer1 will contain the correct expression
    answer_section = problem["answer1"]
    expressions = set([catch for catch in re.findall(var_exp_regex, question_section + "\n" + answer_section)])
    assert any((exp in answer_section for exp in expressions)), "Single-equation question {} had an invalid (immutable) correct answer {}".format(problem, answer_section)
    # assign value to variables in four-tuple 
    four_problems = [dict(problem) for _ in range(4)]
    i = 0
    while i < 4: # this to allow rerolling variables; in case where generated result ran into duplication
        assigned_variables = {k: random.randint(1, 100) for k in variables}
        assigned_expressions = {("{" + exp + "}"): str(eval(exp, None, assigned_variables)) for exp in expressions}
        # format for corresponding problem and id 
        asw_i = answer_section
        for plh, rpl in assigned_expressions.items(): # placeholder & replacement 
            asw_i = asw_i.replace(plh, rpl)
        # check duplication 
        # can probably ignore answer1 anyway; TODO ensure answer1 has a valid expression or this will be in a permanent loop
        if(any(asw_i == used_asw for used_asw in [v for k, v in four_problems[i].items() if "answer" in k])):
            print("Made a duplicate answer: {}; retrying".format(asw_i))
            continue
        four_problems[i]["question"] = question_section # remove the front half
        for plh, rpl in assigned_expressions.items(): # placeholder & replacement 
            four_problems[i]["question"] = four_problems[i]["question"].replace(plh, rpl)
        for p in four_problems: # write to same answer id; doesn't matter as it's shuffled anyway
            p["answer{}".format(i+1)] = asw_i
        # problem [i] will be has this as the correct answer
        four_problems[i]["correct_id"] = i+1 
        # increment after everything
        i += 1
    if(generator_mode): # on generator, return four variants sequentially
        for p in four_problems:
            yield p
        return 
    else:
        return four_problems[0]  # on non-generator; just pump out one

if __name__ == "__main__":
    # test conversion 
    test_question_dynamic = {
        "question": "Test question dynamic: Triangle {alpha_0}{alpha_1}{alpha_2} has {alpha_3} as the middle point of {alpha_1}{alpha_2}. The median line would be",
        "answer1": "{alpha_0}{alpha_3}",
        "answer2": "{alpha_1}{alpha_3}",
        "answer3": "{alpha_0}{alpha_1}",
        "answer4": "{alpha_0}{alpha_2}"
    }
    print(convert_dynamic_key_problem(test_question_dynamic))
    test_question_variable = {
        "question": r"{x}{y}|||Test question variable: {x}*{y} = {x*y}, hence {x}/{y}=?",
        "answer1": "{x}",
        "answer2": "{y}",
        "answer3": r"{y/x}",
        "answer4": r"{x/y}"
    }
    print(convert_fixed_equation_problem(test_question_variable))
    test_question_single = {
        "question": r"{x}{y}|||Test question single: {x}+{y} = ?",
        "answer1": "{x+y}",
    }
    print([q for q in convert_single_equation_problem(test_question_single)])