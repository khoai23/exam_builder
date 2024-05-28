"""Loader in the same logic as split_load's OnRequestData; except this can probs be full-load to memory as it hardly has any data in it.
Uses to build & display sessions for self_learn logic. Later will incorporate the pages alongside bpmn graph to make traversal mindmap; or to extend to some gamey thingie."""
import os, io, glob 

from src.data.split_load import catname_to_filename, filename_to_catname

import logging 
logger = logging.getLogger(__name__)

class MarkdownData(dict):
    def __init__(self, load_directory: str="data/lessons", load_extension: str=".md", search_subdirectory: bool=True, lazy: bool=False):
        """Attempt to load all markdown file in the folder into itself.
        If lazy mode; only keep reference, and get the data from disk when requested.
        TODO find some way to categorize & tag this so it can be linked over to `questions`."""
        if search_subdirectory:
            # this is wrong; need to use os.walk for subdirectory.
            all_files = glob.glob(load_directory + ("*" if load_directory.endswith("/") else "/*"))
        else:
            all_files = [os.path.join(load_directory, f) for f in os.listdir()]
        valid_files = {filename_to_catname(os.path.splitext(os.path.split(f)[-1])[0]): f for f in all_files if f.endswith(load_extension)}
        logger.debug("All valid markdown file found: {}; all files: {}".format(valid_files, all_files))
        self._lazy = lazy
        if lazy:
            # keep paths of all matching items; defer to __get_item__ to do the actual loading.
            self._all_valid_files = valid_files
        else:
            # load everything in right now.
            for key, full_path in valid_files.items():
                with io.open(full_path, "r", encoding="utf-8") as rf:
                    self[key] = rf.read()
            #print("Loaded self:", self.keys())
            self._all_valid_files = None

    def __get_item__(self, key):
        return super(MarkdownData, self).__get_item__(key)

    def __contains__(self, key):
        if self._lazy:
            return key in self._all_valid_files
        else:
            return super(MarkdownData, self).__contains__(key)

    def get_lesson(self, quoted_key: str, default=None):
        """In case of getting data from a key that have came from url; use this instead"""
        true_key = filename_to_catname(quoted_key)
        if self._lazy and true_key in self._all_valid_files and true_key not in self:
            # lazy loading triggered
            with io.open(self._all_valid_files[true_key], "r", encoding="utf-8") as rf:
                self[true_key] = rf.read()
            logger.debug("@MarkdownData: Lazy loading for requested key {} (original {})".format(true_key, key))
        return self.get(true_key, None)

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    md = MarkdownData()
    print("Printing raw md test page: \n\n\n" + md.get_lesson("test"))
