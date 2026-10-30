import { afterEach, expect, it, vi } from 'vitest'
import { request } from './http'

afterEach(() => vi.unstubAllGlobals())

it('sends JSON headers and returns the response body', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify({ id: 7 })))
  vi.stubGlobal('fetch', fetch)
  await expect(
    request('/todos', { headers: { 'X-Request-ID': 'test' } }),
  ).resolves.toEqual({ id: 7 })
  expect(fetch).toHaveBeenCalledWith('/api/todos', {
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': 'test' },
  })
})

it('handles an empty deletion response', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
  )
  await expect(
    request('/todos/7', { method: 'DELETE' }),
  ).resolves.toBeUndefined()
})

it.each([
  [422, { detail: [{ msg: 'Invalid title' }] }, 'Check the task details:'],
  [404, { detail: 'Task not found.' }, 'Task not found.'],
  [500, { detail: [] }, 'The operation failed.'],
  [502, 'Bad gateway', 'The operation failed.'],
])(
  'handles HTTP %s without leaking server details',
  async (status, body, message) => {
    const response = new Response(
      typeof body === 'string' ? body : JSON.stringify(body),
      { status },
    )
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))
    await expect(request('/todos')).rejects.toThrow(message)
  },
)

it('explains connection failures', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockRejectedValue(new TypeError('Failed to fetch')),
  )
  await expect(request('/todos')).rejects.toThrow(
    'Cannot connect to the server.',
  )
})

it('preserves cancellation errors', async () => {
  const controller = new AbortController()
  controller.abort()
  const error = new DOMException('Aborted', 'AbortError')
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(error))
  await expect(request('/todos', { signal: controller.signal })).rejects.toBe(
    error,
  )
})
