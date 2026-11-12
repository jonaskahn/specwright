// One shape language for every status. Colour never carries meaning alone.

export type MarkShape = 'circle' | 'check' | 'triangle' | 'square' | 'diamond' | 'hollow';
export type Tone = 'ok' | 'warn' | 'danger' | 'neutral' | 'accent';

export interface Look {
  shape: MarkShape;
  tone: Tone;
  label: string;
}

export const RUNGS = ['draft', 'in-review', 'ready-to-publish', 'published', 'ready-for-dev'] as const;

const LABELS: Record<string, string> = {
  draft: 'Draft',
  'in-review': 'In review',
  'ready-to-publish': 'Accepted',
  published: 'Published',
  'ready-for-dev': 'Ready for development',
  superseded: 'Superseded',
  withdrawn: 'Withdrawn',
};

export function label(value: string | null): string {
  if (!value) return 'Not set';
  return LABELS[value] ?? value.charAt(0).toUpperCase() + value.slice(1).replace(/-/g, ' ');
}

export function stateLook(state: string, condition: string | null = null): Look {
  const text = label(state);
  if (state === 'superseded' || state === 'withdrawn') return { shape: 'square', tone: 'neutral', label: text };
  if (condition === 'blocked') return { shape: 'triangle', tone: 'danger', label: text };
  switch (state) {
    case 'ready-for-dev':
      return { shape: 'check', tone: 'ok', label: text };
    case 'published':
      return { shape: 'circle', tone: 'ok', label: text };
    case 'ready-to-publish':
      return { shape: 'circle', tone: 'accent', label: text };
    case 'in-review':
      return { shape: 'diamond', tone: 'warn', label: text };
    case 'draft':
      return { shape: 'hollow', tone: 'neutral', label: text };
    default:
      return { shape: 'hollow', tone: 'neutral', label: text };
  }
}

/** Generic status words used by records, sources, tasks and registry rows. */
export function wordLook(value: string | null): Look {
  const text = label(value);
  switch (value) {
    case 'open':
    case 'proposed':
    case 'candidate':
    case 'in-review':
      return { shape: 'diamond', tone: 'warn', label: text };
    case 'answered':
    case 'accepted':
    case 'applied':
    case 'approved':
    case 'active':
    case 'ready':
    case 'published':
    case 'resolved':
    case 'pass':
      return { shape: 'check', tone: 'ok', label: text };
    case 'withdrawn':
    case 'superseded':
    case 'rejected':
    case 'raw':
      return { shape: 'square', tone: 'neutral', label: text };
    case 'fail':
    case 'missing':
    case 'unresolved':
      return { shape: 'triangle', tone: 'danger', label: text };
    default:
      return { shape: 'hollow', tone: 'neutral', label: text };
  }
}

export type RungStep = 'done' | 'current' | 'blocked' | 'todo' | 'off';

/** Where each rung stands for a feature in `state`. */
export function rungSteps(state: string, condition: string | null): RungStep[] {
  if (state === 'superseded' || state === 'withdrawn') return RUNGS.map(() => 'off' as const);
  const at = RUNGS.indexOf(state as (typeof RUNGS)[number]);
  return RUNGS.map((_, i) => {
    if (at < 0) return 'todo';
    if (i < at) return 'done';
    if (i === at) return condition === 'blocked' ? 'blocked' : state === 'ready-for-dev' ? 'done' : 'current';
    return 'todo';
  });
}

/** A rule that fires twice is named once: "review: fail L-005, L-030, L-005" reads "review: fail L-005, L-030". */
export function tidyLint(result: string): string {
  const found = /^(.*?)([A-Z]+-\d+(?:\s*,\s*[A-Z]+-\d+)*)\s*$/.exec(result);
  if (!found) return result;
  const codes = [...new Set(found[2].split(/\s*,\s*/))];
  return found[1] + codes.join(', ');
}

/** The illustration chip. Check is neutral: it asks for a look, and it does not block. */
export function illustrationLook(value: string | null): Look {
  switch (value) {
    case 'illustrated':
      return { shape: 'check', tone: 'ok', label: 'Illustrated' };
    case 'needs illustration':
      return { shape: 'triangle', tone: 'warn', label: 'Needs illustration' };
    case 'no illustration':
      return { shape: 'square', tone: 'neutral', label: 'No illustration' };
    case 'check illustration':
      return { shape: 'diamond', tone: 'neutral', label: 'Check illustration' };
    default:
      return { shape: 'hollow', tone: 'neutral', label: value ? label(value) : 'Illustration not set' };
  }
}

export function lintLook(result: string | null): Look {
  if (result) result = tidyLint(result);
  if (!result) return { shape: 'hollow', tone: 'neutral', label: 'Not run' };
  if (/fail/i.test(result)) return { shape: 'triangle', tone: 'danger', label: result };
  if (/pass/i.test(result)) return { shape: 'check', tone: 'ok', label: result };
  return { shape: 'hollow', tone: 'neutral', label: result };
}
