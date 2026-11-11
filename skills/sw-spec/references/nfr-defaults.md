# Quality thresholds are proposals, not inherited policy

Ask which quality areas apply and who accepts the thresholds. A usable NFR states metric,
numeric threshold, operating conditions and verification method. Areas below follow
ISO/IEC 25010:2011 names, plus Safety, as prompts.

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

WCAG 2.2 AA means meeting every applicable A and AA success criterion, not a scanner score.

- New in 2.2, AA: focus not obscured, minimum (2.4.11); dragging alternatives (2.5.7); target size, minimum (2.5.8, generally 24 by 24 CSS pixels, defined exceptions); accessible authentication, minimum (3.3.8).
- New in 2.2, A: consistent help (3.2.6); redundant entry (3.3.7).
- Do not label AAA focus criteria as AA. Criterion 4.1.1 (Parsing) is not part of 2.2.
- Contrast (1.4.3): ordinary text 4.5:1, large text 3:1.
- Record applicable exceptions with evidence, never a blanket waiver.

Sources: https://www.w3.org/TR/WCAG22/ and
https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/
Category context: https://iso25000.com/index.php/en/iso-25000-standards/iso-25010
Numeric proposals above are kit examples, not requirements imposed by those sources.
