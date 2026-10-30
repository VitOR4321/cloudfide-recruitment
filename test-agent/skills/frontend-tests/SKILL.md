# Frontend tests

Use Vitest and Testing Library with the repository's existing setup and fixtures.
Place tests beside implementation as `*.test.ts` or `*.test.tsx`. Inspect nearby
tests and the relevant types first. Assert observable behavior, errors and state
transitions. Use a real QueryClient with retries disabled for query hooks. Restore
stubbed globals and fake timers after each test. Do not use network services,
snapshots of implementation details or arbitrary sleeps. Preserve the existing
TypeScript and Prettier style. Verification: `npm run typecheck` and
`npm run test:coverage` from `frontend`.
