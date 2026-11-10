# banned words

`L-009` flags vague words in Goal, Acceptance criteria and Business rules prose. The
checker matches the exact word, case-insensitive, with word boundaries; a hit means
"replace with actor, threshold and condition", not that the word is forbidden everywhere.

## The list (as shipped in the checker)

fast, quick, slow, efficient, responsive, scalable, robust, reliable, flexible, modern,
seamless, user-friendly, intuitive, easy, simple, straightforward, clean, nice, some,
many, few, several, most, various, a lot, minimal, large, small, soon, asap, quickly,
real-time, near real-time, immediately, periodically, should, may, might, could,
ideally, preferably, where possible, if possible, as appropriate, as needed, where
applicable, etc., and so on, and/or, tbd, tbc, appropriate, adequate, reasonable,
sufficient, best practice, industry standard, state of the art, compliant, handle
errors gracefully, all, always, never, every, any, ensure, 100%, support, handle,
manage, process, provide, allow, enable, optimize, improve, enhance, minimize, maximize.

## How to resolve

Replace the vague term with a concrete actor, threshold and condition, or remove the
hedge when the requirement does not need it. Keep the list as the checker defines it;
word-list changes are code changes, never a way to silence a real finding.
