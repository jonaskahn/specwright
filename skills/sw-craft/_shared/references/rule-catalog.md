# Rule catalog

`_shared/scripts/sw_lint.py` checks decidable contracts only; wording quality stays a human
judgment. A finding prints `path:line: L-NNN message`. Pick the gate by what must be true next.

## Gates

| Gate | Exit | Blocks when |
| --- | --- | --- |
| `draft` | 10 | Shape or measurable rules fail. |
| `review` | 20 | The accept path or DoR fails (default); formal sign-off applies when required. |
| `publish` | 30 | The publish contract fails. |

Exit 0 pass; 2 usage or unexpected checker failure. No network.

## Rule families

| Family | Rules |
| --- | --- |
| Front matter and identity | L-001/L-002 name and ID grammar; L-003 duplicate ID; L-016 invalid status; L-043 scope, Jira key, https, refs |
| Names | L-054 `title` and `aliases` required (warning on an immutable snapshot); L-055 placeholder title, including a reserved feature with no Title in the registry |
| Citations and amendments | L-057 a citation names a missing, blank or changed line (weak or superseded source is a warning); L-062 a feature has a proposed amendment (review gate) |
| Shape | L-063 the INVEST table of an idea brief is malformed or hides a fail or unknown without a Reason |
| Illustration | L-064 a feature needs an illustration and has no picture and no dismissal (warning, review gate); L-070 a picture of the feature is not embedded in its story, or an embedded image is missing (warning, review gate); L-065 a diagram cites a withdrawn or missing ID (warning, review gate) |
| Visual references | L-066 an `assets:` ID is unregistered or not cited in Context or UI/UX (error, review gate); L-067 a mockup, link or image registered for the feature is missing from `assets:` (warning, review gate) |
| Epic objectives | L-068 an active epic names no business objective in `bo:` (warning, review gate); L-069 a feature and its epic share no business objective (warning, review gate) |
| Legacy names | L-056 a legacy ID (manifest `legacy_id_pattern`) in a body is not an alias of any artifact |
| Records and folders | L-058 unknown top-level folder (warning); L-059 a question without `affects`; L-060 a decision without decider and evidence; L-061 decider not in the manifest approvers (both a warning when sign-off is optional, an error when required) |
| Graph and plan | L-047 stale `.feature`; L-048 task trace; L-049 graph stale or missing; L-050/L-051 epic reference and scopes; L-052 Touches path; L-053 absolute registry path |
| Acceptance criteria | L-005 BO reference; L-007 Given/When/Then order; L-008 observable literal; L-014 clarification markers; L-017 numbered AC heading |
| Business rules and NFRs | L-010 metric, threshold, condition; L-011 worked example; L-012 UI states; L-013 exclusions with reason |
| Wording and leakage | L-009 vague word, ambiguous pronoun, unqualified "secure"; L-015 implementation choice; L-024 card/word cap and lone-side borders |
| Publish contract | L-018 open questions resolved; L-037; L-045 (met by a fresh accept when sign-off is optional); L-046 |
| Snapshot and drift | L-038 snapshot sections; L-039 contract checks; L-041/L-042 published draft changed without a CR; L-044 Jira status mapping |

Never weaken a rule, word list or threshold to pass a report. Record a waiver only where
the gate supports one.

## L-009 vague words

Matched exactly, case-insensitive, at word boundaries, in Goal, Acceptance criteria and
Business rules. A hit means: replace with actor, threshold and condition, or drop the
hedge. The word is not forbidden elsewhere. List (mirrors `BANNED` in sw_lint.py):

fast, quick, slow, efficient, responsive, scalable, robust, reliable, flexible, modern,
seamless, user-friendly, intuitive, easy, simple, straightforward, clean, nice, some,
many, few, several, most, various, a lot, minimal, large, small, soon, asap, quickly,
real-time, near real-time, immediately, periodically, should, may, might, could,
ideally, preferably, where possible, if possible, as appropriate, as needed, where
applicable, etc., and so on, and/or, tbd, tbc, appropriate, adequate, reasonable,
sufficient, best practice, industry standard, state of the art, compliant, handle
errors gracefully, all, always, never, every, any, ensure, 100%, support, handle,
manage, process, provide, allow, enable, optimize, improve, enhance, minimize, maximize.

## L-015 implementation terms

Matched in Goal, Acceptance criteria, Business rules and BO/BR cards (mirrors `IMPL` in
sw_lint.py): sql, endpoint, microservice, kafka, redis, react, database table, json,
http 500.

Fix: move the choice to design notes and restate the rule as actor + observable outcome.
Requirements say what the actor needs; design owns how.
