import "@testing-library/jest-dom";
import { expect, vi } from "vitest";

// Ensure jest-dom matchers are available on expect
import * as matchers from "@testing-library/jest-dom/matchers";
expect.extend(matchers);
