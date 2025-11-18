import sys, time

def patch_line(line: str) -> str:
    s = line.strip()
    if not s:
        return s
    parts = s.split(" ", 2)
    if len(parts) < 2:
        return s
    head, fields = parts[0], parts[1]
    ts = parts[2] if len(parts) == 3 else None

    ms = int(time.time() * 1000)
    fields_out = f"{fields},recorded_at_ms={ms}i"

    return f"{head} {fields_out}" + (f" {ts}" if ts else "")

for line in sys.stdin:
    out = patch_line(line)
    if out:
        print(out, flush=True)
