// The caption of a brainrot short: the chunk of 1 to 3 words that is on screen now, centred on the
// seam between the panel and the background (x 540, y 960), the word being spoken in yellow.
// Yellow is the one colour only Short uses. It draws nothing between chunks, before the first and
// after the last, nor for a chunk that has no word to light up.
import type { CSSProperties } from "react";
import { useCurrentFrame } from "remotion";
import { BRAINROT_BOX } from "../sceneBox";
import { theme } from "../theme";
import type { CaptionChunk } from "../types";
import { activeCaption } from "./captions";

const SEAM_Y = BRAINROT_BOX.height; // 960: the bottom edge of the panel
const MAX_WIDTH = 1000;
const ACTIVE = "#ffd400";

const band: CSSProperties = {
  position: "absolute",
  left: BRAINROT_BOX.width / 2,
  top: SEAM_Y,
  transform: "translate(-50%, -50%)",
  width: "max-content", // an absolute box with `left` set would otherwise wrap at the frame's right half
  maxWidth: MAX_WIDTH,
  textAlign: "center",
  fontFamily: theme.sans,
  fontSize: 76,
  fontWeight: 700,
  lineHeight: 1.1,
  color: "#ffffff",
  WebkitTextStroke: "8px #000000",
  paintOrder: "stroke fill", // the stroke goes under the fill, so the letters keep their full width
};

export function CaptionBand({ captions }: { captions: CaptionChunk[] }) {
  const frame = useCurrentFrame();
  const active = activeCaption(captions, frame);
  if (active === null || active.chunk.words[active.word] === undefined) return null;
  return (
    <div style={band}>
      {active.chunk.words.map((word, i) => (
        <span key={i} style={i === active.word ? { color: ACTIVE } : undefined}>
          {i > 0 ? " " : ""}
          {word.text}
        </span>
      ))}
    </div>
  );
}
