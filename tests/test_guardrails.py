import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.security.prompt_guard import check_prompt_injection
from app.security.pii import mask_pii
from tests.eval_dataset import INJECTION_CASES, PII_CASES

# * Test whether prompt injection detection works correctly
def test_injection_detection_eval():
    results = []    # * recording every test result
    for prompt, should_be_blocked, note in INJECTION_CASES:
        actual = check_prompt_injection(prompt)
        passed = actual == should_be_blocked
        results.append((passed, prompt, should_be_blocked, actual, note))

    passed_count = sum(1 for r in results if r[0])
    total = len(results)

    print(f"\n--- Prompt Injection Eval: {passed_count}/{total} passed ---")
    for passed, prompt, expected, actual, note in results:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] expected_blocked={expected} actual_blocked={actual} | {note}")
        print(f"       prompt: {prompt[:60]}")

    known_gap_failures = [r for r in results if not r[0] and "KNOWN GAP" in r[4]]
    unexpected_failures = [r for r in results if not r[0] and "KNOWN GAP" not in r[4]]

    assert len(unexpected_failures) == 0, f"Unexpected firewall failures: {unexpected_failures}"


def test_pii_masking_eval():
    results = []
    for text, should_contain, should_not_contain, note in PII_CASES:
        masked = mask_pii(text)

        contains_ok = should_contain is None or should_contain in masked
        not_contains_ok = should_not_contain is None or should_not_contain not in masked
        passed = contains_ok and not_contains_ok

        results.append((passed, text, masked, note))

    passed_count = sum(1 for r in results if r[0])
    total = len(results)

    print(f"\n--- PII Masking Eval: {passed_count}/{total} passed ---")
    for passed, original, masked, note in results:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {note}")
        print(f"       original: {original}")
        print(f"       masked:   {masked}")

    known_gap_failures = [r for r in results if not r[0] and "KNOWN FALSE POSITIVE" in r[3]]
    unexpected_failures = [r for r in results if not r[0] and "KNOWN FALSE POSITIVE" not in r[3]]

    assert len(unexpected_failures) == 0, f"Unexpected PII masking failures: {unexpected_failures}"