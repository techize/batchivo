import { describe, it, vi } from 'vitest'

// AddFilamentDialog component does not exist yet — tests will fail with module not found
// until plan 03-04 creates the component. This file provides the test contract.
vi.mock('@/hooks/useFilamentTypes', () => ({
  useBulkCreateFilamentType: () => ({ mutateAsync: vi.fn(), isPending: false, isError: false }),
  useBatchCreateFilamentTypes: () => ({ mutateAsync: vi.fn(), isPending: false, isError: false }),
}))

describe('AddFilamentDialog', () => {
  it.todo('opens dialog when Add Filament button is clicked')
  it.todo('mode selector shows two workflow cards: Batch of identical spools and Multiple color variants')
  it.todo('bulk add mode: clicking bulk card shows bulk form with title Add filament — batch')
  it.todo('bulk add mode: back button returns to mode selector')
  it.todo('bulk add mode: submitting calls useBulkCreateFilamentType.mutateAsync with correct shape')
  it.todo('bulk add mode: dialog closes after successful submit')
  it.todo('batch mode: clicking batch card shows rapid batch form')
  it.todo('batch mode: add color appends row to accumulator table')
  it.todo('batch mode: submit all disabled when table is empty')
  it.todo('batch mode: submitting calls useBatchCreateFilamentTypes.mutateAsync')
  it.todo('batch mode: dialog stays open after successful submit and table clears')
})
