/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom" />

declare global {
  interface Window {
    ResizeObserver: unknown
    IntersectionObserver: unknown
  }
} 