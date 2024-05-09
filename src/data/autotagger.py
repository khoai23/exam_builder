"""Tool to auto-tag the questions in specific category using specific cue.
Not meant for actual user"""
import re

import logging 
logger = logging.getLogger(__name__)

from typing import Optional, List, Tuple, Any, Union, Dict, Set

def autotag_in_category(data: List[Dict], tagger: Dict[str, str], point_based: bool=False):
    for q in data:
        autotag, question = None, q["question"].lower()
        # tagging procedure; if point_based, will get the one with maximum cue count, if not, get the 1st to occur
        if point_based:
            tag_score = dict()
        for cue, tag in tagger.items():
            if cue in question:
                if point_based:
                    tag_score[tag] += 1
                else:
                    logger.debug("Found tag {}; using.".format(tag))
                    autotag = tag 
                    break 
        if point_based:
            autotag = max(tag_score.items(), key=lambda v: v[-1], default=(None, None))[0]
        # with the autotag, check if it already exist; ignore if not
        if autotag:
            if autotag not in q.get("tag", []):
                new_tags = q.get("tag", list())
                new_tags.append(autotag)
                q["tag"] = new_tags 
            else:
                logger.debug("Tag {} already in property; do nothing".format(tag))
    return data

# this will ignore all that already LaTeX-ifed; plus anything with image
_already_formatted_fn = lambda text: any(cue in text for cue in (r"\(", r"\)", "$$", r"\[", r"\]", "https"))
def autoformat_in_category(data: List[Dict], formatter: Dict[re.Pattern, callable], formatted_fn: callable=_already_formatted_fn):
    """If found a specific category-cue in the data's question/answers (by regex), formatter will take the token & convert it accordingly."""
    formatter_list = formatter.items()
    for q in data:
        for field in ("question", "answer1", "answer2", "answer3", "answer4"):
            if field not in q:
                continue 
            value = q[field]
            if formatted_fn(value):
                # already formatted, no need to do all this jazz
                continue
            for regex, converter in formatter_list:
                if re.search(regex, value):
                    logger.debug("Found autoformattable field; attempting convert \"{}\" with matching regex".format(value[:10] + "..." if len(value) > 13 else value))
                    # found matching, attempt conversion
                    value = re.sub(regex, converter, value)
            # after conversion; the value is reassigned back into the field 
            q[field] = value 
    return data



AUTOTAG_MATH = {
        "không gian": "Hình học 3D",
        "mặt phẳng": "Hình học 3D",
        "thể tích": "Hình học 3D",
        "thiết diện": "Hình học 3D",
        "hình hộp": "Hình học 3D",
        "hình chóp": "Hình học 3D",
        "hình trụ": "Hình học 3D",
        "hình cầu": "Hình học 3D",
        "hình nón": "Hình học 3D",
        "khối hộp": "Hình học 3D",
        "khối chóp": "Hình học 3D",
        "khối trụ": "Hình học 3D",
        "khối cầu": "Hình học 3D",
        "lập phương": "Hình học 3D",
        "lăng trụ": "Hình học 3D",
        "tứ diện": "Hình học 3D",
        "mặt cầu": "Hình học 3D",
        "vectơ": "Hình học 3D",
        "tích vô hướng": "Hình học 3D",

        "nguyên hàm": "Nguyên hàm",
        "tích phân": "Nguyên hàm",
        "dx": "Nguyên hàm",
        r"\displaystyle\int": "Nguyên hàm",

        "đạo hàm": "Đạo hàm",

        "log": "Logarit",

        "số phức": "Số phức",
        "phần ảo": "Số phức",

        "cấp số": "Cấp số",
        "công sai": "Cấp số",

        "xác suất": "Xác suất - Thống kê",
        "cách chọn": "Xác suất - Thống kê",

        "chỉnh hợp": "Tổ hợp",
        "hoán vị": "Tổ hợp",

        "hàm số": "Hàm số",
        "phương trình": "Hàm số",
}

regex_all_chemical_element = r"A[cglmrstu]|B[aehikr]?|C[adeflmnorsu]?|D[bsy]|E[rsu]|F[elmr]?|G[ade]|H[efgos]?|I[nr]?|Kr?|L[airuv]|M[cdgnot]|N[abdehiop]?|O[gs]?|P[abdmortu]?|R[abefghnu]|S[bcegimnr]?|T[abcehilms]|U|V|W|Xe|Yb?|Z[nr]"
regex_chemical_compound = r"(" + regex_all_chemical_element + r"|\()(" + regex_all_chemical_element + r"|\(|\)|\d)+"
# additionally, this will lose some specific 2-3 alpha-only compound; write that exception list here
special_alphaonly_compound = ("CO", "HCl", "KCl", "KOH", "NO", "CuO", "FeO", "CaO", "BaO", "MgO", "ZnO", "FeS", "CuS", "ZnS", "MgS")
# also catch CnHn if want to
def latexify_compound(match_obj):
    raw_compound = match_obj.group(0)
    if raw_compound.isnumeric():
        return raw_compound 
    if "II" in raw_compound:
        return raw_compound # muoi sat II & III
    if raw_compound.count(")") != raw_compound.count("("):
        return raw_compound
    elif all(r.isalpha() for r in raw_compound):
        if raw_compound not in special_alphaonly_compound and len(raw_compound) < 4: 
            # compound is very likely incorrect - alpha only compound is rare and usually be long e.g whatever-COOH 
            return raw_compound
        else:
            # if valid; just wrap & return 
            return r"\({:s}\)".format(raw_compound)
    else:
        # has number; attempt to split & rejoin with appropriate conversion 
        pieces = [p for p in re.split("(\d+)", raw_compound) if p]
        # number will be turned to subscript except when it's start of the string (e.g 2CuSO4)
        if pieces[0].isnumeric():
            true_compound = "".join( ("_{" + p + "}" if p.isnumeric() else p for i, p in enumerate(pieces[1:])))
            return r"{:s}\({:s}\)".format(pieces[0], true_compound)
        else:   
            true_compound = "".join( ("_{" + p + "}" if p.isnumeric() else p for i, p in enumerate(pieces)))
            return r"\({:s}\)".format(true_compound)
        
AUTOTAG_CHEMISTRY = {regex_chemical_compound: latexify_compound}
