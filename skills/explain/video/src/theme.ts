// Palette duplicated in templates/sheet.html, page.html and video.html: change all four.
export const theme = {
  ink: "#1b2129",
  muted: "#5b6570",
  line: "#b8c0c9",
  blue: "#1d5fc2",
  red: "#c42f2a",
  fill: "#eef1f4",
  bg: "#ffffff",
  blueTint: "rgba(29, 95, 194, 0.12)", // blue at 12 % alpha: highlight bands, current node
  sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif',
  mono: 'ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace',
} as const;
