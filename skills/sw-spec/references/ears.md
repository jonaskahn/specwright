# EARS sentence patterns

EARS expresses system behaviour in a stable form. It supplements the actor's goal in the
story; it does not replace it. Name the system, state an observable response, one
obligation per sentence.

| Pattern | Structure | Example |
| --- | --- | --- |
| Ubiquitous | The system shall response. | The refund service shall record the currency for each request. |
| State-driven | While state, the system shall response. | While a refund awaits approval, the refund service shall retain its calculated amount. |
| Event-driven | When event, the system shall response. | When an eligible request is submitted, the refund service shall assign "Pending approval". |
| Optional feature | Where feature is present, the system shall response. | Where assisted submission is enabled, the refund service shall record the submitting support role. |
| Unwanted behaviour | If unwanted condition, then the system shall response. | If the delivery age exceeds 14 days, then the refund service shall refuse creation. |

- Combined order: While precondition, When event, the system shall response. Do not reverse it.
- "Where" marks a product variant; it never excuses skipping the decision whether a requirement applies.
- Grammar does not supply policy. "When a refund exceeds the agreed approval limit, the
  refund service shall queue finance review" still needs a numeric limit, currency, owner
  and example before review.

Reference: https://alistairmavin.com/ears/
