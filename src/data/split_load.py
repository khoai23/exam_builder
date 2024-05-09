"""Code to split data by category and only load each of them upon request.
When used, app need a significant overhaul.
Will replace the corresponding item in session.py"""
import os, io, csv, sys
import glob
from collections import defaultdict

from src.data.reader import read_file_xlsx, write_file_xlsx, move_file, DEFAULT_FILE_PATH, read_file
from src.data.autotagger import autotag_in_category, autoformat_in_category
from src.organizer import assign_ids 

import logging
logger = logging.getLogger(__name__)

from typing import Optional, List, Tuple, Any, Union, Dict, Set

import urllib.parse as parselib # use quote/unquote with no safe char by default 
# quote = lambda string, safe="", **kwargs: parselib.quote(string, safe=safe, **kwargs)
# unquote = lambda string, safe="", **kwargs: parselib.unquote(string, safe=safe, **kwargs) 
def catname_to_filename(catname: str, safe=""):
    if sys.platform in ("win32", "cygwin"):
        return parselib.quote(catname, safe=safe) # use html derivative name (space = %20 etc)
    else:
        return catname.replace(" ", "_") # use unicode name as-is (space = underscore)

def filename_to_catname(fname: str):
    if sys.platform in ("win32", "cygwin"):
        return parselib.unquote(fname) # use html derivative name (space = %20)
    else:
        return fname.replace("_", " ") # use unicode name as-is (space = underscore)

class OnRequestData(dict):
    def __init__(self, data_path: str="data/data.xlsx", categories: Optional[Set[str]]=None, backup_path: str="data/backup.xlsx", maximum_cached: int=5, _initiate_blank: bool=False, autotag_dict: Optional[Dict]=None, autoformat_dict: Optional[Dict]=None):
        """Construct and check if all files is ready."""
        base, ext = os.path.splitext(data_path)
        valid_files = glob.glob(base + "*")
        raw_fcats = [os.path.splitext(f.split("_", 1)[-1])[0] for f in valid_files]
        fcats = set(filename_to_catname(fcat) for fcat in raw_fcats)
        if(categories is None):
            # automatically infer the category basing on the filenames.
            categories = fcats
            logger.info("Loading data, categories found: {}({})".format(len(categories), categories))
        else:
            # cross-check with filenames; reporting on missing categories & files 
            not_found = {c for c in categories if c not in fcats}
            if len(not_found) > 0:
                logger.warning("Missing categories: {}; ignored.".format(not_found))
            ignored = {f for f in fcats if f not in categories}
            if len(ignored) > 0:
                logger.info("Categories {} present but not loaded.".format(ignored))
            categories = {c for c in categories if c in fcats}
        # special  _initiate_blank trigger to load backward-compatible file through initiating a blank object
        assert _initiate_blank or len(categories) > 0, "Must have valid categories to continue. File-detected categories: {}".format(fcats)
        # write all values to be used.
        self._data_path = base, ext
        self._data = {cat: base + "_" + catname_to_filename(cat) + ext for cat in categories}
        self._backup_path = bbase, bext = os.path.splitext(backup_path)
        self._backups = {cat: bbase + "_" + catname_to_filename(cat) + ext for cat in categories}
        # dict to load with caching 
        self._cache = {}
        self._maximum_cached = maximum_cached 
        # dict for autotagging questions.
        self._autotag_dict = autotag_dict 
        self._autoformat_dict = autoformat_dict

    @property
    def categories(self):
        return list(self._data.keys())

    @property 
    def current_category(self):
        # get the instance in cache that is last accessed. cache is currently organized as (category, (access_order, real_data))
        return min(self._cache.items(), key=lambda c: c[1][0])[0]

    def load_category(self, category: str, with_ids: bool=True, use_cache: bool=True) -> List[Dict]:
        """Load data specifically belong to a category. Can use cache to reduce IO overhead at expense of idle memory."""
        # load data from necessary filepath 
        if use_cache and category in self._cache:
            # has cache; use it 
            order, data = self._cache[category]
            logger.debug("Found in cache, direct read and update ({}, {} entries).".format(order, len(data)))
            if order > 1:
                # reupdate all order
                self._cache = {category: (1, data), **{k: (i+1 if i < order else i, d) for k, (i, d) in self._cache.items()}}
        else:
            logger.debug("Not found in cache, read new from {}".format(self._data[category]))
            # either cache not enabled or not found, get from file 
            data = read_file_xlsx(self._data[category])
            if self._autotag_dict and category in self._autotag_dict:
                logger.info("Autotag is enabled for selected category ({}); performing..".format(category))
                data = autotag_in_category(data, self._autotag_dict[category])
            if self._autoformat_dict and category in self._autoformat_dict:
                logger.info("Autoformat is enabled for selected category ({}); performing".format(category))
                data = autoformat_in_category(data, self._autoformat_dict[category])
            if with_ids:
                data = assign_ids(data)
            if use_cache:
                # throw away the one with order bigger than _maximum_cached; and append the data as 1st
                self._cache = {category: (1, data), **{k: (i+1, d) for k, (i, d) in self._cache.items() if i+1 <= self._maximum_cached}}
        return data 

    def update_category(self, category: str, data: List, keep_backup: bool=True, update_cache: bool=True, replacement_mode: bool=True):
        """Update data specifically belong to a category. By default keep a backup to perform rollback if necessary.
        replacement_mode: if true (default), the new data will be replacing the old one; if false, the new data will be appended to the end of the old one. This mode is not entirely necessary if data replacement logic is done outside."""
        if(category not in self._data):
            logger.info("Category {} not found; adding new.".format(category))
            base, ext = self._data_path
            self._data[category] = base + "_" + catname_to_filename(category) + ext 
            bbase, bext = self._backup_path
            self._backups[category] = bbase + "_" + catname_to_filename(category) + ext
        elif(keep_backup and os.path.isfile(self._data[category])):
            # if has existing category, update it 
            logger.debug("Keep backup procedure: moving {} -> {}".format(self._data[category], self._backups[category]))
            move_file(self._data[category], self._backups[category], is_target_prefix=False, autoremove_target=True)
        # write the data into category 
        # TODO wrap this with recovery mechanism in case that write file failed
#        with io.open(self._data[category], "w", encoding)
        if replacement_mode:
            logger.debug("Attempt to write data of \"{}\" to path {}".format(category, self._data[category]))
            write_file_xlsx(self._data[category], data)
        else:
            logger.warning("Attempt to append data & write for \"{}\" at path {}".format(category, self._data[category]))
            assert category in self._cache, "@update_category: can't perform append mode in uncached category {}. Upgrade if really need functionality.".format(category)
            _, old_data = self._cache[category]
            new_data = old_data + data 
            write_file_xlsx(self._data[category], new_data)
            data = new_data
#            logger.debug("@update_category, replacement_mode: old data ({}) -> new data ({})".format(len(old_data), len(data)))
        # check and update cache item if any 
        if(update_cache):
            assign_ids(data) # additionally, reindex new data to ensure safety
            logger.debug("Re-updating cache upon updated category {} ({} entries).".format(category, len(data)))
            if(category in self._cache):
                order, old_data = self._cache[category]
                del old_data # throw away old data. Maybe not necessary? 
                cache_replacement = {k: (i+1 if i < order else i, d) for k, (i, d) in self._cache.items()}
            else:
                cache_replacement = {k: (i+1, d) for k, (i, d) in self._cache.items() if i+1 <= self._maximum_cached}
            cache_replacement.update({category: (1, data)}) # this to ensure `category` received the correct entry
            self._cache.clear()
            self._cache.update(cache_replacement)
            logger.debug("After update:({}) {}".format(len(data), {k: (i, len(d)) for k, (i, d) in self._cache.items()}))

    def category_has_rollback(self, category: str):
        # if true, category can be rolled back. 
        return os.path.isfile(self._backup_path[category])

    def rollback_category(self, category: str, update_cache: bool=True):
        """Attempting rollback. Note that this will cause error if rollback is not possible, e.g file missing."""
        move_file(self._backups[category], self._data[category], is_target_prefix=False, autoremove_target=True)
        # reload the data 
        data = self.load_category(category, use_cache=False)
        # check and update cache item if any
        if(update_cache):
            logger.debug("Re-updating cache upon rollback.")
            if(category in self._cache): # cache has category
                order, old_data = self._cache[category]
                del old_data # throw away old data. Maybe not necessary?
                self._cache = {category: (1, data), **{k: (i+1 if i < order else i, d) for k, (i, d) in self._cache.items()}}
            else:   # cache not have category
                self._cache = {category: (1, data), **{k: (i+1, d) for k, (i, d) in self._cache.items() if i+1 <= self._maximum_cached}}
        return data

    def update_data(self, data: List, update_cache: bool=True, replacement_mode: bool=False):
        """Update data of default format (with mixed category). Simply calls appropriate update_category functions.
        By default not updating cache; but wiping it instead.
        Update means \"appending received data to existing\" until otherwise stated.
        """
        categorized = defaultdict(list)
        for q in data:
            # ensure that category will be put into N/A even if it's blank
            categorized[q.get("category", "N/A") or "N/A"].append(q)
        for cat in categorized:
            logger.debug("@update_data performing update for category {}".format(cat))
            self.update_category(cat, categorized[cat], update_cache=update_cache, replacement_mode=replacement_mode)
    
    # compatibility with app routes. See src/routes/data_routes.py for details
    def update_data_from_file(self, data_location: str, update_cache: bool=True, replacement_mode: bool=False):
        logger.info("@update_data_from_file: trying to update with file at {} with replace={}".format(data_location, replacement_mode))
        data = read_file(data_location)
        return self.update_data(data, update_cache=update_cache, replacement_mode=replacement_mode)
    
    def delete_data_by_ids(self, list_ids: List[int], category: str, update_cache: bool=True):
        old_data = self.load_category(category)
        new_data = [d for i, d in enumerate(old_data) if i not in list_ids]
        self.update_category(category, new_data, update_cache=update_cache, replacement_mode=True)

    def modify_data_by_id(self, qid: int, category: str, field: str, value: str, update_cache: bool=True):
        data = self.load_category(category)
        target = data[qid]
        logger.debug("Perform modification: base question {}; value \"{}\"=\"{}\"".format(target, field, value))
        target[field] = value 
        if update_cache:
            self.update_category(category, data, update_cache=update_cache)

    def swap_to_new_category(self, list_ids: List[int], old_category: str, new_category: str, update_id: bool=True, update_cache: bool=True):
        old_data = self.load_category(old_category)
        new_data = self.load_category(new_category)
        removed_data = []
        for i, d in enumerate(old_data):
            if i in list_ids:
                # is in the moved one; append to new_data 
                d["id"] = len(new_data)
                new_data.append(d)
            else:
                # is in unmoved; add back into the removed section 
                d["id"] = len(removed_data)
                removed_data.append(d)
        # reupdate both; new will use append & put all the new data after it, while old will just replace
        self.update_category(new_category, new_data, update_cache=update_cache, replacement_mode=False)
        self.update_category(old_category, removed_data, update_cache=update_cache)

if __name__ == "__main__":
    data_obj = OnRequestData(_initiate_blank=True)
    loaded = read_file(DEFAULT_FILE_PATH)
    data_obj.update_data(loaded, replacement_mode=True)
    print(data_obj)
