"""Script to give appropriate flavor for campaign. Should be a customizable aspect of the campaign object ala Rules."""
import io, json 
from collections import deque

from typing import Optional, List, Tuple, Any, Union, Dict, Callable

class GenericFlavorText:
    """Generic version: just output a simple string; likely without formatting."""
    def __init__(self, campaign, event_dict, keep: int=200):
        self.campaign = campaign
        self.event_dict = event_dict 
        self.event_logs = deque((), maxlen=keep)

    def on_event_triggered(self, event_cue: str, event_data: Optional[dict]):
        event_base = self.event_dict.get(event_cue, None)
        if event_base is None:
            # no matching event; simply skip 
            return  
        true_event_text = event_base.format(**event_data) if event_data else event_base
        self.event_logs.append(true_event_text) # deque should handle this already
        return true_event_text

    def get_full_logs(self, text_mode: bool=False) -> str:
        if text_mode:
            return "\n".join(self.event_logs)
        else:
            return self.event_logs

class DefaultFlavorText(GenericFlavorText):
    """The above; except loading the default text from default file @ src/campaign/default_flavor.json"""
    def __init__(self, campaign, flavor_text_file: str="src/campaign/default_flavor.json", **kwargs):
        with io.open(flavor_text_file, "r") as fjf:
            data = json.load(fjf)
        super(DefaultFlavorText, self).__init__(campaign, data, **kwargs)

class FormattedFlavorText(DefaultFlavorText):
    """Same thing as before; except text is formatted by html tags. Will require campaign html/js to properly interpret it instead of .text()"""
    def __init__(self, campaign, flavor_text_file: str="src/campaign/default_flavor_formatted.json", **kwargs):
        super(FormattedFlavorText, self).__init__(campaign, flavor_text_file=flavor_text_file, **kwargs)
