<script lang="ts">
  const paths: Record<string, string> = {
    overview: 'M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z',
    projects: 'M3 21h18M5 21V5l7-2 7 2v16M9 9h2M13 9h2M9 13h2M13 13h2M10 21v-4h4v4',
    features: 'M5 4h14v16H5zM9 9h6M9 13h6M9 17h3',
    tasks: 'M9 6h12M9 12h12M9 18h12M3 6l1.5 1.5L7 5M3 12l1.5 1.5L7 11M3 18l1.5 1.5L7 17',
    board: 'M4 4h5v16H4zM10 4h5v10h-5zM16 4h4v13h-4z',
    tree: 'M12 3v6M12 9H6v4M12 9h6v4M6 13v4M18 13v4M4 21h4M16 21h4',
    graph: 'M6 6a2 2 0 1 0 0 .01M18 6a2 2 0 1 0 0 .01M12 18a2 2 0 1 0 0 .01M8 7l3 9M16 7l-3 9M8 6h8',
    query: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-4-4',
    records: 'M5 4h14v16H5zM9 8h6M9 12h6M9 16h4',
    sources: 'M4 7l8-4 8 4-8 4zM4 12l8 4 8-4M4 17l8 4 8-4',
    quality: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM9 12l2 2 4-4',
    registry: 'M5 3h14v18H5zM9 8h6M9 12h6M9 16h6',
    metrics: 'M12 20V10M18 20V4M6 20v-4',
    refresh: 'M3 12a9 9 0 0 1 15.5-6.2L21 8M21 3v5h-5M21 12a9 9 0 0 1-15.5 6.2L3 16M3 21v-5h5',
    appearance: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 3v18',
    fold: 'M3 4h18v16H3zM9 4v16',
    menu: 'M4 7h16M4 12h16M4 17h16',
    close: 'M6 6l12 12M18 6L6 18',
    chevron: 'M9 6l6 6-6 6',
    warn: 'M12 3l10 18H2zM12 10v5M12 18v.01',
  };
  let { name, size = '' }: { name: string; size?: string } = $props();
</script>

<svg class="icon {size}" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d={paths[name] ?? paths.overview} /></svg>
