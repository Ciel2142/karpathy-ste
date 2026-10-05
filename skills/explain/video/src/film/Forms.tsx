// The three forms of an artifact, in a row: a sheet, a page and a video. The page is a Document, because
// it becomes the artifact card; the sheet and the video stay in the row. Each form is drawn round the
// middle of its place in the row; Film gives the colour and the opacity.
import type { ReactElement } from "react";
import { C, Mono, Sans } from "../kit";

const FORM_Y = 224;
export const FORM_X = { sheet: 400, page: 640, video: 880 };
const LABEL_Y = 316;
const STROKE = 2.5;

// A form's look: the colour of its outline and its opacity.
export type FormLook = { stroke: string; opacity: number };

// A landscape sheet: one page with a heading bar and two columns of lines.
export function Sheet(props: { look: FormLook }): ReactElement | null {
  const { stroke, opacity } = props.look;
  if (opacity <= 0) return null;
  const x0 = FORM_X.sheet - 62;
  const y0 = FORM_Y - 42;
  const rows = [0, 1, 2];
  return (
    <g opacity={opacity}>
      <rect x={x0} y={y0} width={124} height={84} rx={6} fill={C.panel} stroke={stroke} strokeWidth={STROKE} />
      <line x1={x0 + 14} y1={y0 + 20} x2={x0 + 110} y2={y0 + 20} stroke={stroke} strokeWidth={STROKE} />
      {rows.map((row) => {
        const y = y0 + 40 + row * 14;
        return (
          <g key={row}>
            <line x1={x0 + 14} y1={y} x2={x0 + 54} y2={y} stroke={C.muted} strokeWidth={2} />
            <line x1={x0 + 70} y1={y} x2={x0 + 110} y2={y} stroke={C.muted} strokeWidth={2} />
          </g>
        );
      })}
    </g>
  );
}

// A video: a 16:9 frame with a play mark.
export function Video(props: { look: FormLook }): ReactElement | null {
  const { stroke, opacity } = props.look;
  if (opacity <= 0) return null;
  const x = FORM_X.video;
  return (
    <g opacity={opacity}>
      <rect
        x={x - 64}
        y={FORM_Y - 36}
        width={128}
        height={72}
        rx={8}
        fill={C.panel}
        stroke={stroke}
        strokeWidth={STROKE}
      />
      <path
        d={`M ${x - 10} ${FORM_Y - 15} L ${x + 16} ${FORM_Y} L ${x - 10} ${FORM_Y + 15} Z`}
        fill="none"
        stroke={stroke}
        strokeWidth={STROKE}
        strokeLinejoin="round"
      />
    </g>
  );
}

// The name of a form, under its place in the row.
export function FormLabel(props: {
  x: number;
  text: string;
  fill: string;
  opacity: number;
}): ReactElement | null {
  const { x, text, fill, opacity } = props;
  return <Sans x={x} y={LABEL_Y} size={20} text={text} fill={fill} opacity={opacity} anchor="middle" />;
}

// The middle and the size of a document.
export type Box = { cx: number; cy: number; w: number; h: number };
export const PAGE: Box = { cx: FORM_X.page, cy: FORM_Y, w: 80, h: 104 };

const FOLD = 16; // the folded corner
const NAME_SIZE = 18;
const ADVANCE = 0.6; // Mono sets each character 0.6 of its size wide (kit/text.tsx)

// A document with a folded corner: the page of the row, and the artifact card it becomes. `lines` is the
// opacity of the text lines of the page, `name` the part of `fullName` written on the card so far; the
// name is placed as if whole, so it does not move while it is written.
export function Document(props: {
  box: Box;
  stroke: string;
  fill: string;
  opacity: number;
  lines: number;
  name: string;
  fullName: string;
}): ReactElement | null {
  const { box, stroke, fill, opacity, lines, name, fullName } = props;
  if (opacity <= 0) return null;
  const x0 = box.cx - box.w / 2;
  const y0 = box.cy - box.h / 2;
  const x1 = x0 + box.w;
  const y1 = y0 + box.h;
  const rows = [0, 1, 2, 3];
  return (
    <g opacity={opacity}>
      <path
        d={`M ${x0} ${y0} L ${x1 - FOLD} ${y0} L ${x1} ${y0 + FOLD} L ${x1} ${y1} L ${x0} ${y1} Z`}
        fill={fill}
        stroke={stroke}
        strokeWidth={STROKE}
        strokeLinejoin="round"
      />
      <path
        d={`M ${x1 - FOLD} ${y0} L ${x1 - FOLD} ${y0 + FOLD} L ${x1} ${y0 + FOLD}`}
        fill="none"
        stroke={stroke}
        strokeWidth={STROKE}
        strokeLinejoin="round"
      />
      {rows.map((row) => (
        <line
          key={row}
          x1={x0 + 14}
          y1={y0 + 34 + row * 16}
          x2={row === 3 ? x0 + box.w / 2 : x1 - 14}
          y2={y0 + 34 + row * 16}
          stroke={C.muted}
          strokeWidth={2}
          opacity={lines}
        />
      ))}
      <Mono
        x={box.cx - (Array.from(fullName).length * ADVANCE * NAME_SIZE) / 2}
        y={box.cy + 6}
        size={NAME_SIZE}
        text={name}
      />
    </g>
  );
}
