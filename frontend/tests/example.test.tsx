import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DisclaimerBanner } from "@/components/disclaimer-banner";

describe("DisclaimerBanner", () => {
  it("renders the persistent legal disclaimer", () => {
    render(<DisclaimerBanner />);
    expect(screen.getByRole("note")).toHaveTextContent(/not legal advice/i);
  });

  it("renders the compact variant", () => {
    render(<DisclaimerBanner compact />);
    expect(screen.getByRole("note")).toHaveTextContent(/Informational research/i);
  });
});