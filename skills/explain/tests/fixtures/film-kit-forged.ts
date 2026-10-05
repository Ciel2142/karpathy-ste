// Four things a film must not be able to write. test_film_kit.py (TestKitCompiles) copies this file to
// src/kitcheck/forged.ts of a copy of the app and expects tsc to refuse exactly the four lines that end in
// a marker comment, and nothing else: a source built by hand, a scene id the film does not have, the
// maker of a source (which is for the pipeline) and a source id the film did not declare.
import type { FilmProps, Source } from "../kit";
import { sourceFromDisk } from "../kit"; // MAKER

export const forged: Source = { path: "src/app.py", from: 47, lines: ["x = 1"] }; // FORGED
export const jump = (props: FilmProps<"type" | "checks", never>) => props.at("no-such-scene"); // UNKNOWN
export const made = sourceFromDisk({ path: "src/app.py", from: 47, lines: ["x = 1"] });
export const undeclared = (props: FilmProps<"type", "app">) => props.sources.nope; // UNDECLARED
