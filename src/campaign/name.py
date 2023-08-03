"""Creation of province & units names, randomized or specific."""
import random 
from functools import partial

from typing import Optional, List, Tuple, Any, Union, Dict 

class NameGenerator:
    @staticmethod
    def generate_name() -> str:
        raise NotImplementedError

    @staticmethod
    def generate_province_name() -> str:
        raise NotImplementedError

    @staticmethod
    def generate_unit_name() -> str:
        raise NotImplementedError 

    @staticmethod
    def batch_generate_name(batch_size: int, generate_fn: callable, loop_limit: int=1000, **kwargs) -> List[str]:
        """Generate {batch_size} non-duplicate names using {generate_fn}
        Has a loop_limit that will raise an error if it ran up to this and still can't make enough name for batch_size"""
        assert loop_limit > batch_size, "Must specify a loop_limit greater than batch_size, but {} <= {}".format(loop_limit, batch_size)
        batch = set()
        for _ in range(loop_limit):
            # generate and dump
            name = generate_fn(**kwargs)
            batch.add(name)
            if len(batch) == batch_size:
                return batch 
        raise ValueError("Looped for {} iteration, but couldn't create batched name of size {} (only {})".format(loop_limit, batch_size, len(batch)))

class RussianNameGenerator(NameGenerator):
    PROVINCE_PREFIX = ["kra", "ku", "do", "o", "obo", "oktya", "le", "lo", "lyu", "frya", "i", "ma", "mi", "za", "ze", "zhi", "so", "ro", "rha", "se"]
    PROVINCE_PADDING = ["lya", "ksha", "ra", "zha", "sko", "chno", "do", "kho", "zho", "ntso", "pusko", "ktro", "shki", "bi", "fri", "mode", "khne", "she", "ve", "leta", "zi"]
    PROVINCE_SUFFIX = ["novo", "vo", "noy", "no", "ska", "vka", "nka", "dnya", "mut", "sky", "vsky", "rsky", "dny", "vny", "tov", "nskoye", "vskoye", "rkov", "nskov"]

    def __init__(self, shared_kwargs: Dict={}, province_kwargs: Dict={}):
        # allow creation of customizable NameGenerator object 
        self.generate_province_name = partial(RussianNameGenerator.generate_province_name, **shared_kwargs, **province_kwargs)

    @staticmethod 
    def non_duplicate_rule(previous, list_next):
        # prevent same-vowel word to occur together.
        # if multiple vowel available; only target the last one
        vowel = next((c for c in previous[::-1] if c in "aeiou"))
        # prevent repeating syllable (e.g nono or dod)
        return [w for w in list_next if vowel not in w and w[1] != previous[-1] and w[0] != previous[-2]]

    @staticmethod
    def generate_province_name(filter_generation_rule: Optional[callable]=None, capitalize: Optional[bool]=True) -> str:
        """Generate randomized name using the prefix-padding-suffix rule.
        If filter_generation_rule is used, it will receive the previous word and output the valid filtered list of next word.
        If set to true, will use the non_duplicate_rule specified above."""
        if not callable(filter_generation_rule) and filter_generation_rule:
            # is true; use above 
            filter_generation_rule = RussianNameGenerator.non_duplicate_rule
        prefix = random.choice(RussianNameGenerator.PROVINCE_PREFIX)
        list_pad = filter_generation_rule(prefix, RussianNameGenerator.PROVINCE_PADDING) if filter_generation_rule else RussianNameGenerator.PROVINCE_PADDING
        padding = random.choice(list_pad)
        list_suffix = filter_generation_rule(padding, RussianNameGenerator.PROVINCE_SUFFIX) if filter_generation_rule else RussianNameGenerator.PROVINCE_SUFFIX
        suffix = random.choice(list_suffix)
        if capitalize:
            prefix = prefix[0].upper() + prefix[1:]
        return prefix + padding + suffix


if __name__ == "__main__":
    dupnames = RussianNameGenerator.batch_generate_name(20, RussianNameGenerator.generate_province_name)
    print("Generate (dup):", dupnames)
    nodupnames = RussianNameGenerator.batch_generate_name(20, RussianNameGenerator.generate_province_name, filter_generation_rule=True)
    print("Generate (nodup):", nodupnames)
