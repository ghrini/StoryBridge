/** True in the copy of StoryBridge on the public website (`npm run build:hosted`). Stories are made only on a
 *  volunteer's own computer, so that copy shows what StoryBridge is and never calls the StoryBridge server. */
export const HOSTED = import.meta.env.MODE === "hosted";

export const ASK_US = "mailto:smilecardnonprofit@gmail.com?subject=StoryBridge";

/** Where the SmileCard website's pages are. Next to the app (on a volunteer's computer) they are at /smilecard/;
 *  on the live website StoryBridge sits inside the SmileCard site, so its pages are at "/" (see
 *  scripts/build_storybridge_page.py, which sets VITE_SMILECARD_SITE). */
export const SMILECARD_SITE = import.meta.env.VITE_SMILECARD_SITE || "/smilecard/";
export const smilecardPage = (file) => `${SMILECARD_SITE}${encodeURIComponent(file)}.dc.html`;
