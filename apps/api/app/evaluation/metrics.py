"""Pure metric functions shared by the Phase-4 harnesses (no I/O)."""

from typing import Dict, Hashable, Iterable, List, Optional, Sequence, Tuple


def safe_div(num: float, den: float) -> Optional[float]:
    """num/den, or None when the denominator is zero (an undefined metric is never 0)."""
    return None if den == 0 else num / den


def precision_recall_f1(tp: int, fp: int, fn: int) -> Dict[str, Optional[float]]:
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    if precision is None or recall is None or (precision + recall) == 0:
        f1 = None if (precision is None or recall is None) else 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1}


def accuracy(correct: int, total: int) -> Optional[float]:
    return safe_div(correct, total)


def binary_counts(pairs: Iterable[Tuple[bool, bool]]) -> Dict[str, int]:
    """pairs of (gold, predicted) booleans -> tp/fp/fn/tn."""
    tp = fp = fn = tn = 0
    for gold, pred in pairs:
        if gold and pred:
            tp += 1
        elif pred and not gold:
            fp += 1
        elif gold and not pred:
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def multiset_match_counts(gold: Sequence[Hashable], predicted: Sequence[Hashable]) -> Dict[str, int]:
    """tp/fp/fn when comparing two lists as multisets (a duplicate must be found twice)."""
    remaining: Dict[Hashable, int] = {}
    for g in gold:
        remaining[g] = remaining.get(g, 0) + 1
    tp = 0
    for p in predicted:
        if remaining.get(p, 0) > 0:
            remaining[p] -= 1
            tp += 1
    return {"tp": tp, "fp": len(predicted) - tp, "fn": len(gold) - tp}


def edit_distance(a: Sequence, b: Sequence) -> int:
    """Levenshtein distance over any two sequences (characters or words)."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def _words(text: str) -> List[str]:
    return text.split()


def wer(reference: str, hypothesis: str) -> Optional[float]:
    """Word error rate = word edit distance / reference word count (None if the reference is empty)."""
    ref = _words(reference)
    return safe_div(edit_distance(ref, _words(hypothesis)), len(ref))


def cer(reference: str, hypothesis: str) -> Optional[float]:
    """Character error rate = char edit distance / reference length. Whitespace runs are
    collapsed first so line wrapping is not scored as an OCR error."""
    ref = " ".join(reference.split())
    hyp = " ".join(hypothesis.split())
    return safe_div(edit_distance(ref, hyp), len(ref))


def corpus_error_rate(pairs: Sequence[Tuple[str, str]], unit: str) -> Optional[float]:
    """Corpus-level WER/CER: total edits / total reference length (not a mean of ratios)."""
    edits = total = 0
    for ref, hyp in pairs:
        if unit == "word":
            r, h = _words(ref), _words(hyp)
        else:
            r, h = list(" ".join(ref.split())), list(" ".join(hyp.split()))
        edits += edit_distance(r, h)
        total += len(r)
    return safe_div(edits, total)
