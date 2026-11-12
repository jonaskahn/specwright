import { describe, expect, it } from 'vitest';
import { lintLook, tidyLint } from '../src/lib/status';

describe('lint result words', () => {
  it('names a rule that fires twice only once, keeping the order', () => {
    expect(tidyLint('review: fail L-005, L-030, L-005, L-010')).toBe('review: fail L-005, L-030, L-010');
    expect(tidyLint('review: fail L-005,L-005')).toBe('review: fail L-005');
  });

  it('leaves other results alone', () => {
    expect(tidyLint('review: pass')).toBe('review: pass');
    expect(tidyLint('review: fail L-005')).toBe('review: fail L-005');
  });

  it('shows the tidy text on the pill', () => {
    expect(lintLook('review: fail L-001, L-001').label).toBe('review: fail L-001');
    expect(lintLook(null).label).toBe('Not run');
  });
});
