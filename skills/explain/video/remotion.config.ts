// Remotion CLI settings for the explain video app. The CLI reads this file; it runs as
// <workspace>/app/node_modules/.bin/remotion with cwd <workspace>/app.
import { Config } from "@remotion/cli/config";

Config.setRspack(true);
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
