// What the Markdown components share: where the document lives and what its links may do.
export interface MdContext {
  scope: string;
  /** Folder of the file being shown, so relative links and images resolve against it. */
  dir: string;
  openDoc: (path: string) => void;
  openRef: (id: string) => void;
  jump: (id: string) => void;
  /** First and last line to mark, or null. */
  hit: [number, number] | null;
}
export const MD = Symbol('markdown');
