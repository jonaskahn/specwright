# Quality thresholds are proposals, not inherited policy

Ask which quality areas apply and who accepts their thresholds. A useful NFR states
metric, numeric threshold, operating conditions and verification method. Categories
below use the familiar ISO/IEC 25010:2011 names as prompts, with Safety added as a
separate prompt. This is not a claim to reproduce the different 2023 model.

| Area                   | Questions before agreement                                            |
|------------------------|-----------------------------------------------------------------------|
| Functional suitability | Which calculation oracle and correctness cases apply?                 |
| Performance efficiency | Which percentile, load, duration and measurement boundary?            |
| Compatibility          | Which supported clients and cooperating systems?                      |
| Usability              | Which actors, completion rate and assisted-use conditions?            |
| Reliability            | Which reporting window, exclusions, recovery time and loss tolerance? |
| Security               | Which authentication, authorization and threat cases?                 |
| Maintainability        | Which change verification and operational diagnostics?                |
| Portability            | Which deployment environments must work?                              |
| Safety                 | What harm needs a measurable prevention or detection check?           |
| Other                  | Which privacy, retention, audit, legal and localization duties apply? |

Three concrete candidate NFRs, to confirm with the relevant owners:

- NFR-REF-001: refund submission p95 latency below 2 seconds at 200 concurrent users,
  measured at the submission boundary over 15 minutes in staging with agreed data.
- Accessibility: refund entry meets WCAG 2.2 A and AA requirements, verified by
  automated checks plus manual keyboard, focus, reflow and error-recovery checks;
  include contrast criterion 1.4.3 and target-size criterion 2.5.8 in the test record.
- Audit/recovery: retain refund decision events for seven years, demonstrate recovery
  within four hours with no more than fifteen minutes of event loss in a restore test.

Three inadequate alternatives:

- “Very fast under heavy traffic” omits both traffic quantity and a latency measure.
- “Secure and legally compliant” names neither authorization outcomes nor legal scope.
- “99.999% available” omits the measurement period, service boundary and exclusions.

WCAG 2.2 AA means satisfying applicable A and AA success criteria, not just a scanner
score. Its principles are Perceivable, Operable, Understandable and Robust. New items
include AA focus-not-obscured minimum (2.4.11), non-drag alternatives (2.5.7), and
minimum target size (2.5.8, generally 24 by 24 CSS pixels, with defined exceptions).
Consistent help (3.2.6) and redundant entry (3.3.7) are A; accessible authentication
minimum (3.3.8) is AA. Do not mislabel AAA focus criteria as AA. Parsing criterion
4.1.1 is no longer part of 2.2. For text contrast, distinguish ordinary 4.5:1 and large
3:1 text under 1.4.3. Record applicable exceptions with evidence, not a blanket waiver.

Sources: https://www.w3.org/TR/WCAG22/ and
https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/
Category context: https://iso25000.com/index.php/en/iso-25000-standards/iso-25010
Numeric proposals above are kit examples, not requirements imposed by those sources.
