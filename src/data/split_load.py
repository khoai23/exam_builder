"""Code to split data by category and only load each of them upon request.
When used, app need a significant overhaul.
Will replace the corresponding item in session.py"""
import os, io, csv 
import glob
from collections import defaultdict

from src.data.reader import read_file_xlsx, write_file_xlsx, move_file, DEFAULT_FILE_PATH, read_file
from src.organizer import assign_ids

import logging
logger = logging.getLogger(__name__)

from typing import Optional, List, Tuple, Any, Union, Dict, Set

import urllib.parse as parselib # use quote/unquote with no safe char by default 
quote = lambda string, safe="", **kwargs: parselib.quote(string, safe=safe, **kwargs)
# unquote = lambda string, safe="", **kwargs: parselib.unquote(string, safe=safe, **kwargs)
unquote = parselib.unquote

class OnRequestData(dict):
    def __init__(self, data_path: str="data/data.html", categories: Optional[Set[str]]=None, backup_path: str="data/backup.html", maximum_cached: int=5, _initiate_blank: bool=False):
        """Construct and check if all files is ready."""
        base, ext = os.path.splitext(data_path)
        valid_files = glob.glob(base + "*")
        raw_fcats = [os.path.splitext(f.split("_")[-1])[0] for f in valid_files]
        fcats = set(unquote(cat) for cat in raw_fcats)
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
        self._data = {cat: base + "_" + quote(cat) + ext for cat in categories}
        self._backup_path = bbase, bext = os.path.splitext(backup_path)
        self._backups = {cat: bbase + "_" + quote(cat) + ext for cat in categories}
        # dict to load with caching 
        self._cache = {}
        self._maximum_cached = maximum_cached

    def load_category(self, category: str, with_ids: bool=False, use_cache: bool=True):
        """Load data specifically belong to a category. Can use cache to reduce IO overhead at expense of idle memory."""
        # load data from necessary filepath 
        if use_cache and category in self._cache:
            logger.debug("Found in cache, direct read and update.")
            # has cache; use it 
            order, data = self._cache[category]
            if order > 1:
                # reupdate all order
                self._cache = {category: (1, data), **{k: (i+1 if i < order else i, d) for k, (i, d) in self._cache.items()}}
        else:
            logger.debug("Not found in cache, read new.")
            # either cache not enabled or not found, get from file 
            data = read_file_xlsx(self._data[category])
            if with_ids:
                data = assign_ids(data)
            if use_cache:
                # throw away the one with order bigger than _maximum_cached; and append the data as 1st
                self._cache = {category: (1, data), **{k: (i+1, d) for k, (i, d) in self._cache.items() if i+1 <= self._maximum_cached}}
        return data 

    def update_category(self, category: str, data: List, keep_backup: bool=True, update_cache: bool=True):
        """Update data specifically belong to a category. By default keep a backup to perform rollback if necessary."""
        if(category not in self._data):
            logger.info("Category {} not found; adding new.".format(category))
            base, ext = self._data_path
            self._data[category] = base + "_" + quote(category) + ext 
            bbase, bext = self._backup_path
            self._backups[category] = bbase + "_" + quote(category) + ext
        elif(keep_backup and os.path.isfile(self._data[category])):
            # if has existing category, update it 
            logger.debug("Keep backup procedure: moving {} -> {}".format(self._data[category], self._backups[category]))
            move_file(self._data[category], self._backups[category], is_target_prefix=False, autoremove_target=True)
        # write the data into category 
        # TODO wrap this with recovery mechanism in case that write file failed
#        with io.open(self._data[category], "w", encoding)
        logger.debug("Attempt to write data: {}".format(self._data[category]))
        write_file_xlsx(self._data[category], data)
        # check and update cache item if any 
        if(update_cache):
            logger.debug("Re-updating cache upon update.")
            if(category in self._cache):
                order, old_data = self._cache[category]
                del old_data # throw away old data. Maybe not necessary?
                self._cache = {category: (1, data), **{k: (i+1 if i < order else i, d) for k, (i, d) in self._cache.items()}}
            else:
                # 
                self._cache = {category: (1, data), **{k: (i+1, d) for k, (i, d) in self._cache.items() if i+1 <= self._maximum_cached}}

    def category_has_rollback(self, category: str):
        # if true, category can be rolled back. 
        return os.path.isfile(self._backup_path[category])

    def rollback_category(self, category: str, update_cache: bool=True):
        """Attempting rollback. Note that this will cause error if rollback is not possible, e.g file missing."""
        move_file(self._backups[category], self._data[category], is_target_prefix=False, autoremove_target=True)
        # reload the data 
        data = load_category(category, use_cache=False)
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

    def update_data(self, data: List, update_cache: bool=False):
        """Update data of default format (with mixed category). Simply calls appropriate update_category functions.
        By default not updating cache; but wiping it instead"""
        categorized = defaultdict(list)
        for q in data:
            categorized[q.get("category", "N/A")].append(q)
        for cat in categorized:
            logger.debug("update_data performing update for category {}".format(cat))
            self.update_category(cat, data, update_cache=update_cache)
        if(not update_cache):
            # clear out the cache if not updated; TODO sort by old_i?
            self._cache = {k: (i+1, v) for i, (k, (old_i, v)) in enumerate(filter(lambda it: it[0] in categorized, self._cache.items()))}
    
    # compatibility with app.py

    def update_data_from_file(self, data_location: str, update_cache: bool=False):
        data = read_file(data_location)
        return update_data(data, update_cache=update_cache)
    
    def delete_data_by_ids(self, category: str, list_ids: List[int], update_cache: bool=True):
        old_data = self.load_category(category)
        new_data = [d for i, d in enumerate(old_data) if i in list_ids]
        self.update_category(category, new_data, update_cache=update_cache)

if __name__ == "__main__":
    data_obj = OnRequestData(_initiate_blank=True)
    loaded = read_file(DEFAULT_FILE_PATH)
    data_obj.update_data(loaded)
    print(data_obj)