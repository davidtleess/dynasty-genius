# Reusable Input-Validation & Data-Quality Infrastructure — Design Spec

**Date:** 2026-07-23 · **Revision:** v3 (Codex round-1 C1–C10 + v2 review V2-1…V2-7, all ACCEPT; precision only — v2 architecture unchanged)
**Status:** DRAFT — awaiting cockpit CLEAR, then David authorization
**Authoring lane:** Claude (spec + framing + disposition) · Codex (sole binding reviewer + RED author + contract-surface confirmation) · Gemini (Operations & Telemetry seat — awareness copy; telemetry on request, no judgment)
**Authoritative path (spec-of-record — C1):** `docs/superpowers/specs/2026-07-23-reusable-validation-infrastructure-design.md`. Origin **spike brief** (separate doc): `docs/strategies/2026-07-23-scalable-input-validation-spike.md`.
**Scope (one line):** a shared `src/dynasty_genius/validation/` runtime module (generic helpers + a marker/named exception-base pair + a subtype-preserving, TOTAL reason registry + an adapter/case protocol) **plus** a Hypothesis property harness — **used only by NEW post-QB-1 code**. NOT a retrofit of D3-a, NOT a migration of any existing subsystem's exceptions, NOT a runtime-schema adoption, NOT anything that blocks QB-1.

**Sequencing (C2):** lands **AFTER the entire QB-1 arc** (D3-b/c → D4 → D5 → F33 → H5). No QB-1 build phase remains after H5, so **this increment is NOT adopted by the QB-1 arc**; D3-b/c through H5 stay fully hand-written (may reuse lessons/strategy ideas locally, cannot import an unlanded increment). Payoff is **future post-QB-1** validation + ingestion.

---

## 1. Problem (measured, not inferred)

D3-a's input validation hardened over **6 Codex rounds** into **13 real defects**, one family (leakage-exclusion · type/finiteness robustness · numeric-edge totality · hostile-value rendering), found one at a time. That manual per-increment discovery does not scale to future validation/ingestion work, and DG's validation seams are fragmented and un-reused.

**Root cause (two parts, `file:line`):**

**(a) Manual adversarial discovery.** Codex hand-crafted the numeric/rendering edges (`10**10000`, `1e308`, `5e-324`, a raising-`__repr__` object) across rounds 3–5. No automated generator exists.

**(b) Fragmented, package-local seams.** `grep -rnE "^class .*(Error|Failure)\(Exception\)" src/ app/` → **9** Exception subclasses, no shared base, **0** external importers of the qb_validation guards/errors seams. **Corrected taxonomy (C3):** only **TWO** carry a `(reason, detail)` named-reason contract — `QBValidationFailure` (`eval/qb_validation/errors.py:11`), `ValidationIngestError` (`adapters/nflreadpy_qb_adapter.py:110`). The other **seven are message-only** (FC capture ×2, `ProvenanceConfigError` + its `ModelRegistryLoadError`/`RuntimeEnvironmentError` graph, CaptureHealth/TierReadiness/Health config errors, `LeaguePulseDependencyError` — dynamic messages asserted in tests / surfaced in HTTP 503 detail). Treating a message as a "registered reason" is meaningless; they are out of scope here (§3).

**Reproduced — the fix works (the David-worded probe):** a Hypothesis property against a pre-C5 `folds.py` snapshot re-found the family in seconds (`bc353fb` untouched): `median([8.988e307,8.988e307])=inf` (overflow, automatic); `OverflowError: int too large to convert to float` (huge-int, wide-int strategy); `median 0.0 outside [5e-324,5e-324]` (subnormal, endpoint property + subnormal strategy). Honest limit (→ F9): plain `st.floats()` at 5,000 examples missed the `[5e-324,5e-324]` pair — razor edges need targeted strategies. **Consequence:** future work re-pays the manual cost; fragmented reasons resist reuse and invite drift.

---

## 2. Design

Two layers — runtime infra (new-code reuse consolidation) + a test harness (automated discovery). Nothing here changes any existing subsystem's behavior in the phase-1 default.

### 2.1 Runtime: `src/dynasty_genius/validation/`

**(a) A marker/named base PAIR (C3):**

```python
# validation/errors.py
class ValidationError(Exception): ...                 # MARKER base
class NamedValidationFailure(ValidationError):        # reason-bearing
    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason, self.detail = reason, detail
        super().__init__(f"{reason}: {detail}" if detail else reason)
```

**Binding compatibility invariants for any family that later adopts (phase 2; B/C/V2-4):** import path + class name, the `(reason, detail="")` constructor, `.reason`/`.detail`, `str(exc)` stay **byte-identical**; the concrete class a site raises/catches stays the subsystem class; existing subclass relations and `except QBValidationFailure` behavior remain; the `TypeError`(API-misuse)/named-failure(data-corruption) split holds. **Additive-MRO law (V2-4):** base-widening DOES change the MRO — "MRO preserved" is retired — the ONLY permitted delta is the pinned insertion of `NamedValidationFailure → ValidationError` immediately before `Exception`; the exact post-adoption MRO is pinned in the phase-2 RED only. F5 must also preserve the `ProvenanceConfigError` subclass graph if that family is in scope.

**(b) A subtype-preserving, TOTAL reason registry/factory (C4, V2-3, V2-5):**

```python
# validation/reasons.py — reasons are an ORDERED declaration sequence (dup-detectable), then frozen
class ReasonFamily:
    def __init__(self, exc_type, reasons: Sequence[str]):
        self._exc = exc_type
        self._reasons = _frozen_no_dups(reasons)         # build-time error on a duplicate; requires "unregistered_reason" present
    def refuse(self, reason: object, detail: object = "") -> NoReturn:
        if type(reason) is not str or reason not in self._reasons:   # type-check BEFORE hash/membership (V2-3)
            raise self._exc("unregistered_reason", _safe_repr(reason))
        raise self._exc(reason, _coerce_detail(detail))              # detail: exact str, else bounded safe_repr (V2-3)
```

- **Totality (V2-3):** `type(reason) is str` is checked **before** any hash/membership, so an unhashable/hostile reason (list, hostile `__hash__`, str-subclass) can never raise before the named `unregistered_reason`; a non-plain-string reason AND any `detail` route through bounded `safe_repr`, so a raising `__str__` cannot violate F4. `unregistered_reason` must itself be present at construction.
- **Ownership/duplicates (V2-5):** an **ordered sequence** (not a `frozenset`, which erases dups) → a duplicate reason **within one family's declaration** is a build-time error. **Cross-family law:** identical reason STRINGS across independent subsystem families are LEGAL (each bound to its own exception type); duplicate family identity/binding is not.
- **Escape hatch:** direct `raise QBValidationFailure(...)` stays permissive (does NOT validate the registry) → existing D3-a call sites byte-unchanged; only NEW code opts into `.refuse()`, which owns the totality guarantees.

**(c) Reusable helpers** (new code; D3-a inline copies stay): `is_finite_real`, total `median`, `safe_repr`, `require_plain_str` — behavior-pinned to D3-a (F7).

**(d) Domain constants stay module-owned (C8).** The shared module **accepts declared contracts as INPUTS**, never mirrors football/model constants: Engine-B prohibited features owned by `engine_b_contract.py`; QB draft-capital owned by the QB module. No second source of truth, no reverse-import cycle.

### 2.2 Test harness: `tests/property/` — Hypothesis, adapter-driven

**Adapter/case protocol (C5).** Each registered validator declares: an argument strategy, a success oracle, a **recursive/named numeric-output extractor** (a nested `inf` is caught — F2), a mutation policy, an allowed reason family, and a precedence oracle. Generated inputs are **TAGGED** `valid | api_misuse | data_corruption`.

**Named non-empty initial adapter set (V2-6 — the harness cannot pass vacuously).** Phase 1 registers an EXACT, asserted-non-empty reference set:
- **`ref_numeric`** — a hermetic reference numeric-median validator built in `tests/property/` (**F1/F2 subject**); proves the protocol + numeric totality; validates NO QB production code.
- **`harness_imputer`** — a **read-only** test-harness adapter around the existing `folds.fit_train_only_imputer` seam (**F3 subject**): the metamorphic leakage oracle runs against a REAL train/test-fit seam — **test-harness adoption only, NOT production-runtime adoption**. The draft-capital contract is **imported from its QB owner** (`folds._DRAFT_CAPITAL_FEATURES`) or injected as a test contract — never copied (C8).
`test_registry_exact_set` asserts the registry equals `{"ref_numeric","harness_imputer"}` so a stripped registry cannot false-green F1/F2/F3.

**Property oracle (C5 — the split preserved):** `valid`→success+postconditions; `api_misuse`→**`TypeError` only**; `data_corruption`→**bound subtype + REGISTERED reason**; never a bare/unclassified exception; every numeric output finite-or-named-refusal; refusal rendering never crashes.

**CI determinism — ONE profile, concrete values (C7, V2-7).** Pin `hypothesis==6.161.0` (the probed version) in `requirements-dev.txt`; the property lane runs `@settings(max_examples=500, deadline=None, derandomize=True, database=None)` (a seed overrides `derandomize`; `derandomize=True` implies `database=None`). Mandatory razor edges use `@example`/enumeration and do NOT rely on `max_examples`. (`6.161.0`/`500` are concrete pins, revisitable as a named David pre-RED input; an example database, if ever used, is a separate replay artifact.)

---

## 3. Out of scope (named, not hidden)

1. **No retrofit of committed D3-a (`bc353fb`)** — a "backport D3-a onto shared infra" increment can be named later.
2. **No migration of the seven message-only families (C3)** — each is a separate future increment with its own reason-taxonomy + message + route pins.
3. **PIN-FORBID guard (C-A, V2-2).** MUST NOT edit `docs/validation/2026-07-21-qb-1-study-registration.json`, the canonicalization/hash semantics in `registration.py`, or the runner's expected-hash constant. F-pin + F-pin-2 pin all three (§4).
4. **No pandera/Pydantic/GX** (Option B/C) — deferred to new ingestion boundaries.
5. **No model-output / No-Verdict change, no new data source/feature.** `decision_supported=false` untouched; market-out-of-model wall unaffected (leakage properties strengthen evidence about it).

**[DAVID — scope choices, surfaced not decided]:** (i) does THIS increment include **phase-2 adoption of the two already-named families** (with exact compat pins + base-widening), or is it **strictly phase-1 new-code-only**? *Default: phase-1-only.* (ii) any **D3-b-onward local adoption** (needs new David authority per C2), or QB-1 stays fully hand-written? *Default: fully hand-written.* (iii) confirm/adjust the concrete CI pins `hypothesis==6.161.0`, `max_examples=500` (V2-7).

---

## 4. Falsification seeds — the RED matrix (TWO manifests per David's §3(i) choice — V2-1)

Test paths: `tests/property/test_reusable_validation_red.py` + `tests/contract/test_validation_infra_red.py`. All hermetic. **The RED author builds exactly ONE manifest, selected by David's phase choice.**

- **Phase-1 manifest (default, new-code only):** F1, F2, F3, F4, F6, F7, F8, F9, F-pin, F-pin-2, F-reg, F-reg-set, F10. **F5 and F-route are PHASE-2-ONLY** (they touch an existing family/route) and are absent here.
- **Phase-1+2 addendum (only if David scopes it in):** add F5, and F-route if a route family is included.

| # | Seed | Required behavior |
|---|---|---|
| **F1** | `ref_numeric` + `harness_imputer` cases tagged valid/api_misuse/data_corruption | valid→success+postconditions; api_misuse→**TypeError only**; data_corruption→bound subtype+registered reason; never bare/unclassified |
| **F2** | `ref_numeric` over `hostile_numeric` with the recursive extractor | finite-or-named-refusal at every nesting depth; nested `inf` caught; never bare OverflowError |
| **F3** | metamorphic leakage on `harness_imputer`: train FIXED, ≥2 test variants | identical fitted state/medians/transformed-train; draft-capital never enters fitted stats (contract IMPORTED from QB owner, not copied); state/provenance defined pre-run |
| **F4** | refusal rendering over `hostile_objects` (`10**10000`, raising `__repr__`/`__str__`, str-subclass) | bounded `safe_repr`; never raises; intended reason/`TypeError` still surfaces |
| **F5** *(phase-2 only)* | `QBValidationFailure`/`ValidationIngestError` (+ ProvenanceConfigError graph if in scope) | `isinstance(_, ValidationError)`; exact class identity/import/constructor/`.reason`/`.detail`/`str(exc)`; still raises its own subtype; **additive-MRO law** — only delta = `NamedValidationFailure→ValidationError` before `Exception`, exact post-adoption MRO pinned here |
| **F6** | `refuse("<unregistered>")`, an unhashable/hostile-`__hash__`/str-subclass reason, a raising-`__str__` detail | subsystem-subtype `unregistered_reason` with bounded detail; `type(reason) is str` before membership; never bare, never a rendering crash |
| **F7** | helpers on D3-a boundary vectors (`10**10000`,`1e308`,`5e-324`,`-5e-324`,`±0.0`, both-sign near-max, empty+heterogeneous median inputs, `RaisingReprStr`) | byte-match to D3-a; finite+endpoint-preserving; no crash |
| **F8** | property suite under the pinned profile, twice; + explicit-corpus replay | **stable pass/fail** + `@example` vectors execute; NOT "identical generated set across tool upgrades" |
| **F9** | deterministic strategy-adequacy: local mutant `median=a/2+b/2` + targeted signed-subnormal strategy + endpoint property, razor edges via `@example` | the targeted strategy FINDS/executes the subnormal counterexample |
| **F-pin** | `registration.json`: the `head -c 11008` canonical body AND the raw whole file | canonical-body SHA-256 == `37065566a9b372e329454cc51edbcf3de724fd1e5cc57a2f15cc547b1ae54c9d` (the SEMANTIC pin; the file is 11,009 bytes with a trailing LF); raw whole-file SHA-256 == `eb56943a17549f268894128a9f4a7b9fe421d542bae9538f5781d9f667b13782` (byte identity, SEPARATE assertion) — V2-2 |
| **F-pin-2** | change-set path guard: `registration.py` canonicalization/hash symbols + the runner's expected-hash constant | baseline-hashed/behaviorally pinned unchanged (a JSON-only test cannot see these two forbidden surfaces — V2-2); exact paths/symbols named once H5 exists |
| **F-reg** | duplicate reason within one declaration; registry/factory import-cycle; import-order independence | build-time duplicate error (ordered-sequence input); no import-order mutation; no cycle |
| **F-reg-set** | the phase-1 adapter registry | equals the exact non-empty set `{"ref_numeric","harness_imputer"}` — a stripped registry fails (V2-6) |
| **F10** | a validator input violating two invariants at once | the DECLARED per-validator precedence oracle returns the pinned reason deterministically; a second failure never masks it |
| **F-route** *(phase-2 only, if a route family is in scope)* | catch→503 + sanitized `decision_supported=false` + League Pulse `str(exc)` in HTTP detail | exact translation preserved |

---

## 5. Sequence (cockpit-TDD)

1. **Cockpit CLEAR:** Claude framing (v3) → Codex challenge (round-1 + v2 review, all dispositioned) → this v3 → Codex technical review → CLEAR. Gemini: awareness.
2. **David authorizes** the RED **and settles §3 scope choices** — phase-1 vs phase-1+2 (§3(i)), any D3-b adoption (§3(ii)), the CI pins (§3(iii)).
3. **Codex authors the RED** — **exactly the manifest selected by David's phase choice** (phase-1 default, or phase-1+2), demonstrably red on `main` (V2-1).
4. **Claude GREEN** — matches the SELECTED manifest: phase-1 = `validation/` module + property harness (new code only, no existing family touched); phase-1+2 = also the two concrete-family base-widening changes with their compatibility pins. Full gate (import surface); self-probes the matrix.
5. **Codex CLEAR.**
6. **David-authorized:** commit (rides `hypothesis==6.161.0` dev-dep) → push/CI. CI is the merge gate.

**POST-QB-1 increment — starts only after H5.**

---

## 6. Risks

| # | Risk | Mitigation |
|---|---|---|
| **R1** | *(removed by C9)* — scope is phase-1 new-code only | No existing subsystem modified in the default; phase-2 (two named families) only if David scopes it; message-only migrations (phase 3) are separate |
| **R2** | Hypothesis CI flakiness | Pinned `6.161.0` + single profile (`max_examples=500, derandomize=True, database=None, deadline=None`); `@example` regression vectors; F8 asserts stable pass/fail, not cross-version reproducibility |
| **R3** | **Contract break** — a preserved family's surface changes | Compatibility matrix (C — class identity/import/constructor/attrs/`str`/catch-translation/success/mutation/precedence/reasons; **additive-MRO law, NOT "MRO preserved"** — V2-4) pinned by the phase-2 F5/F-route rows; F7 pins helpers. The sealed pin is guarded by **F-pin (semantic body `37065566…` + raw file `eb56943a…`) AND F-pin-2 (`registration.py` hash-semantics + runner-hash)** — R3 claims the full §3 forbid-list is guarded only because all three surfaces are executably pinned (V2-2) |
| **R4** | False-green (under-covering strategies; vacuous harness) | F9 deterministic strategy-adequacy; **F-reg-set** asserts the non-empty adapter registry so a stripped harness fails (V2-6) |
| **R5** | Domain-constant duplication / reverse-import cycle | C8/§2.1(d): constants module-owned, injected as contracts; F-reg pins import-order independence + no cycle |
| **R6** | Scope creep back to big-bang | §3 names phase-2/phase-3 + the D3-a backport as separate David-sequenced follow-ups |

**What this does NOT prove:** that Hypothesis finds every future edge (violations of *stated* properties within *covered* regions — R4); that any later message-only migration is free; or that any increment is defect-free. It raises the floor; it is not an oracle.

---

*Spec of record for David's review — not a build. No implementation, dependency change, commit, push, phase-advance, or study execution is taken or authorized. Routing to the cockpit is David's word.*
