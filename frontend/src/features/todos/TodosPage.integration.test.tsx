import { QueryClient } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { AppProviders } from '../../app/AppProviders'
import { todoFixture } from '../../test/todoFixture'
import { todosApi } from './api/todos'
import { TodosPage } from './TodosPage'

const clients: QueryClient[] = []

afterEach(() => {
  vi.restoreAllMocks()
  clients.splice(0).forEach((client) => client.clear())
})

function renderPage(completed = false) {
  const todo = { ...todoFixture, completed }
  vi.spyOn(todosApi, 'list').mockResolvedValue([todo])
  vi.spyOn(todosApi, 'update').mockImplementation(async (_, input) => ({
    ...todo,
    ...input,
  }))
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  clients.push(client)
  render(
    <AppProviders client={client}>
      <TodosPage />
    </AppProviders>,
  )
  return userEvent.setup()
}

it.each([false, true])(
  'keeps a task visible under All statuses when completed starts as %s',
  async (completed) => {
    const user = renderPage(completed)
    const checkbox = await screen.findByRole('checkbox')
    await user.click(checkbox)
    await waitFor(() => expect(checkbox).toHaveProperty('checked', !completed))
    expect(
      screen.getByRole('heading', { name: todoFixture.title }),
    ).toBeVisible()
    expect(todosApi.update).toHaveBeenCalledWith(todoFixture.id, {
      completed: !completed,
    })
  },
)

it.each([
  ['active', false, 'Task completed. It is now hidden by the To do filter.'],
  [
    'completed',
    true,
    'Task marked as active. It is now hidden by the Completed filter.',
  ],
] as const)(
  'explains the task leaving the %s filter and restores it under All statuses',
  async (filter, completed, notice) => {
    const user = renderPage(completed)
    await screen.findByRole('checkbox')
    await user.selectOptions(screen.getByLabelText('Status'), filter)
    await user.click(screen.getByRole('checkbox'))
    expect(await screen.findByText(notice)).toBeVisible()
    expect(
      screen.queryByRole('heading', { name: todoFixture.title }),
    ).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Status'), 'all')
    expect(
      screen.getByRole('heading', { name: todoFixture.title }),
    ).toBeVisible()
  },
)

it('preserves the task on a failed toggle and retries without removing it', async () => {
  const user = renderPage()
  vi.mocked(todosApi.update).mockRejectedValueOnce(
    new Error('Save unavailable'),
  )
  const checkbox = await screen.findByRole('checkbox')
  await user.click(checkbox)
  expect(await screen.findByText('Save unavailable')).toBeVisible()
  expect(checkbox).not.toBeChecked()
  expect(screen.getByRole('heading', { name: todoFixture.title })).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  await waitFor(() =>
    expect(screen.queryByText('Save unavailable')).not.toBeInTheDocument(),
  )
  await user.click(checkbox)
  await waitFor(() => expect(checkbox).toBeChecked())
})
