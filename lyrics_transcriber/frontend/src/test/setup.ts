// Test setup file for Vitest
// Note: This will be properly typed once vitest packages are installed

// Mock window.matchMedia for components that use media queries
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
})

// Mock ResizeObserver
const ResizeObserverMock = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
;(globalThis as typeof globalThis & { ResizeObserver: typeof ResizeObserverMock }).ResizeObserver = ResizeObserverMock

// Mock IntersectionObserver
const IntersectionObserverMock = class IntersectionObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
;(globalThis as typeof globalThis & { IntersectionObserver: typeof IntersectionObserverMock }).IntersectionObserver = IntersectionObserverMock 