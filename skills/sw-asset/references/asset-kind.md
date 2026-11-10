# Asset kinds

Choose exactly one kind per asset.

| Kind     | Use for                                                                | Stored as                        |
|----------|------------------------------------------------------------------------|----------------------------------|
| figma    | A Figma file or frame link                                             | ASSET-NNN.url                    |
| diagram  | An exported diagram, flowchart or sequence image                       | ASSET-NNN.<ext>                  |
| mockup   | A screen mockup, wireframe or prototype export                         | ASSET-NNN.<ext>                  |
| raw-idea | Unshaped user words to keep for later shaping                          | ASSET-NNN.md                     |
| document | A reference document or note, not a business source needing extraction | ASSET-NNN.<ext>                  |
| image    | A photo, screenshot or picture                                         | ASSET-NNN.<ext>                  |
| other    | Anything else the user wants kept                                      | ASSET-NNN.<ext> or ASSET-NNN.url |

Rules:

- A link is never fetched; store it as ASSET-NNN.url.
- Business documents that need text extraction go to sw-ingest, not here.
- Raw ideas stay verbatim and are never promoted to requirements by sw-asset.
- Keep file names lower-case, short, and free of paths; ASSET ids come from the registry.
