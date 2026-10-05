// The caption of a brainrot short: the chunk of 1 to 3 words that is on screen now, centred on the
// seam between the panel and the background (x 540, y 960), the word being spoken in yellow.
// Yellow is the one colour only Short uses. It draws nothing between chunks, before the first and
// after the last, nor for a chunk that has no word to light up.
// The band is always one line: the text never wraps (`nowrap`), and a text that is too long for the
// band at the full size (a code name alone in its chunk) is drawn smaller (`captionFontSize`).
import type { CSSProperties } from "react";
import { useCurrentFrame } from "remotion";
import { BRAINROT_BOX } from "../sceneBox";
import { theme } from "../theme";
import type { CaptionChunk } from "../types";
import { CAPTION_FONT, activeCaption, captionFontSize } from "./captions";

const SEAM_Y = BRAINROT_BOX.height; // 960: the bottom edge of the panel
const MAX_WIDTH = 1000;
const ACTIVE = "#ffd400";
const STROKE_AT_FULL_SIZE = 8; // px of outline at CAPTION_FONT; the outline scales with the size

const band: CSSProperties = {
  position: "absolute",
  left: BRAINROT_BOX.width / 2,
  top: SEAM_Y,
  transform: "translate(-50%, -50%)",
  width: "max-content", // an absolute box with `left` set would otherwise wrap at the frame's right half
  maxWidth: MAX_WIDTH,
  textAlign: "center",
  whiteSpace: "nowrap",
  fontFamily: theme.sans,
  fontWeight: 700,
  lineHeight: 1.1,
  color: "#ffffff",
  paintOrder: "stroke fill", // the stroke goes under the fill, so the letters keep their full width
};

export function CaptionBand({ captions }: { captions: CaptionChunk[] }) {
  const frame = useCurrentFrame();
  const active = activeCaption(captions, frame);
  if (active === null || active.chunk.words[active.word] === undefined) return null;
  const size = captionFontSize(active.chunk.words.map((word) => word.text).join(" "));
  const stroke = Math.round((STROKE_AT_FULL_SIZE * size) / CAPTION_FONT);
  return (
    <div style={{ ...band, fontSize: size, WebkitTextStroke: `${stroke}px #000000` }}>
      {active.chunk.words.map((word, i) => (
        <span key={i} style={i === active.word ? { color: ACTIVE } : undefined}>
          {i > 0 ? " " : ""}
          {word.text}
        </span>
      ))}
    </div>
  );
}
