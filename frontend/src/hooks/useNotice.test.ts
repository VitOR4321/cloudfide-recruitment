import { act, renderHook } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { useNotice } from './useNotice'

afterEach(() => vi.useRealTimers())

it('starts without a notice and exposes a notification callback', () => {
  const { result } = renderHook(() => useNotice())
  expect(result.current.message).toBe('')
  expect(result.current.notify).toEqual(expect.any(Function))
})

it('restarts the expiry timer when a new notification arrives', () => {
  vi.useFakeTimers()
  const { result, unmount } = renderHook(() => useNotice())
  act(() => result.current.notify('Task created'))
  expect(result.current.message).toBe('Task created')
  act(() => vi.advanceTimersByTime(3000))
  act(() => result.current.notify('Task updated'))
  act(() => vi.advanceTimersByTime(1000))
  expect(result.current.message).toBe('Task updated')
  act(() => vi.advanceTimersByTime(3000))
  expect(result.current.message).toBe('')
  act(() => result.current.notify('Task deleted'))
  unmount()
  expect(vi.getTimerCount()).toBe(0)
})
