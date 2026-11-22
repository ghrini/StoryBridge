import { describe, expect, it } from "vitest";
import {
  bookTitle,
  countNeedingReview,
  filenameFromDisposition,
  formatTime,
  qrPointsAtThisComputerOnly,
  shortText,
  sourceSpan,
  spreadLabel,
} from "./format.js";

const transcript = [
  { id: "seg-0001", text: "One.", start: 0, end: 4 },
  { id: "seg-0002", text: "Two.", start: 5, end: 9 },
  { id: "seg-0003", text: "Three.", start: 12, end: 15 },
  { id: "seg-0004", text: "Four.", start: 16, end: 20 },
];

describe("formatTime", () => {
  it("shows minutes and zero-padded seconds", () => {
    expect(formatTime(0)).toBe("0:00");
    expect(formatTime(65.9)).toBe("1:05");
    expect(formatTime(600)).toBe("10:00");
  });
  it("never shows negative time", () => {
    expect(formatTime(-3)).toBe("0:00");
  });
});

describe("review helpers", () => {
  it("counts only sentences still needing review", () => {
    const chapters = [
      { sentences: [{ status: "flagged" }, { status: "approved" }] },
      { sentences: [{ status: "flagged" }, { status: "removed" }] },
    ];
    expect(countNeedingReview(chapters)).toBe(2);
    expect(countNeedingReview([])).toBe(0);
  });
  it("finds the stretch of recording a sentence is based on", () => {
    expect(sourceSpan(transcript, ["seg-0002", "seg-0003"])).toEqual({ start: 5, end: 15 });
    expect(sourceSpan(transcript, ["seg-9999"])).toBeNull();
  });
  it("shortens text for screen-reader labels", () => {
    expect(shortText("one two three")).toBe("one two three");
    expect(shortText("one two three four five six seven eight")).toBe("one two three four five six…");
  });
});

describe("bookTitle", () => {
  it("prefers a person's title, then the suggestion, then a default from the name", () => {
    expect(bookTitle({ book_title: "Mine", suggested_title: "AI" })).toBe("Mine");
    expect(bookTitle({ book_title: "  ", suggested_title: "Gram's Typical Day" })).toBe("Gram's Typical Day");
    expect(bookTitle({ family_name: "Gram" })).toBe("Gram's Story");
    expect(bookTitle({ family_name: "Charles" })).toBe("Charles' Story");
    expect(bookTitle({})).toBe("A Life Story");
  });
});

describe("filenameFromDisposition", () => {
  it("reads the file name the server chose", () => {
    expect(filenameFromDisposition('attachment; filename="Grams-Day.pdf"', "x.pdf")).toBe("Grams-Day.pdf");
    expect(filenameFromDisposition(null, "fallback.pdf")).toBe("fallback.pdf");
  });
});

describe("spreadLabel", () => {
  it("names the cover, each two-page spread, and the back", () => {
    expect(spreadLabel(0, 7)).toBe("Cover (page 1 of 7)");
    expect(spreadLabel(1, 7)).toBe("Pages 2–3 of 7");
    expect(spreadLabel(3, 7)).toBe("Pages 6–7 of 7");
    expect(spreadLabel(4, 7)).toBe("The back of the book");
    expect(spreadLabel(4, 8)).toBe("Page 8 of 8, the back of the book");
    expect(spreadLabel(0, 0)).toBe("No pages");
  });
});

describe("qrPointsAtThisComputerOnly", () => {
  it("flags localhost addresses but not a network address", () => {
    expect(qrPointsAtThisComputerOnly("http://localhost:8000")).toBe(true);
    expect(qrPointsAtThisComputerOnly("http://127.0.0.1:8000")).toBe(true);
    expect(qrPointsAtThisComputerOnly("http://192.168.4.27:8000")).toBe(false);
  });
});
