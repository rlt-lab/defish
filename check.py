"""Render one frame for every panel combination and check the output size, then encode a short MP4 with libx264.
Usage: uv run --python 3.13 --with imageio-ffmpeg python check.py [fisheye-video]
Without a video it uses a synthetic 1920x1920 test pattern, which exercises the same filters (used in CI)."""
import itertools
import os
import re
import sys
import tempfile

import app

tmp = tempfile.mkdtemp()
out = os.path.join(tmp, "f.png")
if len(sys.argv) > 1:
    src = sys.argv[1]
else:
    src = os.path.join(tmp, "src.mp4")
    r = app.run(["-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1920x1920:d=2", src])
    assert r.returncode == 0, r.stderr[-500:]
stamp = app.find_stamp(src, "1")
for n in range(1, 5):
    for sel in itertools.combinations(range(4), n):
        r = app.run(["-v", "error", "-y", "-i", src, "-frames:v", "1", "-filter_complex",
                     app.graph(0, stamp, list(sel)), "-map", "[out]", "-update", "1", out])
        assert r.returncode == 0, (sel, r.stderr[-500:])
        size = re.search(r"(\d+)x(\d+)", app.run(["-i", out]).stderr.split("Video:")[1]).group(0)
        assert size == ("1920x570" if n == 2 else "1920x1110"), (sel, size)  # + 30 px timestamp bar
r = app.render_preview(src, "0", 0, stamp, out, out)
assert r.returncode == 0, r.stderr[-500:]
r = app.run(["-v", "error", "-y", "-i", src, "-t", "0.5", "-filter_complex", app.graph(0, stamp, [0]),
             "-map", "[out]", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
             os.path.join(tmp, "ünï cødé.mp4")])  # non-ASCII name, like the UTF-8 fix guards against
assert r.returncode == 0, r.stderr[-500:]
print("ok: all 15 panel combinations + preview + libx264 export")
