# Frontend tests

Use Vitest and Testing Library with the repository's existing setup and fixtures.
Place tests beside implementation as `*.test.ts` or `*.test.tsx`. Inspect nearby
tests and the relevant types first. Assert observable behavior, errors and state
transitions. Use a real QueryClient with retries disabled for query hooks. Restore
stubbed globals and fake timers after each test. Do not use network services,
snapshots of implementation details or arbitrary sleeps. Preserve the existing
TypeScript and Prettier style.

Before writing tests, inspect the supplied neighboring test and helpers. Preserve
existing tests and their mocks. Component tests commonly mock the design-system
barrel with its existing mocks module. If using real styled components, wrap them
in the existing AppProviders or ThemeProvider with the repository theme.

Import expect, it and vi explicitly from vitest; runtime globals are disabled.
Type helper overrides with Partial<ComponentProps<typeof Component>> and use the
actual enum values from source. JSX belongs in .test.tsx. Use userEvent for user
interactions. Separate scenarios with it.each or use rerender/unmount from the
original render result. Calling render(null) creates another root and does not
unmount the existing component.

Verification: npm run typecheck and npm run test:coverage from frontend. Never
remove an assertion, mock or strict type check to make generated tests pass.
