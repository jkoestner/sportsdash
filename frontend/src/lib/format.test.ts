import { describe, expect, it } from "vitest";
import { addDays, clock, dayRange, localDay, longDay, monthDay, shortDay, weekday } from "./format";

const ET = "America/New_York";

describe("instants in the configured timezone", () => {
  it("formats a UTC start time as Eastern clock time", () => {
    expect(clock("2026-10-03T19:30:00+00:00", ET)).toBe("3:30 PM");
    expect(clock("2026-10-03T04:05:00Z", ET)).toBe("12:05 AM");
    expect(clock(null, ET)).toBe("TBD");
  });

  it("puts a late Sunday-night game on Sunday, not Monday", () => {
    // 8:20 PM ET Sunday is 00:20 UTC Monday.
    expect(localDay("2026-10-05T00:20:00Z", ET)).toBe("2026-10-04");
    expect(localDay("2026-10-05T00:20:00Z", "UTC")).toBe("2026-10-05");
  });
});

describe("calendar days", () => {
  it("adds days across month and year boundaries", () => {
    expect(addDays("2026-09-30", 1)).toBe("2026-10-01");
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
    expect(addDays("2026-10-02", -2)).toBe("2026-09-30");
  });

  it("formats without timezone drift", () => {
    expect(weekday("2026-10-03")).toBe("Sat");
    expect(monthDay("2026-10-03")).toBe("Oct 3");
    expect(shortDay("2026-10-03")).toBe("Sat, Oct 3");
    expect(longDay("2026-10-03")).toBe("Saturday, October 3");
  });

  it("formats tournament date ranges", () => {
    expect(dayRange("2026-10-01T04:00Z", "2026-10-04T04:00Z", ET)).toBe("Oct 1–4");
    expect(dayRange("2026-09-30T04:00Z", "2026-10-03T04:00Z", ET)).toBe("Sep 30–Oct 3");
    expect(dayRange(null, null, ET)).toBe("");
  });
});
