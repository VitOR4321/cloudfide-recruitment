import {
  QueryClient,
  QueryClientProvider,
  useMutation,
} from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useTodosBusy } from './useTodosBusy'
import { useTodosQuery } from './useTodosQuery'

afterEach(() => vi.restoreAllMocks())

function setup<T>(hook: () => T) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  function wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  return { client, ...renderHook(hook, { wrapper }) }
}

it('fetches tasks with an abort signal and stores the result under the list key', async () => {
  const list = vi.spyOn(todosApi, 'list').mockResolvedValue([todoFixture])
  const { client, result, unmount } = setup(useTodosQuery)
  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(list).toHaveBeenCalledWith(expect.any(AbortSignal))
  expect(result.current.data).toEqual([todoFixture])
  expect(client.getQueryData(todoKeys.list)).toEqual([todoFixture])
  unmount()
  client.clear()
})

it('exposes query failures', async () => {
  vi.spyOn(todosApi, 'list').mockRejectedValue(new Error('Server unavailable'))
  const { client, result, unmount } = setup(useTodosQuery)
  await waitFor(() => expect(result.current.isError).toBe(true))
  expect(result.current.error?.message).toBe('Server unavailable')
  unmount()
  client.clear()
})

it('tracks pending task mutations and ignores unrelated mutations', async () => {
  let finish: () => void = () => {}
  const pending = new Promise<void>((resolve) => {
    finish = resolve
  })
  const { client, result, unmount } = setup(() => ({
    busy: useTodosBusy(),
    task: useMutation({
      mutationKey: todoKeys.create,
      mutationFn: () => pending,
    }),
    other: useMutation({
      mutationKey: ['unrelated'],
      mutationFn: () => pending,
    }),
  }))
  expect(result.current.busy).toBe(false)
  act(() => result.current.other.mutate())
  await waitFor(() => expect(result.current.other.isPending).toBe(true))
  expect(result.current.busy).toBe(false)
  act(() => result.current.task.mutate())
  await waitFor(() => expect(result.current.busy).toBe(true))
  await act(async () => finish())
  await waitFor(() => expect(result.current.busy).toBe(false))
  unmount()
  client.clear()
})
