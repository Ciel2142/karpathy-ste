// Palette duplicated in templates/sheet.html, page.html and video.html: change all four.
export const theme = {
  bg: "#faf9f5",
  fill: "#f0eee6",
  ink: "#1f1d1a",
  muted: "#6b6a64",
  line: "#d4d0c6",
  accent: "#c2613f",
  blue: "#1d5fc2",
  red: "#c42f2a",
  blueTint: "rgba(29, 95, 194, 0.12)", // blue at 12 % alpha: highlight bands, current node
  sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif',
  mono: 'ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace',
} as const;
