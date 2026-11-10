# Behavior before layout

Choose the distinction the consumer must test, then one type. These patterns are
Specwright's own requirement-review prompts, not another diagramming runtime.

| Uncertainty | Required evidence | Layout |
| --- | --- | --- |
| Many inputs bottleneck at one owner | actual inputs, capacity and queue meaning | data-flow |
| A rough request becomes a durable requirement | source, transformation and saved artifact | process |
| Two policy outcomes diverge | concrete inputs, guards and first differing rule | flowchart |
| Boundaries constrain data access | explicit zones and permitted/forbidden relations | architecture |
| Responsibility changes at a layer | enforcement owner and observable result | layer-stack |
| A feature decomposes into testable pieces | parentage, source IDs and scope boundary | tree |
| An object waits, retries or terminates | named states, events and guards | state |
| Change propagates to shared consumers | saved dependency edges, not inferred approval | dependency |

Do not mix layout grammars to imply missing policy. Put UNKNOWN or a Q record in
the source; the renderer requires the fields necessary for a truthful picture.
Each arrow must answer a question. A grouping alone does not establish causality.
