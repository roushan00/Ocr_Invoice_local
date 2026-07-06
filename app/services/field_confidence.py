import json
import bisect

from typing import Any

import numpy as np


def build_token_spans(tokens: list[str]) -> list[tuple[int, int]]:
    spans = []
    pos = 0
    for tok in tokens:
        end = pos + len(tok)
        spans.append((pos, end))
        pos = end
    return spans

def compute_field_confidences(
    data: Any,
    text: str,
    tokens: list[str],
    probs: list[float],
    token_spans: list[tuple[int, int]] | None = None,
    search_state: list[int] | None = None, # Tracks position to fix the "first match" bug
) -> Any:

    # Initialization on first call
    if token_spans is None:
        token_spans = build_token_spans(tokens)
    if search_state is None:
        search_state = [0] # Use a mutable list to pass by reference through recursion

    # Handle Dictionaries
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            # Note: We don't calculate confidence for the keys, only values
            out[k] = compute_field_confidences(v, text, tokens, probs, token_spans, search_state)
        return out

    # Handle Lists
    if isinstance(data, list):
        return [
            compute_field_confidences(x, text, tokens, probs, token_spans, search_state)
            for x in data
        ]

    # Handle Primitives (Strings, Ints, Floats, Bools, None)
    try:
        value_str = json.dumps(data, ensure_ascii=False)
    except Exception:
        return None

    # Search FORWARD from our last known position to prevent duplicate matching
    start = text.find(value_str, search_state[0])

    # Fallback: If not found in remainder, search from beginning (rare edge case in malformed JSON)
    if start == -1:
        start = text.find(value_str)
        if start == -1:
            return None

    end = start + len(value_str)

    # Update search state for the next primitive
    search_state[0] = end

    # --- O(log N) BINARY SEARCH FOR TOKENS ---
    # Create a list of just the start indices for bisect
    start_indices = [s for s, e in token_spans]

    # Find the first token that could possibly overlap
    first_idx = bisect.bisect_right(start_indices, start) - 1
    first_idx = max(0, first_idx)

    field_probs = []
    for i in range(first_idx, len(token_spans)):
        s, e = token_spans[i]

        # If the token starts after our value ends, we can stop immediately!
        if s >= end:
            break

        # If it overlaps, grab the probability
        if s < end and e > start:
            field_probs.append(probs[i])

    if not field_probs:
        return None

    return round(float(np.mean(field_probs)) * 100, 2)
# def compute_field_confidences(data: Any, text_to_search: str, tokens: list[str], probs: list[float]) -> Any:
#     """
#     Recursively compute confidence (%) for every leaf field value
#     based on token probability alignment.
#     """
#     if isinstance(data, dict):
#         conf = {}
#         for key, value in data.items():
#             if isinstance(value, (dict, list)):
#                 conf[key] = compute_field_confidences(value, text_to_search, tokens, probs)
#             else:
#                 # Serialize the primitive value exactly as it appears in JSON
#                 # We use json.dumps to ensure string escaping matches the generated output
#                 value_str = json.dumps(value)

#                 # Find where this value appears in the full generated text
#                 start_pos = text_to_search.find(value_str)
#                 if start_pos == -1:
#                     conf[key] = None  # Not found
#                     continue
#                 end_pos = start_pos + len(value_str)

#                 # Find all tokens that overlap this character span
#                 field_probs = []
#                 current_pos = 0
#                 for i, token in enumerate(tokens):
#                     token_end = current_pos + len(token)
#                     # Check overlap
#                     if current_pos < end_pos and token_end > start_pos:
#                         field_probs.append(probs[i])
#                     current_pos = token_end

#                 if field_probs:
#                     # Arithmetic mean probability -> confidence %
#                     conf[key] = round(float(np.mean(field_probs)) * 100, 2)
#                 else:
#                     conf[key] = None
#         return conf

#     elif isinstance(data, list):
#         return [compute_field_confidences(item, text_to_search, tokens, probs) for item in data]
#     else:
#         return None


#--------------------------------------------
# import json

# from typing import Any

# import numpy as np

# def build_token_spans(tokens: list[str]) -> list[tuple[int, int]]:
#     spans = []
#     pos = 0
#     for tok in tokens:
#         start = pos
#         end = start + len(tok)
#         spans.append((start, end))
#         pos = end
#     return spans

# def compute_field_confidences(
#     data: Any,
#     text: str,
#     tokens: list[str],
#     probs: list[float],
#     token_spans: list[tuple[int, int]] | None = None,
# ) -> Any:

#     if token_spans is None:
#         token_spans = build_token_spans(tokens)

#     if isinstance(data, dict):
#         out = {}
#         for k, v in data.items():
#             out[k] = compute_field_confidences(v, text, tokens, probs, token_spans)
#         return out

#     if isinstance(data, list):
#         return [
#             compute_field_confidences(x, text, tokens, probs, token_spans)
#             for x in data
#         ]

#     # primitive
#     try:
#         value_str = json.dumps(data, ensure_ascii=False)
#     except Exception:
#         return None

#     start = text.find(value_str)
#     if start == -1:
#         return None
#     end = start + len(value_str)

#     field_probs = [
#         probs[i]
#         for i, (s, e) in enumerate(token_spans)
#         if s < end and e > start
#     ]

#     if not field_probs:
#         return None

#     return round(float(np.mean(field_probs)) * 100, 2)


