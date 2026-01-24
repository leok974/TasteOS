import React from "react";
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import TasteOSPrototype from "../TasteOSPrototype";

describe("TasteOSPrototype", () => {
  it("renders without crashing", () => {
    const { getByText } = render(<TasteOSPrototype />);
    expect(getByText(/Good morning/i)).toBeTruthy();
  });
});
