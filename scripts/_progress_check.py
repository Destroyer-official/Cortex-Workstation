import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(HERE, "_result.txt")


def w(msg):
    with open(out, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


# fresh file
open(out, "w").close()
w("start")
sys.path.insert(0, os.path.join(HERE, "..", "src"))
try:
    from cortex_unified.engine import CleanerService
    w("imported")
    msgs = []
    rep = CleanerService().scan_categories(progress=lambda m: msgs.append(m))
    w(f"done files={rep.total_files} progress_msgs={len(msgs)}")
except BaseException as exc:  # noqa: BLE001
    import traceback
    w("EXC " + repr(exc))
    w(traceback.format_exc())
