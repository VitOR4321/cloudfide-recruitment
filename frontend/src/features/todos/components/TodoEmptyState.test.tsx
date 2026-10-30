import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { TodoEmptyState } from './TodoEmptyState'

vi.mock('../../../design-system', () => import('../../../design-system/mocks'))

it('offers creation for an empty list and respects the busy state', async () => {
  const user = userEvent.setup()
  const onCreate = vi.fn()
  const { rerender } = render(
    <TodoEmptyState hasTodos={false} disabled={false} onCreate={onCreate} />,
  )
  const button = screen.getByRole('button', { name: 'Add your first task' })
  await user.click(button)
  expect(onCreate).toHaveBeenCalledTimes(1)
  rerender(<TodoEmptyState hasTodos={false} disabled onCreate={onCreate} />)
  await user.click(button)
  expect(button).toBeDisabled()
  expect(onCreate).toHaveBeenCalledTimes(1)
})

it('suggests changing filters when tasks exist but none match', () => {
  render(<TodoEmptyState hasTodos disabled={false} onCreate={vi.fn()} />)
  expect(
    screen.getByRole('heading', { name: 'No matching tasks' }),
  ).toBeVisible()
  expect(
    screen.getByText('Change the status filter or search to find your tasks.'),
  ).toBeVisible()
  expect(screen.queryByRole('button')).not.toBeInTheDocument()
})
