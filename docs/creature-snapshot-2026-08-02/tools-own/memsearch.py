#!/usr/bin/env python3
"""
memsearch – fast free‑text query over a persistent JSONL memory file.

Usage:
    memsearch.py "<query>" <memory.jsonl> [N]

Arguments:
    <query>        The search string.
    <memory.jsonl> Path to a line‑delimited JSON file, each line a record with a 'text' field.
    N              (optional) Number of top results to return (default 3).

Output:
    Prints the top‑N matching records, one per line, in descending relevance order.
    Each line is the original JSON record (compact, no extra whitespace).

Implementation notes:
    * Pure Python 3, only the standard library.
    * Builds a TF‑IDF vector for the query and each document on the fly.
    * Uses cosine similarity; ties are broken by document order.
    * Handles missing or malformed lines gracefully (skips them with a warning).
"""

import sys
import json
import math
import re
from collections import Counter, defaultdict

def tokenize(text):
    # Very simple tokeniser: lower‑case, keep alphanumerics only
    return re.findall(r'\b\w+\b', text.lower())

def tfidf_vectors(docs, query_tokens):
    """Return TF‑IDF vectors for all docs and the query."""
    # Document frequencies
    df = Counter()
    doc_terms = []
    for tokens in docs:
        uniq = set(tokens)
        df.update(uniq)
        doc_terms.append(Counter(tokens))

    # IDF (add 1 to avoid division by zero)
    total_docs = len(docs)
    idf = {term: math.log((total_docs + 1) / (df[term] + 1)) + 1 for term in df}

    # TF‑IDF for each doc
    doc_vecs = []
    for term_counts in doc_terms:
        vec = {term: (count / sum(term_counts.values())) * idf[term]
               for term, count in term_counts.items()}
        doc_vecs.append(vec)

    # TF‑IDF for the query
    query_counts = Counter(query_tokens)
    qvec = {term: (count / sum(query_counts.values())) * idf.get(term, math.log(total_docs + 1))
            for term, count in query_counts.items()}

    return doc_vecs, qvec

def cosine_similarity(vec_a, vec_b):
    # Dot product
    dot = sum(vec_a.get(k, 0) * vec_b.get(k, 0) for k in set(vec_a) | set(vec_b))
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

def main():
    if len(sys.argv) < 3:
        print("Usage: memsearch.py \"<query>\" <memory.jsonl> [N]", file=sys.stderr)
        sys.exit(1)

    query = sys.argv[1]
    memory_path = sys.argv[2]
    top_n = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    # Load records
    records = []
    docs = []
    with open(memory_path, 'r', encoding='utf-8') as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                text = obj.get('text') or obj.get('content') or ''
                tokens = tokenize(text)
                records.append((obj, tokens))
                docs.append(tokens)
            except json.JSONDecodeError:
                print(f"Warning: line {lineno} is not valid JSON – skipping.", file=sys.stderr)

    if not records:
        print("No valid records found in the memory file.", file=sys.stderr)
        sys.exit(1)

    query_tokens = tokenize(query)
    doc_vecs, query_vec = tfidf_vectors(docs, query_tokens)

    # Compute similarities
    scores = []
    for idx, vec in enumerate(doc_vecs):
        sim = cosine_similarity(vec, query_vec)
        scores.append((sim, idx))

    # Rank and output top‑N
    for sim, idx in sorted(scores, reverse=True)[:top_n]:
        record_json = json.dumps(records[idx][0], separators=(',', ':'))
        print(record_json)

if __name__ == "__main__":
    main()
