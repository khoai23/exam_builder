"""Creation of province & units names, randomized or specific."""
import random 
from functools import partial

from typing import Optional, List, Tuple, Any, Union, Dict 

class NameGenerator:
    def __init__(self, shared_kwargs: Dict={}, province_kwargs: Dict={}):
        # allow creation of customizable NameGenerator object 
        # shared as default 
        # access current globals to get class name 
        class_obj = globals()[self.__class__.__name__]
        self.generate_province_name = partial(class_obj.generate_province_name, **shared_kwargs, **province_kwargs)

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
    """Ruskie names are currently vowel-ended for prefix & padding."""
    PROVINCE_PREFIX = ["kra", "ku", "do", "o", "obo", "oktya", "le", "lo", "lyu", "frya", "i", "ma", "mi", "za", "ze", "zhi", "so", "ro", "rha", "se"]
    PROVINCE_PADDING = ["lya", "ksha", "ra", "zha", "sko", "chno", "do", "kho", "zho", "ntso", "pusko", "ktro", "shki", "bi", "fri", "mode", "khne", "she", "ve", "leta", "zi"]
    PROVINCE_SUFFIX = ["novo", "vo", "noy", "no", "ska", "vka", "nka", "dnya", "mut", "sky", "vsky", "rsky", "dny", "vny", "tov", "nskoye", "vskoye", "rkov", "nskov"]

    @staticmethod 
    def non_duplicate_rule(previous, list_next):
        # prevent same-vowel word to occur together.
        # if multiple vowel available; only target the last one
        vowel = next((c for c in previous[::-1] if c in "aeiou"), "_") # if no vowel, this check search for _, which will always return false
        # prevent repeating syllable (e.g nono or dod)
        return [w for w in list_next if vowel not in w and (len(w) < 2 or len(previous) < 2 or (w[1] != previous[-1] and w[0] != previous[-2]))]

    @staticmethod
    def generate_province_name(filter_generation_rule: Optional[callable]=None, capitalize: Optional[bool]=True) -> str:
        """Generate randomized name using the prefix-padding-suffix rule.
        If filter_generation_rule is used, it will receive the previous word and output the valid filtered list of next word.
        If set to true, will use the non_duplicate_rule specified above."""
        if filter_generation_rule and not callable(filter_generation_rule):
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

class PolishNameGenerator(NameGenerator):
    """Polack names are vowel-started for padding & suffix.
    TODO add accents"""
    PROVINCE_PREFIX = ["aug", "bedz", "bol", "brz", "chrz", "cz", "czl", "deb", "elb", "gd", "gni", "grudz", "hrub", "kedz", "ketrz", "kl", "koz", "lw", "mik", "myszk", "op", "olszt", "pab", "polk", "prz", "radz", "rybn", "siedlc", "sok", "szkz", "wabrz", "wr", "wodz", "zg", "zl"]
    PROVINCE_PADDING = ["yst", "ansk", "iansk", "iesz", "obrz", "usz", "otosz", "ajsk", "ow", "idw", "yw", "ok", "alcz", "ezn", "ebn", "arn", "achow", "ult", "uszk", "iotrk", "olek"]
    PROVINCE_SUFFIX = ["e", "ie", "ecz", "ek", "owo", "ow", "orz", "ice", "in", "ik", "icz", "a", "ia", "aw"]

    @staticmethod
    def general_rule(previous, list_next, common_syllable=["dz", "cz", "sz", "sk", "ow"]):
        # in addition of ruling out vowel duplicates, also eliminate common syllable duplication 
        last_vowel = next((c for c in previous[::-1] if c in "aeiou"), "_") # if no vowel, this check search for _, which will always return false
        existed_syllable = [cs for cs in common_syllable if cs in previous]
        # filter once
        valid = (it for it in list_next if last_vowel not in it and all((es not in it for es in existed_syllable)))
        # same rule as Ruskie, preventing thing like kek or zoz happening
        valid = (w for w in valid if (len(w) < 2 or len(previous) < 2 or (w[1] != previous[-1] and w[0] != previous[-2])))
        # special rule 
        if previous[-1] in "gr":
            # if g/r, filter starter iy
            valid = (it for it in valid if it[0] not in "iy")
        elif previous[-1] == "k":
            # if k, filter e/a (should be with i)
            valid = (it for it in valid if it[0] not in "ea")
        # after all rules, convert to a list
        return list(valid)

    @staticmethod
    def generate_province_name(filter_generation_rule: Optional[callable]=None, capitalize: Optional[bool]=True) -> str:
        """Generate randomized name using the prefix-padding-suffix rule.
        If filter_generation_rule is used, it will receive the previous word and output the valid filtered list of next word.
        If set to true, will use the non_duplicate_rule specified above."""
        if filter_generation_rule and not callable(filter_generation_rule):
            # is true; use above 
            filter_generation_rule = PolishNameGenerator.general_rule
        prefix = random.choice(PolishNameGenerator.PROVINCE_PREFIX)
        list_pad = filter_generation_rule(prefix, PolishNameGenerator.PROVINCE_PADDING) if filter_generation_rule else PolishNameGenerator.PROVINCE_PADDING
        padding = random.choice(list_pad)
        list_suffix = filter_generation_rule(padding, PolishNameGenerator.PROVINCE_SUFFIX) if filter_generation_rule else PolishNameGenerator.PROVINCE_SUFFIX
        suffix = random.choice(list_suffix)
        if capitalize:
            prefix = prefix[0].upper() + prefix[1:]
        return prefix + padding + suffix

class SinoLatinizedNameGenerator(NameGenerator):
    """Gook names are.. what the hell I'm doing, I dont need guide for this shit."""
    PROVINCE_PREFIX = ["Quảng", "Hà", "Trường", "Hoàng", "Lạng", "Sa", "Hoà", "Tiền", "Xích", "Phú", "Thục", "Quyền", "Lữ", "Viễn"]
    PROVINCE_SUFFIX = ["Đông", "Tây", "Nội", "Ngoại", "Giang", "Sơn", "Thiên", "Nguyên", "Trị", "Kiến", "Phong", "Xương"]
    
    @staticmethod
    def generate_province_name(**kwargs) -> str:
        prefix = random.choice(SinoLatinizedNameGenerator.PROVINCE_PREFIX)
        suffix = random.choice(SinoLatinizedNameGenerator.PROVINCE_SUFFIX)
        return prefix + " " + suffix

class GermanNameGenerator(NameGenerator):
    """Same nonsense as we had always been doing; this time for the kraut. Extra X-Y variant can be very rarely generated."""
    PROVINCE_SUFFIX = ["sheim", "shaven", "bach", "burg", "berg", "nach", "dorn", "dorf", "münde", "stein", "städt", "feld", "land", "nau", "shausen", "snitz"]
    # essentially prefix; but allow some adj prefix appendage e.g Gross

    PROVINCE_CENTER = ["Her", "Hau", "Hör", "Höch", "Frei", "Elster", "Dorn", "Augs", "Arn", "Ilmen", "Kaiser", "Kreuz", "Langen", "Lieben", "Mackt", "Lützen", "Oder", "Oppen", "Ratzen", "Rhein", "Roß", "Schön", "Wessel", "Walder", "Witten", "Königs"]
    PROVINCE_PREFIX = ["Groß", "Bad ", "Oster", "Schwarzen", "Unter", "Weiß"]
    SPECIAL_LINK = ["Vellen-", "-Lengefeld", "Ober-", "-Lößnitz", "-Greiz", "-Freren", "-am-Rhein", "Breisach-"]

    @staticmethod
    def generate_province_name(**kwargs) -> str:
        core = random.choice(GermanNameGenerator.PROVINCE_CENTER)
        suffix = random.choice(GermanNameGenerator.PROVINCE_SUFFIX)
        name = core + suffix if suffix[0] != core[-1] else core + suffix[1:] # duplicate char (s mostly) will get truncated
        if len(name) < 10 and random.random() < 0.5:
            # 50% to append the prefix if name is too short
            prefix = random.choice(GermanNameGenerator.PROVINCE_PREFIX)
            name = prefix + name if prefix[-1] == " " else prefix + name[0].lower() + name[1:] 
        if random.random() < 0.1:
            # 10% to put the special link; either forward or backward depending on which
            linker = random.choice(GermanNameGenerator.SPECIAL_LINK)
            name = name + linker if linker[0] == "-" else linker + name
        return name

NAME_GENERATOR_BY_CUE = {
    "ruskie": RussianNameGenerator,
    "polack": PolishNameGenerator,
    "gook": SinoLatinizedNameGenerator,
    "kraut": GermanNameGenerator
}

if __name__ == "__main__":
    dupnames = RussianNameGenerator.batch_generate_name(20, RussianNameGenerator.generate_province_name)
    print("Generate (dup):", dupnames)
    nodupnames = RussianNameGenerator.batch_generate_name(20, RussianNameGenerator.generate_province_name, filter_generation_rule=True)
    print("Generate (nodup):", nodupnames)
