import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useCreateTodoMutation } from './useCreateTodoMutation'
import { useDeleteTodoMutation } from './useDeleteTodoMutation'
import { useUpdateTodoMutation } from './useUpdateTodoMutation'

vi.mock('../api/todos', () => ({
  todosApi: { create: vi.fn(), update: vi.fn(), remove: vi.fn() },
}))

afterEach(() => vi.clearAllMocks())

function setup<T>(hook: () => T) {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  })
  function wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  return { client, ...renderHook(hook, { wrapper }) }
}

it('creates a task in an empty cache', async () => {
  vi.mocked(todosApi.create).mockResolvedValue(todoFixture)
  const { client, result, unmount } = setup(useCreateTodoMutation)
  await act(() => result.current.mutateAsync(todoFixture))
  expect(todosApi.create).toHaveBeenCalledWith(todoFixture)
  expect(client.getQueryData(todoKeys.list)).toEqual([todoFixture])
  unmount()
  client.clear()
})

it('replaces a duplicate task and preserves unrelated cached tasks', async () => {
  const saved = { ...todoFixture, title: 'Saved title' }
  const other = { ...todoFixture, id: 8 }
  vi.mocked(todosApi.create).mockResolvedValue(saved)
  const { client, result, unmount } = setup(useCreateTodoMutation)
  client.setQueryData(todoKeys.list, [other, todoFixture])
  await act(() => result.current.mutateAsync(todoFixture))
  expect(client.getQueryData(todoKeys.list)).toEqual([saved, other])
  unmount()
  client.clear()
})

it('updates only the saved task in the cache', async () => {
  const saved = { ...todoFixture, completed: true }
  const other = { ...todoFixture, id: 8 }
  vi.mocked(todosApi.update).mockResolvedValue(saved)
  const { client, result, unmount } = setup(useUpdateTodoMutation)
  client.setQueryData(todoKeys.list, [todoFixture, other])
  await act(() =>
    result.current.mutateAsync({ id: 7, input: { completed: true } }),
  )
  expect(todosApi.update).toHaveBeenCalledWith(7, { completed: true })
  expect(client.getQueryData(todoKeys.list)).toEqual([saved, other])
  unmount()
  client.clear()
})

it('removes only the deleted task from the cache', async () => {
  const other = { ...todoFixture, id: 8 }
  vi.mocked(todosApi.remove).mockResolvedValue(undefined)
  const { client, result, unmount } = setup(useDeleteTodoMutation)
  client.setQueryData(todoKeys.list, [todoFixture, other])
  await act(() => result.current.mutateAsync(7))
  expect(todosApi.remove).toHaveBeenCalledWith(7)
  expect(client.getQueryData(todoKeys.list)).toEqual([other])
  unmount()
  client.clear()
})

it('preserves cached tasks when saving fails', async () => {
  vi.mocked(todosApi.update).mockRejectedValue(new Error('Save failed'))
  const { client, result, unmount } = setup(useUpdateTodoMutation)
  client.setQueryData(todoKeys.list, [todoFixture])
  await act(async () => {
    await expect(
      result.current.mutateAsync({ id: 7, input: { completed: true } }),
    ).rejects.toThrow('Save failed')
  })
  expect(client.getQueryData(todoKeys.list)).toEqual([todoFixture])
  unmount()
  client.clear()
})

it('does not create a partial task list when updating without cached data', async () => {
  vi.mocked(todosApi.update).mockResolvedValue(todoFixture)
  const { client, result, unmount } = setup(useUpdateTodoMutation)
  await act(() =>
    result.current.mutateAsync({ id: 7, input: { completed: true } }),
  )
  expect(client.getQueryData(todoKeys.list)).toBeUndefined()
  unmount()
  client.clear()
})

it('can delete a task without cached data', async () => {
  vi.mocked(todosApi.remove).mockResolvedValue(undefined)
  const { client, result, unmount } = setup(useDeleteTodoMutation)
  await act(() => result.current.mutateAsync(7))
  expect(client.getQueryData(todoKeys.list)).toBeUndefined()
  unmount()
  client.clear()
})
