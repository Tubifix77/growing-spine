"""embed_gate.py -- semantic similarity layer for the idea gate (v0.12).

Static embeddings (Model2Vec potion-base-8M: numpy-only, ~30MB, ~2ms/encode
on this laptop) give the gate what lexical matching structurally cannot:
paraphrase detection. Calibrated 2026-07-14 on the REAL corpus (68 regrown
paraphrases vs genuine one-offs, never authored fixtures):
  regrown->sibling similarity: min 0.446, p10 0.557, median 0.704
  genuine uniques (thermal probe, ensure_jq, resource_monitor): <= 0.53
  borderline non-dups (backup-workspace~task_backlog): ~0.71
Three bands:
  sim >= SIM_DUP  (0.75) -> deterministic DUPLICATE, zero tokens
  sim <  SIM_FLOOR(0.45) -> deterministic NEW, zero tokens
  between                -> LLM judge, fed embedding-ranked candidates
Everything here fails soft: any error -> available() False -> callers fall
back to the lexical path (current behavior), printing one notice.
"""
import json, os, re, time

SIM_DUP = 0.75
SIM_FLOOR = 0.45
MODEL_NAME = os.environ.get("EMBED_MODEL", "minishlab/potion-base-8M")
_MIND = os.environ.get("VOLUME_MOUNT", os.path.expanduser("~/growing-spine-mind"))
_STATE_DIR = os.path.join(_MIND, "state")
_INDEX_NPZ = os.path.join(_STATE_DIR, "tool_embeddings.npz")
_INDEX_META = os.path.join(_STATE_DIR, "tool_embeddings.meta.json")
_REFRESH_INTERVAL = 60.0

_model = None
_model_failed = False
_index = None          # {"names": [..], "vecs": np.ndarray, "meta": {name: sig}}
_last_refresh = 0.0


def _log(msg):
    print(f"[embed-gate] {msg}")


def _get_model():
    global _model, _model_failed
    if _model is not None or _model_failed:
        return _model
    try:
        from model2vec import StaticModel
        t0 = time.time()
        _model = StaticModel.from_pretrained(MODEL_NAME)
        _log(f"model '{MODEL_NAME}' loaded in {time.time()-t0:.1f}s")
    except Exception as e:
        _model_failed = True
        _log(f"UNAVAILABLE ({type(e).__name__}: {e}) -- lexical fallback in effect")
    return _model


def available() -> bool:
    return _get_model() is not None


def _tool_text(dirpath, name):
    try:
        src = open(os.path.join(dirpath, name), encoding="utf-8", errors="replace").read(3000)
    except OSError:
        return ""
    m = re.search(r"#\s*does:\s*(.+)", src)
    d = m.group(1).strip() if m else ""
    if not d or d.upper().startswith("DESCRIBE"):
        return ""
    return f"{name.replace('_', ' ').replace('-', ' ')}: {d}"


# CANONICAL junk predicate for "is this file in tools/own actually a tool?".
# Was duplicated three ways (here, idea_gate, toolfind) and they DISAGREED:
# 2026-08-03 `b741e07` taught only tool-find about birth accidents (--show,
# dummy, own) and the creature's timestamped backups (X.bak_<epoch>), so those
# three files kept reaching the embedding index and the wake catalogue for two
# more days. Both other modules now delegate here; a test asserts all three
# agree on a fixture list, because this drifted once already.
JUNK_RE = re.compile(
    r'(^--|^\.|^(own|dummy)$|\.bak(_\d+)?$|\.broken|\.(tmp|swp|md|json|jsonl|log)$)')


def _is_junk(name):
    return bool(JUNK_RE.search(name))


def _sig(path):
    st = os.stat(path)
    return f"{st.st_mtime_ns}:{st.st_size}"


def _load_index():
    global _index
    if _index is not None:
        return
    try:
        import numpy as np
        meta = json.load(open(_INDEX_META))
        data = np.load(_INDEX_NPZ)
        _index = {"names": list(data["names"]), "vecs": data["vecs"], "meta": meta}
    except Exception:
        _index = {"names": [], "vecs": None, "meta": {}}


def refresh_standard():
    """Refresh the index over the standard live+attic mapping.

    Audit P3-D9: `refresh()` had exactly ONE caller (the idea-gate/oracle path),
    so tool-find and the curated catalogue -- the two surfaces the creature reads
    every cycle -- searched whatever index that path happened to leave behind. A
    tool born this cycle was invisible to tool-find until an ideation refill ran.
    Cheap to call from anywhere: refresh() is incremental AND self-throttled to
    once per _REFRESH_INTERVAL, so extra callers cost a clock comparison.
    The mapping lives here so there is one definition of it, not three.
    """
    mind = os.environ.get("VOLUME_MOUNT",
                          os.path.expanduser("~/growing-spine-mind"))
    refresh({"live": os.path.join(mind, "tools", "own"),
             "attic": os.path.join(mind, "tools", "attic")})


def refresh(dirs):
    """Incrementally (re)embed changed/new tool files in the given
    {label: dirpath} mapping. Names in the index are 'label:filename'."""
    global _index, _last_refresh
    if not available():
        return
    now = time.time()
    if now - _last_refresh < _REFRESH_INTERVAL and _index is not None:
        return
    _last_refresh = now
    import numpy as np
    _load_index()
    current, texts_to_embed, embed_keys = {}, [], []
    for label, d in dirs.items():
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for n in names:
            p = os.path.join(d, n)
            if not os.path.isfile(p) or _is_junk(n):
                continue
            key = f"{label}:{n}"
            try:
                sig = _sig(p)
            except OSError:
                continue
            current[key] = sig
            if _index["meta"].get(key) != sig:
                txt = _tool_text(d, n)
                if txt:
                    texts_to_embed.append(txt)
                    embed_keys.append(key)
    removed = [k for k in _index["meta"] if k not in current]
    if not texts_to_embed and not removed:
        return
    m = _get_model()
    new_vecs = m.encode(texts_to_embed) if texts_to_embed else None
    if new_vecs is not None:
        norms = np.linalg.norm(new_vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        new_vecs = new_vecs / norms
    keep_idx = [i for i, n in enumerate(_index["names"])
                if n in current and n not in embed_keys]
    names = [_index["names"][i] for i in keep_idx]
    vecs = _index["vecs"][keep_idx] if keep_idx else None
    if new_vecs is not None:
        names += embed_keys
        vecs = new_vecs if vecs is None else np.vstack([vecs, new_vecs])
    meta = {k: current[k] for k in names if k in current}
    _index = {"names": names, "vecs": vecs, "meta": meta}
    try:
        os.makedirs(_STATE_DIR, exist_ok=True)
        np.savez(_INDEX_NPZ, names=np.array(names), vecs=vecs)
        tmp = _INDEX_META + ".tmp"
        json.dump(meta, open(tmp, "w"))
        os.replace(tmp, _INDEX_META)
    except Exception as e:
        _log(f"index persist failed ({type(e).__name__}) -- in-memory only")
    _log(f"index: {len(names)} tools ({len(embed_keys)} embedded, {len(removed)} dropped)")


def top_matches(text, k=8, labels=None, exclude=None):
    """[(label:name, similarity)] best-first, or [] when unavailable.
    exclude: set of bare tool names to skip -- replay judges already-built
    tools against an index that CONTAINS them, so without exclusion the
    top hit is the tool itself (cos~1.0) and the verdict is corrupt
    (score from self, target from the nearest allowed name; 2026-07-17)."""
    if not available():
        return []
    _load_index()
    if _index["vecs"] is None or not len(_index["names"]):
        return []
    import numpy as np
    v = _get_model().encode([text])[0]
    n = np.linalg.norm(v)
    if n == 0:
        return []
    v = v / n
    sims = _index["vecs"] @ v
    order = np.argsort(-sims)
    out = []
    for i in order:
        name = _index["names"][i]
        if labels and name.split(":", 1)[0] not in labels:
            continue
        if exclude and name.split(":", 1)[1] in exclude:
            continue
        out.append((name, float(sims[i])))
        if len(out) >= k:
            break
    return out
