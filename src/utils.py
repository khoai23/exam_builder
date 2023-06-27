# throw all nonsense, stackoverflow copy function here 
import re 
def ColIdxToXlName(idx):
    if idx < 1:
        raise ValueError("Index is too small")
    result = ""
    while True:
        if idx > 26:
            idx, r = divmod(idx - 1, 26)
            result = chr(r + ord('A')) + result
        else:
            return chr(idx + ord('A') - 1) + result 

def XlNameToColIdx(col):
    idx = (ord(c) - ord('A') + 1 for c in col.upper())
    val_idx = [i*26**idx for idx, i in enumerate(idx)]
    return sum(val_idx)

def cell_name_xl_to_tuple(cellname, zero_index=True):
    col = re.sub(r"\d", "", cellname)
    row = re.sub(r"[A-Z]", "", cellname)
    reduce = int(zero_index)
    return (int(row) - reduce, XlNameToColIdx(col) - reduce)
