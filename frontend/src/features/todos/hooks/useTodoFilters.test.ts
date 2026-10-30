import { act, renderHook } from '@testing-library/react'
import { expect, it } from 'vitest'
import { todoFixture } from '../../../test/todoFixture'
import { useTodoFilters } from './useTodoFilters'

it('combines status, search and sorting and responds to updated tasks', () => {
  const tasks = [
    todoFixture,
    {
      ...todoFixture,
      id: 8,
      title: 'Book a room',
      completed: true,
      priority: 'high' as const,
    },
  ]
  const { result, rerender } = renderHook(
    ({ todos }) => useTodoFilters(todos),
    {
      initialProps: { todos: tasks },
    },
  )
  expect(result.current.filter).toBe('all')
  expect(result.current.search).toBe('')
  expect(result.current.sort).toBe('newest')
  act(() => result.current.setFilter('completed'))
  expect(result.current.visible.map((todo) => todo.id)).toEqual([8])
  act(() => result.current.setSearch('missing'))
  expect(result.current.visible).toEqual([])
  act(() => {
    result.current.setFilter('all')
    result.current.setSearch('')
    result.current.setSort('priority')
  })
  expect(result.current.visible.map((todo) => todo.id)).toEqual([8, 7])
  rerender({ todos: [] })
  expect(result.current.visible).toEqual([])
})
