#!/usr/bin/env python3
"""Verify the AI continuity docs (doc/ai/) against their archived originals.

Read-only. Exit status 0 = every check passed, 1 = at least one failure.
Warnings (size budgets) never fail the run.

Checks:

1. Archive integrity -- every file in doc/ai/archive/*/manifest.json still
   has its recorded SHA-256, and (when git can reach the recorded revision)
   is byte-identical to `git show <revision>:<original_path>`.
2. Mapping coverage -- in doc/ai/migration/*-mapping.json every source's
   segments tile it exactly: each line in exactly one segment.
3. Verbatim blocks -- every segment is present exactly once, in its recorded
   destination, between `<!-- verbatim:begin src=... lines=a-b ... -->` and
   `<!-- verbatim:end -->`. Its text, after undoing the recorded relative-link
   rewrites, is byte-identical to that line range of the archive. No
   unmapped verbatim block exists anywhere under doc/ai/.
4. Reconstruction -- concatenating all recovered segments in line order
   reproduces each archived file exactly (SHA-256 compared).
5. Links -- every relative Markdown link in doc/ai/**/*.md, in each
   CLAUDE.md and in AGENTS.md resolves to an existing path.
6. Budgets (warnings) -- root CLAUDE.md <= 150 lines; doc/ai/STATE.md and
   doc/ai/HANDOFF.md <= ~600 words (the copyable prompt block in HANDOFF is
   counted separately); nested CLAUDE.md sizes are reported.

Usage:  python scripts/verify-ai-docs.py [--quiet]
"""
import glob
import hashlib
import json
import os
import posixpath
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINK_RE = re.compile(rb"\]\(([^)\s]+)\)")
BEGIN_RE = re.compile(rb"^<!-- verbatim:begin src=(\S+) lines=(\d+)-(\d+) sha256=([0-9a-f]{64}) -->\n", re.M)
END = b"<!-- verbatim:end -->\n"

failures = []
warnings = []
quiet = "--quiet" in sys.argv


def fail(msg):
    failures.append(msg)
    print("FAIL  " + msg)


def ok(msg):
    if not quiet:
        print("ok    " + msg)


def warn(msg):
    warnings.append(msg)
    print("WARN  " + msg)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


def read(p):
    with open(os.path.join(ROOT, p), "rb") as f:
        return f.read()


def split_lines(b):
    parts = b.split(b"\n")
    lines = [p + b"\n" for p in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def is_external(t):
    return t.startswith(("http://", "https://", "mailto:", "#")) or (":" in t.split("/")[0] and not t.startswith("."))


def strip_anchor(t):
    return t.split("#", 1)[0]


def exists(repo_path):
    return os.path.exists(os.path.join(ROOT, repo_path))


# ---- 1. archives -----------------------------------------------------------
manifests = sorted(glob.glob(os.path.join(ROOT, "doc/ai/archive/*/manifest.json")))
if not manifests:
    fail("no archive manifest found under doc/ai/archive/")
archive_bytes = {}
for mf in manifests:
    man = json.load(open(mf, encoding="utf8"))
    revision = man["revision"]
    for f in man["files"]:
        a = f["archive"]
        if not exists(a):
            fail(f"archive missing: {a}")
            continue
        data = read(a)
        archive_bytes[a] = data
        if sha(data) != f["sha256"]:
            fail(f"archive hash changed: {a}")
        else:
            ok(f"archive hash {f['sha256'][:12]} {a}")
        try:
            head = subprocess.run(["git", "show", f"{revision}:{f['original_path']}"], cwd=ROOT,
                                  capture_output=True, check=True).stdout
            if head != data:
                fail(f"archive differs from git {revision[:7]}:{f['original_path']}")
            else:
                ok(f"archive == git {revision[:7]}:{f['original_path']}")
        except (OSError, subprocess.CalledProcessError):
            warn(f"git revision {revision[:7]} not reachable; skipped git comparison for {a}")

# ---- 2-4. mapping, verbatim blocks, reconstruction -------------------------
md_files = [p for p in glob.glob(os.path.join(ROOT, "doc/ai/**/*.md"), recursive=True)
            if "/archive/" not in rel(p) + "/"]
blocks = {}  # (src, a, b) -> list of (file, bytes)
for p in md_files:
    data = open(p, "rb").read()
    for m in BEGIN_RE.finditer(data):
        start = m.end()
        end = data.find(END, start)
        if end < 0:
            fail(f"{rel(p)}: unterminated verbatim block {m.group(0)[:80]!r}")
            continue
        key = (m.group(1).decode(), int(m.group(2)), int(m.group(3)))
        blocks.setdefault(key, []).append((rel(p), data[start:end], m.group(4).decode()))

seen = set()
for mp in sorted(glob.glob(os.path.join(ROOT, "doc/ai/migration/*-mapping.json"))):
    mapping = json.load(open(mp, encoding="utf8"))
    for s in mapping["sources"]:
        src, arch = s["path"], s["archive"]
        data = archive_bytes.get(arch)
        if data is None:
            fail(f"{rel(mp)}: archive {arch} not in any manifest")
            continue
        lines = split_lines(data)
        if len(lines) != s["lines"]:
            fail(f"{src}: mapping says {s['lines']} lines, archive has {len(lines)}")
        expect = 1
        rebuilt = []
        for g in sorted(s["segments"], key=lambda g: g["lines"][0]):
            a, b = g["lines"]
            if a != expect:
                fail(f"{src}: coverage gap/overlap at line {expect} (segment starts {a})")
            expect = b + 1
            key = (src, a, b)
            seen.add(key)
            found = blocks.get(key, [])
            if len(found) != 1:
                fail(f"{src}:{a}-{b}: expected 1 verbatim block, found {len(found)} {[f for f, _, _ in found]}")
                continue
            fpath, text, hsum = found[0]
            if fpath != g["dest"]:
                fail(f"{src}:{a}-{b}: block is in {fpath}, mapping says {g['dest']}")
            # undo link rewrites, checking each against the record
            recs = list(g["links"])
            out, pos, i = [], 0, 0
            dest_dir, src_dir = posixpath.dirname(g["dest"]), posixpath.dirname(src)
            for m in LINK_RE.finditer(text):
                t = m.group(1).decode("utf8")
                if is_external(t):
                    continue
                if i >= len(recs) or recs[i]["new"] != t:
                    fail(f"{src}:{a}-{b}: link #{i} is {t!r}, record says {recs[i]['new'] if i < len(recs) else None!r}")
                    break
                r = recs[i]
                tgt = posixpath.normpath(posixpath.join(dest_dir, strip_anchor(t)))
                orig_tgt = posixpath.normpath(posixpath.join(src_dir, strip_anchor(r["orig"])))
                if tgt != r["target"] or (orig_tgt != tgt and not (r["repaired"] and posixpath.normpath(strip_anchor(r["orig"])) == tgt)):
                    fail(f"{src}:{a}-{b}: link {r['orig']!r} -> {t!r} does not point at the same file")
                out.append(text[pos:m.start(1)])
                out.append(r["orig"].encode("utf8"))
                pos = m.end(1)
                i += 1
            if i != len(recs):
                fail(f"{src}:{a}-{b}: {len(recs) - i} recorded link rewrite(s) not found in block")
            out.append(text[pos:])
            restored = b"".join(out)
            original = b"".join(lines[a - 1:b])
            if restored != original:
                fail(f"{src}:{a}-{b}: verbatim text differs from archive (edited inside markers?)")
            elif sha(original) != hsum or hsum != g["sha256"]:
                fail(f"{src}:{a}-{b}: segment hash mismatch")
            rebuilt.append(restored)
        if expect != len(lines) + 1:
            fail(f"{src}: segments end at line {expect - 1}, file has {len(lines)}")
        if sha(b"".join(rebuilt)) == sha(data):
            ok(f"reconstructed {src} byte-for-byte from {len(s['segments'])} segments ({len(data)} bytes)")
        else:
            fail(f"{src}: reconstruction does not match archive")

for key, found in blocks.items():
    if key not in seen:
        fail(f"unmapped verbatim block {key} in {[f for f, _, _ in found]}")

# ---- 5. links --------------------------------------------------------------
guides = [p for p in glob.glob(os.path.join(ROOT, "**/CLAUDE.md"), recursive=True)
          if "thirdparty" not in p and "node_modules" not in p]
check = md_files + guides + [os.path.join(ROOT, "AGENTS.md")]
nlinks = 0
for p in check:
    d = posixpath.dirname(rel(p))
    text = open(p, "rb").read()
    # ignore fenced code blocks
    text = re.sub(rb"```.*?```", b"", text, flags=re.S)
    for m in LINK_RE.finditer(text):
        t = m.group(1).decode("utf8")
        if is_external(t) or not strip_anchor(t):
            continue
        nlinks += 1
        target = posixpath.normpath(posixpath.join(d, strip_anchor(t)))
        if not exists(target):
            fail(f"broken link in {rel(p)}: ({t}) -> {target}")
ok(f"{nlinks} relative links checked")

# ---- 6. budgets ------------------------------------------------------------
def words(p):
    t = read(p).decode("utf8")
    fence = re.findall(r"```.*?```", t, flags=re.S)
    body = re.sub(r"```.*?```", "", t, flags=re.S)
    return len(body.split()), sum(len(f.split()) for f in fence)

root_lines = len(split_lines(read("CLAUDE.md")))
(warn if root_lines > 150 else ok)(f"root CLAUDE.md: {root_lines} lines, {len(read('CLAUDE.md'))} bytes (target <= 150 lines)")
for p in ("doc/ai/STATE.md", "doc/ai/HANDOFF.md"):
    if exists(p):
        w, fw = words(p)
        (warn if w > 600 else ok)(f"{p}: {w} words outside code blocks (+{fw} in code blocks; target ~600)")
    else:
        fail(f"missing {p}")
for p in guides:
    if rel(p) != "CLAUDE.md":
        ok(f"{rel(p)}: {len(split_lines(open(p, 'rb').read()))} lines, {os.path.getsize(p)} bytes")

print()
print(f"{len(failures)} failure(s), {len(warnings)} warning(s)")
sys.exit(1 if failures else 0)
