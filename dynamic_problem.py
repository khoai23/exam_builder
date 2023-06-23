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

MathJaxSymbols = re.compile(r"$$|\\\(|\\\)|\\\[|\\\]")

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

range_regex = re.compile(r"\[(\d+),\s*(\d+)\]")

N = 1000
_PRIME, _SQUARE = [], []
for n in range(2, N):
    # prime
    is_prime = True
    for p in _PRIME:
        if(n % p == 0):
            is_prime = False
            break
    if(is_prime):
        _PRIME.append(n)
    # square 
    if(int(n ** 0.5) ** 2 == n):
        _SQUARE.append(n)
_PRIME = set(_PRIME)
_SQUARE = set(_SQUARE)

PROPERTIES_FILTER = {
    "prime":     lambda v: v in _PRIME,
    "square":    lambda v: v in _SQUARE,
    "nonprime":  lambda v: v not in _PRIME,
    "nonsquare": lambda v: v not in _SQUARE,
}
def create_variable_set(variable_and_limitation: str, duplicate_set: Optional[int]=None, check_validity: bool=False):
    """Variables will be specified with range [start, end], and other possible properties (square, prime, nonprime)
    Format will be variable: specification1 specification2..
    If the specification is empty, the variables will be assigned with range [1, 100].
    TODO: add conditional option between variables"""
    if(duplicate_set):
        result = [dict() for _ in range(duplicate_set)]
    else:
        result = dict()
    for variable_spec in (variable_and_limitation.split("\n") if "\n" in variable_and_limitation else [variable_and_limitation]):
        name, spec = variable_spec.split(":")
        range_match = re.search(range_regex, spec)
        if(range_match is None):
            start, end = 1, 100 
        else:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            if(start > end):
                start, end = end, start
        varrange = range(start, end+1) # turn to list after every filter 
        spec = [s.strip() for s in spec.split() if s.strip()]
        for key, filter_fn in PROPERTIES_FILTER.items():
            if key not in spec:
                continue 
            varrange = filter(filter_fn, varrange)
        # after filtering, condense to list and choose randomly 
        choices = list(varrange)
        if(check_validity):
            # choice should have more than one option 
            # TODO check composite  
            assert len(choices) > 1, "Variable {} must have at least 2 different choices to generate differing question, but only have {}.".format(name.strip(), choices)
        if(duplicate_set):
            for i in range(duplicate_set):
                result[i][name.strip()] = random.choice(choices)
        else:
            result[name.strip()] = random.choice(choices)
    return result

var_exp_regex = re.compile(r"{(.+?)}")
def convert_fixed_equation_problem(problem: Dict, separator="|||", generator_mode=False):
    """Designated fixed-equation format (e.g algebraic) will be `{variable}` and `{expression}` with the same 4 answers format, expression can only uses the designated variables.
    Currently enforced listing all variables at the start of the question; separated by "|||".
    TODO catch variables dynamically instead
        generator_mode: see above"""
    # find all instances of curly brackets 
    if(separator in problem["question"]):
        variable_section, question_section = problem["question"].split(separator)
        variables = set([catch for catch in re.findall(var_exp_regex, variable_section)])
    else:
        variable_section, question_section = None, problem["question"]
    answer_section = "\n".join(problem["answer{}".format(i)] for i in range(1, 5))
    expressions = set([catch for catch in re.findall(var_exp_regex, question_section + "\n" + answer_section)])
    if(problem.get("variable_limitation", "").strip()):
        # has a valid limitation; use it to create the variable
        assigned_variables = create_variable_set(problem["variable_limitation"])
    elif(variable_section is not None):
        print("Problem {} is in deprecated mode (with |||); please convert to the `variable_limitation` format.")
        assigned_variables = {k: random.randint(1, 100) for k in variables}
    else:
        raise ValueError("Problem using variable but specifying neither variable section (||| in question) nor `variable_limitation` field; question build aborted.")
    # TODO enforce expression type
    assigned_expressions = {("{" + exp + "}"): str(eval(exp, None, assigned_variables)) for exp in expressions}
    if re.search(MathJaxSymbols, problem["question"]):
        # keep symbols curly brackets 
        assigned_expressions = {k: "{" + v + "}" for k, v in assigned_expressions.items()}
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
    if(separator in problem["question"]):
        variable_section, question_section = problem["question"].split(separator)
        variables = set([catch for catch in re.findall(var_exp_regex, variable_section)])
    else:
        variable_section, question_section = None, problem["question"]
    # answer1 will contain the correct expression
    answer_section = problem["answer1"]
    expressions = set([catch for catch in re.findall(var_exp_regex, question_section + "\n" + answer_section)])
    assert any((exp in answer_section for exp in expressions)), "Single-equation question {} had an invalid (immutable) correct answer {}".format(problem, answer_section)
    # assign value to variables in four-tuple 
    four_problems = [dict(problem) for _ in range(4)]
    i = 0
    while i < 4: # this to allow rerolling variables; in case where generated result ran into duplication
        # TODO use the `duplicate_set` generatively
        if(problem.get("variable_limitation", "").strip()):
            # has a valid limitation; use it to create the variable
            assigned_variables = create_variable_set(problem["variable_limitation"])
        elif(variable_section is not None):
            print("Problem {} is in deprecated mode (with |||); please convert to the `variable_limitation` format.")
            assigned_variables = {k: random.randint(1, 100) for k in variables}
        else:
            raise ValueError("Problem using variable but specifying neither variable section (||| in question) nor `variable_limitation` field; question build aborted.")
        print(assigned_variables)
#        assigned_variables = {k: random.randint(1, 100) for k in variables}
        assigned_expressions = {("{" + exp + "}"): str(eval(exp, None, assigned_variables)) for exp in expressions}
        if re.search(MathJaxSymbols, problem["question"]):
            # keep symbols curly brackets 
            assigned_expressions = {k: "{" + v + "}" for k, v in assigned_expressions.items()}
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
