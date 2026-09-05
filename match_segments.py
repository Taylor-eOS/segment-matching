import os
import re
import sys

INPUT_TXT_PATH = "input.txt"
INPUT_FOLDER_PATH = "input"
OUTPUT_PATH = "output.txt"
WORD_COUNT = 7

def normalize_words(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    words = text.split()
    return words

def get_prefix_key(text, word_count):
    words = normalize_words(text)
    if len(words) < word_count:
        return None
    return " ".join(words[:word_count])

def read_segments(text):
    raw_segments = text.split("\n\n")
    segments = []
    for raw in raw_segments:
        stripped = raw.strip()
        if stripped:
            segments.append(stripped)
    return segments

def strip_role_prefix(block, role_label):
    prefix = role_label + ":"
    if block.startswith(prefix):
        block = block[len(prefix):]
    return block.strip()

def parse_conversation_file(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    raw_blocks = content.split("---")
    blocks = []
    for raw in raw_blocks:
        stripped = raw.strip()
        if stripped:
            blocks.append(stripped)
    pairs = []
    pending_user_text = None
    for block in blocks:
        if block.startswith("User:"):
            pending_user_text = strip_role_prefix(block, "User")
        elif block.startswith("Assistant:"):
            if pending_user_text is not None:
                assistant_text = strip_role_prefix(block, "Assistant")
                pairs.append((pending_user_text, assistant_text))
                pending_user_text = None
    return pairs

def build_index(folder_path, word_count):
    index = {}
    for filename in sorted(os.listdir(folder_path)):
        file_path = os.path.join(folder_path, filename)
        if not os.path.isfile(file_path):
            continue
        pairs = parse_conversation_file(file_path)
        for position, (user_text, assistant_text) in enumerate(pairs):
            key = get_prefix_key(assistant_text, word_count)
            if key is None:
                continue
            entry = (filename, position, user_text)
            if key not in index:
                index[key] = []
            index[key].append(entry)
    return index

def match_input_segments(input_segments, index, word_count):
    matched_user_texts = []
    unmatched_segments = []
    for segment_index, segment_text in enumerate(input_segments):
        key = get_prefix_key(segment_text, word_count)
        if key is None:
            unmatched_segments.append((segment_index, segment_text, "segment shorter than word count"))
            continue
        matches = index.get(key)
        if not matches:
            unmatched_segments.append((segment_index, segment_text, "no match found"))
            continue
        if len(matches) > 1:
            print(f"Ambiguous match for input segment {segment_index}, using first match:")
            for filename, position, _ in matches:
                print(f"  candidate: file={filename} position={position}")
        filename, position, user_text = matches[0]
        matched_user_texts.append(user_text)
    return matched_user_texts, unmatched_segments

def main():
    with open(INPUT_TXT_PATH, "r", encoding="utf-8") as f:
        input_text = f.read()
    input_segments = read_segments(input_text)
    index = build_index(INPUT_FOLDER_PATH, WORD_COUNT)
    matched_user_texts, unmatched_segments = match_input_segments(input_segments, index, WORD_COUNT)
    if unmatched_segments:
        print("The following input segments could not be matched:")
        for segment_index, segment_text, reason in unmatched_segments:
            preview = segment_text[:80].replace("\n", " ")
            print(f"  segment {segment_index} ({reason}): {preview}")
        sys.exit(1)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n\n".join(matched_user_texts))
    print(f"Wrote {len(matched_user_texts)} user segments to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
