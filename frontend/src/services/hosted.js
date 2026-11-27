/** True in the copy of StoryBridge on the public website (`npm run build:hosted`). Stories are made only on a
 *  volunteer's own computer, so that copy shows what StoryBridge is and never calls the StoryBridge server. */
export const HOSTED = import.meta.env.MODE === "hosted";

export const ASK_US = "mailto:smilecardnonprofit@gmail.com?subject=StoryBridge";
