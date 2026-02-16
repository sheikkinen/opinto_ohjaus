"""Parse and summarize pipeline results from run log."""
import re
import sys

log_file = sys.argv[1] if len(sys.argv) > 1 else 'projects/opinto_ohjaus/run-op1-v3.log'
print(f"Parsing: {log_file}\n")
with open(log_file) as f:
    text = f.read()

# 1. Topic inventory
print("=" * 70)
print("1. TOPIC INVENTORY (list_topics)")
print("=" * 70)
idx = text.find("topic_inventory:")
end = text.find("vuosikello:", idx)
chunk = text[idx:end]
topics = re.findall(r"'title': '([^']+)'", chunk)
modules = re.findall(r"'module': '([^']+)'", chunk)
ids = re.findall(r"'id': '([^']+)'", chunk)
for tid, title, mod in zip(ids, topics, modules):
    print(f"  {tid:8s} [{mod}] {title}")
print(f"\n  Total: {len(topics)} topics")

# 2. Vuosikello
print("\n" + "=" * 70)
print("2. VUOSIKELLO (extract_vuosikello)")
print("=" * 70)
idx = text.find("vuosikello:")
end_idx = text.find("augmented_topics:", idx)
if end_idx < 0:
    end_idx = idx + 5000
chunk = text[idx:end_idx]
years = re.findall(r"'year': (\d+)", chunk)
semesters = re.findall(r"'semester': '([^']+)'", chunk)
foci = re.findall(r"'focus_areas': \[([^\]]+)\]", chunk)
for y, s, f in zip(years, semesters, foci):
    areas = [a.strip().strip("'") for a in f.split(",")]
    print(f"  {y}. vuosi {s}: {', '.join(areas[:4])}")
print(f"\n  Total: {len(years)} slots")

# 3. Lesson mapping
print("\n" + "=" * 70)
print("3. LESSON MAPPING (split_into_hours)")
print("=" * 70)
idx = text.find("lesson_mapping:")
end_idx = text.find("lesson_plans:", idx)
chunk = text[idx:end_idx]
titles = re.findall(r"'title': '([^']+)'", chunk)
types = re.findall(r"'session_type': '([^']+)'", chunk)
slots = re.findall(r"'vuosikello_slot': '([^']+)'", chunk)
topic_ids = re.findall(r"'topic_id': '([^']+)'", chunk)
for i, (title, stype, slot) in enumerate(zip(titles, types, slots), 1):
    tid = topic_ids[i-1] if i-1 < len(topic_ids) else "?"
    print(f"  {i:2d}. [{stype:14s}] {slot:30s} {title}")
print(f"\n  Total: {len(titles)} lessons")

# Type distribution
from collections import Counter
print(f"  Types: {dict(Counter(types))}")

# 4. Lesson plans - first plan sample
print("\n" + "=" * 70)
print("4. LESSON PLANS (generate_lessons) — Sample: Tunti 1")
print("=" * 70)
idx = text.find("# OPINTO-OHJAUS")
if idx > 0:
    # Find end of first plan (next map_index or next OPINTO-OHJAUS)
    next_plan = text.find("'_map_index':", idx + 100)
    chunk = text[idx:next_plan if next_plan > 0 else idx + 4000]
    chunk = chunk.replace("\\n", "\n")
    # Trim to reasonable length
    lines = chunk.split("\n")
    for line in lines[:40]:
        print(f"  {line}")
    if len(lines) > 40:
        print(f"  ... ({len(lines) - 40} more lines)")

# 5. Summary stats
print("\n" + "=" * 70)
print("5. SUMMARY")
print("=" * 70)
plan_count = len(re.findall(r"'_map_index': \d+", text[text.find("lesson_plans:"):]))
print(f"  Topics extracted: {len(topics)}")
print(f"  Vuosikello slots: {len(years)}")
print(f"  Lessons mapped: {len(titles)}")
print(f"  Lesson plans generated: {plan_count // 2}")  # each appears twice (map returns pairs)
