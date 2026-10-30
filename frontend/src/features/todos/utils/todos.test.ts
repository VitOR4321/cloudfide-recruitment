import { afterEach, describe, expect, it, vi } from 'vitest'
import { formatDate, isOverdue, selectTodos, validateTodo } from './todos'
import type { Todo } from '../types'

const base: Todo = {
  id: 1,
  title: 'Sprint plan',
  description: '',
  priority: 'medium',
  completed: false,
  due_date: null,
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
}

afterEach(() => vi.useRealTimers())

it.each(['2026-02-30', 'not-a-date', '2026-2-01'])(
  'rejects an invalid due date %s',
  (due_date) => {
    expect(validateTodo({ ...base, due_date })).toHaveProperty(
      'due_date',
      'Enter a valid date.',
    )
  },
)

it('validates trimmed text at the exact length limits', () => {
  expect(validateTodo({ ...base, title: ' '.repeat(5) })).toHaveProperty(
    'title',
    'Enter a task title.',
  )
  expect(validateTodo({ ...base, title: 'x'.repeat(121) })).toHaveProperty(
    'title',
  )
  expect(
    validateTodo({ ...base, description: 'x'.repeat(2001) }),
  ).toHaveProperty('description')
  expect(
    validateTodo({
      ...base,
      title: ` ${'x'.repeat(120)} `,
      description: 'x'.repeat(2000),
      due_date: '2028-02-29',
    }),
  ).toEqual({})
})

it('sorts due dates before missing dates and breaks ties by descending id', () => {
  const first = { ...base, id: 2, due_date: '2026-10-15' }
  const tied = { ...first, id: 3 }
  expect(selectTodos([base, first, tied], 'all', '', 'due')).toEqual([
    tied,
    first,
    base,
  ])
})

it('marks only incomplete tasks before the local current date as overdue', () => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date(2026, 9, 15, 12))
  expect(isOverdue({ ...base, due_date: '2026-10-14' })).toBe(true)
  expect(isOverdue({ ...base, due_date: '2026-10-15' })).toBe(false)
  expect(isOverdue({ ...base, due_date: '2026-10-16' })).toBe(false)
  expect(isOverdue({ ...base, completed: true, due_date: '2026-10-14' })).toBe(
    false,
  )
  expect(isOverdue(base)).toBe(false)
})

it('formats dates in the application locale', () => {
  expect(formatDate('2026-10-15')).toBe('15 Oct 2026')
})

describe('selectTodos', () => {
  it('combines status with a case-insensitive search in the description', () => {
    const matching = { ...base, description: 'Discuss the API' }
    const todos = [
      matching,
      { ...matching, id: 2, completed: true },
      { ...base, id: 3 },
    ]
    expect(selectTodos(todos, 'active', ' api ', 'newest')).toEqual([matching])
  })

  it('sorts by priority without changing the source array', () => {
    const high: Todo = { ...base, id: 2, priority: 'high' }
    const todos = [base, high]
    expect(selectTodos(todos, 'all', '', 'priority')).toEqual([high, base])
    expect(todos).toEqual([base, high])
  })
})
