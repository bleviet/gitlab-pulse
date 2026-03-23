import logging
import re
from typing import Optional, List, Union

logger = logging.getLogger(__name__)

def match_text(text: str, pattern: str) -> Optional[Union[str, bool]]:
    """Check if text matches pattern.

    Returns:
        - None if no match
        - Matched String (for regex capture) or True (for simple match)
    """
    if pattern.startswith("regex:"):
        regex = pattern[6:]
        try:
            match = re.search(regex, text)
            if match:
                return True
        except re.error:
            pass

    elif pattern.startswith("contains:"):
        substring = pattern[9:]
        if substring in text:
            return True

    elif pattern.startswith("exact:"):
        exact_str = pattern[6:]
        if text == exact_str:
            return True

    else:
        # Default to exact match
        if text == pattern:
            return True

    return None

def has_any_label(issue_labels: object, target_labels: List[str]) -> bool:
    """Check if issue has any of the target labels.

    Supports "regex:", "contains:", and "exact:" prefixes via match_text.
    """
    if issue_labels is None:
        return False
    try:
        # Handle numpy arrays / lists
        i_labels = list(issue_labels) if not isinstance(issue_labels, list) else issue_labels
    except (TypeError, ValueError):
        return False

    for target in target_labels:
        # Optimization: Check for simple exact match first if no prefix
        is_simple = not (target.startswith("regex:") or target.startswith("contains:") or target.startswith("exact:"))
        
        for label in i_labels:
            if not isinstance(label, str):
                continue
            
            # Use unified matching logic
            if match_text(label, target):
                 return True
                 
    return False
