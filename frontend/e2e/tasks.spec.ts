import { randomUUID } from 'node:crypto'
import { expect, test as base } from '@playwright/test'
import type { Todo, TodoInput } from '../src/features/todos/types'

const test = base.extend<{
  tasks: {
    create: (input?: Partial<TodoInput>) => Promise<Todo>
    track: (id: number) => void
  }
}>({
  tasks: async ({ request }, use) => {
    const ids: number[] = []
    await use({
      async create(input = {}) {
        const response = await request.post('/api/todos', {
          data: { title: `Browser test ${randomUUID()}`, ...input },
        })
        expect(response.status()).toBe(201)
        const todo: Todo = await response.json()
        ids.push(todo.id)
        return todo
      },
      track: (id) => ids.push(id),
    })
    for (const id of ids) {
      const response = await request.delete(`/api/todos/${id}`)
      expect([204, 404]).toContain(response.status())
    }
  },
})

test('completing and reopening a task keeps it visible under All statuses', async ({
  page,
  tasks,
}) => {
  const todo = await tasks.create()
  await page.goto('/')
  const title = page.getByRole('heading', { name: todo.title, exact: true })
  await expect(title).toBeVisible()
  const checkbox = page.getByRole('checkbox', {
    name: `Complete: ${todo.title}`,
    exact: true,
  })
  await checkbox.locator('..').click()
  const completed = page.getByRole('checkbox', {
    name: `Mark as active: ${todo.title}`,
    exact: true,
  })
  await expect(completed).toBeChecked()
  await expect(title).toBeVisible()
  await page.reload()
  await expect(completed).toBeChecked()
  await expect(title).toBeVisible()
  await completed.focus()
  await completed.press('Space')
  await expect(checkbox).not.toBeChecked()
  await page.reload()
  await expect(checkbox).not.toBeChecked()
})

test('status filters explain why toggled tasks leave the current view', async ({
  page,
  tasks,
}) => {
  const todo = await tasks.create()
  await page.goto('/')
  await page.getByLabel('Search tasks', { exact: true }).fill(todo.title)
  const status = page.getByLabel('Status', { exact: true })
  await status.selectOption('active')
  await expect(
    page.getByText('Only tasks to do are shown.', { exact: false }),
  ).toBeVisible()
  await page
    .getByRole('checkbox', { name: `Complete: ${todo.title}`, exact: true })
    .locator('..')
    .click()
  await expect(
    page.getByRole('heading', { name: todo.title, exact: true }),
  ).toHaveCount(0)
  await expect(
    page.getByText('Task completed. It is now hidden by the To do filter.'),
  ).toBeVisible()
  await status.selectOption('completed')
  await page
    .getByRole('checkbox', {
      name: `Mark as active: ${todo.title}`,
      exact: true,
    })
    .locator('..')
    .click()
  await expect(
    page.getByText(
      'Task marked as active. It is now hidden by the Completed filter.',
    ),
  ).toBeVisible()
  await expect(
    page.getByRole('heading', { name: todo.title, exact: true }),
  ).toHaveCount(0)
  await status.selectOption('all')
  await expect(
    page.getByRole('heading', { name: todo.title, exact: true }),
  ).toBeVisible()
})

test('failed completion leaves the task unchanged and permits retrying', async ({
  page,
  tasks,
}) => {
  const todo = await tasks.create()
  await page.goto('/')
  await page.route(`**/api/todos/${todo.id}`, async (route) => {
    if (route.request().method() === 'PATCH') {
      await route.fulfill({
        status: 503,
        json: { detail: 'Temporarily unavailable' },
      })
    } else {
      await route.continue()
    }
  })
  const checkbox = page.getByRole('checkbox', {
    name: `Complete: ${todo.title}`,
    exact: true,
  })
  await checkbox.locator('..').click()
  await expect(page.getByText('Temporarily unavailable')).toBeVisible()
  await expect(checkbox).not.toBeChecked()
  await expect(
    page.getByRole('heading', { name: todo.title, exact: true }),
  ).toBeVisible()
  await page.unroute(`**/api/todos/${todo.id}`)
  await page.getByRole('button', { name: 'Try again', exact: true }).click()
  await expect(page.getByText('Temporarily unavailable')).toHaveCount(0)
  await checkbox.locator('..').click()
  await expect(
    page.getByRole('checkbox', {
      name: `Mark as active: ${todo.title}`,
      exact: true,
    }),
  ).toBeChecked()
})

test('creates, validates, edits and deletes a task through the interface', async ({
  page,
  tasks,
}) => {
  const title = `UI task ${randomUUID()}`
  await page.goto('/')
  await page.getByRole('button', { name: 'New task', exact: true }).click()
  let dialog = page.getByRole('dialog', { name: 'New task', exact: true })
  await dialog.getByRole('button', { name: 'Save task', exact: true }).click()
  await expect(dialog.getByText('Enter a task title.')).toBeVisible()
  await dialog.getByLabel('Task title *', { exact: true }).fill(title)
  await dialog
    .getByLabel('Description (optional)', { exact: true })
    .fill('Created in a real browser')
  await dialog.getByLabel('Priority', { exact: true }).selectOption('high')
  const created = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/todos') && response.status() === 201,
  )
  await dialog.getByRole('button', { name: 'Save task', exact: true }).click()
  const todo: Todo = await (await created).json()
  tasks.track(todo.id)
  await expect(dialog).toHaveCount(0)
  await expect(
    page.getByRole('heading', { name: title, exact: true }),
  ).toBeVisible()
  await page
    .getByRole('button', { name: `Edit: ${title}`, exact: true })
    .click()
  dialog = page.getByRole('dialog', { name: 'Edit task', exact: true })
  await expect(
    dialog.getByLabel('Description (optional)', { exact: true }),
  ).toHaveValue('Created in a real browser')
  await dialog
    .getByLabel('Task title *', { exact: true })
    .fill(`${title} edited`)
  await dialog.getByRole('button', { name: 'Save task', exact: true }).click()
  await expect(dialog).toHaveCount(0)
  await page.reload()
  await expect(
    page.getByRole('heading', { name: `${title} edited`, exact: true }),
  ).toBeVisible()
  await page
    .getByRole('button', { name: `Delete: ${title} edited`, exact: true })
    .click()
  dialog = page.getByRole('dialog', { name: 'Delete task?', exact: true })
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click()
  await expect(
    page.getByRole('heading', { name: `${title} edited`, exact: true }),
  ).toBeVisible()
  await page
    .getByRole('button', { name: `Delete: ${title} edited`, exact: true })
    .click()
  await dialog.getByRole('button', { name: 'Delete task', exact: true }).click()
  await expect(
    page.getByRole('heading', { name: `${title} edited`, exact: true }),
  ).toHaveCount(0)
  await page.reload()
  await expect(
    page.getByRole('heading', { name: `${title} edited`, exact: true }),
  ).toHaveCount(0)
})

test('searching and priority sorting use the persisted task data', async ({
  page,
  tasks,
}) => {
  const prefix = `Sort ${randomUUID()}`
  const low = await tasks.create({
    title: `${prefix} low`,
    priority: 'low',
    description: `${prefix} searchable description`,
  })
  const high = await tasks.create({ title: `${prefix} high`, priority: 'high' })
  await page.goto('/')
  await page.getByLabel('Search tasks', { exact: true }).fill(prefix)
  await page.getByLabel('Sort by', { exact: true }).selectOption('priority')
  const titles = page
    .getByRole('region', { name: 'Task list' })
    .getByRole('heading')
  await expect(titles).toHaveText([high.title, low.title])
  await page
    .getByLabel('Search tasks', { exact: true })
    .fill(`${prefix.toUpperCase()} SEARCHABLE DESCRIPTION`)
  await expect(titles).toHaveText([low.title])
  await page
    .getByLabel('Search tasks', { exact: true })
    .fill(`Missing ${randomUUID()}`)
  await expect(
    page.getByRole('heading', { name: 'No matching tasks', exact: true }),
  ).toBeVisible()
})
