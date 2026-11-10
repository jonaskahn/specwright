# EARS as a sentence discipline

EARS offers a stable way to express system behaviour. It supplements a story rather
than replacing the actor's goal. Use a named system and an observable response, and
prefer one obligation per sentence.

| Pattern            | Structure                                              | Refund example                                                                                     |
|--------------------|--------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| Ubiquitous         | The system shall response.                             | The refund service shall record the currency for each request.                                     |
| State-driven       | While state, the system shall response.                | While a refund awaits approval, the refund service shall retain its calculated amount.             |
| Event-driven       | When event, the system shall response.                 | When an eligible request is submitted, the refund service shall assign “Pending approval”.         |
| Optional feature   | Where feature is present, the system shall response.   | Where assisted submission is enabled, the refund service shall record the submitting support role. |
| Unwanted behaviour | If unwanted condition, then the system shall response. | If the delivery age exceeds 14 days, then the refund service shall refuse creation.                |

Combined sentences retain order: While precondition, When event, the system shall
response. Do not reverse the clauses arbitrarily. “Where” identifies a product
variant, not an excuse to avoid deciding whether a requirement applies.

A sentence like “When a refund exceeds the agreed approval limit, the refund service
shall queue finance review” still needs a numeric limit, currency, owner and example
before review. Grammar improves consistency; it cannot supply missing policy.

Method reference: https://alistairmavin.com/ears/
