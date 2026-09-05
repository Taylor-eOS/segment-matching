import os
import re
import sys
from difflib import SequenceMatcher

INPUT_TXT_PATH = "input.txt"
INPUT_FOLDER_PATH = "input"
OUTPUT_PATH = "output.txt"
DIAGNOSTICS_PATH = "diagnostics.txt"
TOP_CANDIDATES_TO_REPORT = 3
PREVIEW_LENGTH = 200

def normalize_words(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    words = text.split()
    return words

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

def build_candidates(folder_path):
    candidates = []
    for filename in sorted(os.listdir(folder_path)):
        file_path = os.path.join(folder_path, filename)
        if not os.path.isfile(file_path):
            continue
        pairs = parse_conversation_file(file_path)
        for position, (user_text, assistant_text) in enumerate(pairs):
            assistant_words = normalize_words(assistant_text)
            candidates.append({
                "filename": filename,
                "position": position,
                "user_text": user_text,
                "assistant_text": assistant_text,
                "assistant_words": assistant_words,
            })
    return candidates

def score_candidate(segment_words, candidate_words):
    matcher = SequenceMatcher(None, segment_words, candidate_words, autojunk=False)
    return matcher.ratio()

def rank_candidates_for_segment(segment_text, candidates):
    segment_words = normalize_words(segment_text)
    scored = []
    for candidate in candidates:
        score = score_candidate(segment_words, candidate["assistant_words"])
        scored.append((score, candidate))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored

def make_preview(text):
    flattened = text.replace("\n", " ")
    if len(flattened) > PREVIEW_LENGTH:
        return flattened[:PREVIEW_LENGTH] + "..."
    return flattened

def match_all_segments(input_segments, candidates):
    results = []
    for segment_index, segment_text in enumerate(input_segments):
        ranked = rank_candidates_for_segment(segment_text, candidates)
        results.append((segment_index, segment_text, ranked))
    return results

def write_diagnostics(results, path):
    with open(path, "w", encoding="utf-8") as f:
        for segment_index, segment_text, ranked in results:
            f.write(f"=== INPUT SEGMENT {segment_index} ===\n")
            f.write(make_preview(segment_text) + "\n\n")
            top = ranked[:TOP_CANDIDATES_TO_REPORT]
            for rank_index, (score, candidate) in enumerate(top):
                f.write(f"  candidate #{rank_index + 1} score={score:.3f} file={candidate['filename']} position={candidate['position']}\n")
                f.write("    assistant: " + make_preview(candidate["assistant_text"]) + "\n")
                f.write("    user:      " + make_preview(candidate["user_text"]) + "\n")
            f.write("\n")

def write_output(results, path):
    matched_user_texts = []
    for segment_index, segment_text, ranked in results:
        if not ranked:
            continue
        best_score, best_candidate = ranked[0]
        matched_user_texts.append(best_candidate["user_text"])
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(matched_user_texts))
    return len(matched_user_texts)

def print_summary(results):
    relative_margin_threshold = 1.5
    for segment_index, segment_text, ranked in results:
        if not ranked:
            print(f"segment {segment_index}: no candidates available at all")
            continue
        best_score, best_candidate = ranked[0]
        if len(ranked) > 1:
            second_score, second_candidate = ranked[1]
            if second_score <= 0:
                continue
            relative_margin = best_score / second_score
            if relative_margin < relative_margin_threshold:
                print(f"segment {segment_index}: close call, best score={best_score:.3f} (file={best_candidate['filename']} position={best_candidate['position']}) vs second={second_score:.3f} (file={second_candidate['filename']} position={second_candidate['position']})")

def main():
    with open(INPUT_TXT_PATH, "r", encoding="utf-8") as f:
        input_text = f.read()
    input_segments = read_segments(input_text)
    candidates = build_candidates(INPUT_FOLDER_PATH)
    if not candidates:
        print("No Assistant/User pairs found in the input folder, nothing to match against.")
        sys.exit(1)
    results = match_all_segments(input_segments, candidates)
    write_diagnostics(results, DIAGNOSTICS_PATH)
    written_count = write_output(results, OUTPUT_PATH)
    print_summary(results)
    print(f"Wrote {written_count} user segments to {OUTPUT_PATH}")
    print(f"Wrote per-segment candidate diagnostics to {DIAGNOSTICS_PATH}")

if __name__ == "__main__":
    main()
