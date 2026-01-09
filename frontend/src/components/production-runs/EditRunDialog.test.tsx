/**
 * Tests for EditRunDialog - Status-Based Edit Restrictions
 *
 * Covers:
 * - Status-based restrictions (immutable vs editable)
 * - Form initialization from run data
 * - Change detection (Save button state)
 * - Editing basic info, items, and materials
 * - Update mutations
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach, Mock } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { EditRunDialog } from './EditRunDialog'
import {
  updateProductionRun,
  updateProductionRunItem,
  updateProductionRunMaterial,
} from '@/lib/api/production-runs'
import type { ProductionRunDetail } from '@/types/production-run'

// Mock API functions
vi.mock('@/lib/api/production-runs', () => ({
  updateProductionRun: vi.fn(),
  updateProductionRunItem: vi.fn(),
  updateProductionRunMaterial: vi.fn(),
}))

// Type the mocked functions
const mockUpdateProductionRun = updateProductionRun as Mock
const mockUpdateProductionRunItem = updateProductionRunItem as Mock
const mockUpdateProductionRunMaterial = updateProductionRunMaterial as Mock

// Mock production run data
const mockInProgressRun: ProductionRunDetail = {
  id: 'run-1',
  tenant_id: 'tenant-1',
  run_number: 'RUN-001',
  started_at: '2024-01-01T10:00:00Z',
  completed_at: null,
  duration_hours: null,
  estimated_print_time_hours: 5.5,
  printer_name: 'Prusa i3 MK3S',
  slicer_software: 'PrusaSlicer 2.6',
  bed_temperature: 60,
  nozzle_temperature: 210,
  status: 'in_progress',
  notes: 'Initial notes',
  is_reprint: false,
  items: [
    {
      id: 'item-1',
      production_run_id: 'run-1',
      model_id: 'model-1',
      quantity: 10,
      successful_quantity: 0,
      failed_quantity: 0,
      bed_position: 'A1',
      model: {
        id: 'model-1',
        sku: 'MODEL-001',
        name: 'Test Widget',
        description: null,
      },
    },
  ],
  materials: [
    {
      id: 'material-1',
      production_run_id: 'run-1',
      spool_id: 'spool-1',
      estimated_model_weight_grams: 100.0,
      estimated_flushed_grams: 10.0,
      estimated_tower_grams: 5.0,
      estimated_total_weight: 115.0,
      actual_model_weight_grams: null,
      actual_total_weight: 0,
      cost_per_gram: 0.025,
      estimated_cost: 2.875,
      total_cost: 0,
      spool: {
        id: 'spool-1',
        spool_id: 'FIL-001',
        brand: 'Prusament',
        color: 'Galaxy Black',
        color_hex: '1a1a1a',
        finish: null,
        material_type: {
          code: 'PLA',
          name: 'PLA',
        },
      },
    },
  ],
  total_items_planned: 10,
  total_items_successful: 0,
  total_items_failed: 0,
  overall_success_rate: null,
  total_estimated_cost: 2.875,
  total_material_cost: 0,
  created_at: '2024-01-01T10:00:00Z',
  updated_at: '2024-01-01T10:00:00Z',
}

const mockCompletedRun: ProductionRunDetail = {
  ...mockInProgressRun,
  id: 'run-2',
  run_number: 'RUN-002',
  status: 'completed',
  completed_at: '2024-01-01T15:00:00Z',
  duration_hours: 5.2,
}

const mockFailedRun: ProductionRunDetail = {
  ...mockInProgressRun,
  id: 'run-3',
  run_number: 'RUN-003',
  status: 'failed',
  completed_at: '2024-01-01T12:00:00Z',
}

const mockCancelledRun: ProductionRunDetail = {
  ...mockInProgressRun,
  id: 'run-4',
  run_number: 'RUN-004',
  status: 'cancelled',
  completed_at: '2024-01-01T11:00:00Z',
}

// Helper to render component with QueryClient
function renderEditRunDialog(run: ProductionRunDetail, props: Partial<Parameters<typeof EditRunDialog>[0]> = {}) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  const defaultProps = {
    run,
    open: true,
    onOpenChange: vi.fn(),
    onSuccess: vi.fn(),
  }

  return render(
    <QueryClientProvider client={queryClient}>
      <EditRunDialog {...defaultProps} {...props} />
    </QueryClientProvider>
  )
}

describe('EditRunDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Status-Based Restrictions', () => {
    it('should show all tabs for in_progress run', () => {
      renderEditRunDialog(mockInProgressRun)

      expect(screen.getByText('Edit Production Run')).toBeInTheDocument()
      expect(screen.getByText('Basic Info')).toBeInTheDocument()
      expect(screen.getByText(/Items \(1\)/)).toBeInTheDocument()
      expect(screen.getByText(/Materials \(1\)/)).toBeInTheDocument()
    })

    it('should show lock alert for completed run', () => {
      renderEditRunDialog(mockCompletedRun)

      expect(screen.getByText(/This run is completed/i)).toBeInTheDocument()
      expect(screen.getByText(/Only notes can be edited/i)).toBeInTheDocument()
    })

    it('should show lock alert for failed run', () => {
      renderEditRunDialog(mockFailedRun)

      expect(screen.getByText(/This run is failed/i)).toBeInTheDocument()
    })

    it('should show lock alert for cancelled run', () => {
      renderEditRunDialog(mockCancelledRun)

      expect(screen.getByText(/This run is cancelled/i)).toBeInTheDocument()
    })

    it('should hide tabs for immutable runs', () => {
      renderEditRunDialog(mockCompletedRun)

      expect(screen.queryByText('Basic Info')).not.toBeInTheDocument()
      expect(screen.queryByText(/Items/)).not.toBeInTheDocument()
      expect(screen.queryByText(/Materials/)).not.toBeInTheDocument()
    })

    it('should only show notes field for immutable runs', () => {
      renderEditRunDialog(mockCompletedRun)

      expect(screen.getByLabelText('Notes')).toBeInTheDocument()
      expect(screen.queryByLabelText('Printer Name')).not.toBeInTheDocument()
    })
  })

  describe('Form Initialization', () => {
    it('should initialize form with run data', () => {
      renderEditRunDialog(mockInProgressRun)

      // Click Basic Info tab
      fireEvent.click(screen.getByText('Basic Info'))

      expect(screen.getByLabelText('Printer Name')).toHaveValue('Prusa i3 MK3S')
      expect(screen.getByLabelText('Slicer Software')).toHaveValue('PrusaSlicer 2.6')
      expect(screen.getByLabelText(/Bed Temperature/)).toHaveValue(60)
      expect(screen.getByLabelText(/Nozzle Temperature/)).toHaveValue(210)
      expect(screen.getByLabelText(/Estimated Print Time/)).toHaveValue(5.5)
      expect(screen.getByLabelText('Notes')).toHaveValue('Initial notes')
    })

    it('should initialize items with correct quantities', async () => {
      const user = userEvent.setup()
      renderEditRunDialog(mockInProgressRun)

      await user.click(screen.getByText(/Items \(1\)/))

      expect(await screen.findByText('Test Widget')).toBeInTheDocument()
      expect(screen.getByText('Current: 10')).toBeInTheDocument()
      expect(screen.getByLabelText('Quantity:')).toHaveValue(10)
    })

    it('should initialize materials with correct weights', async () => {
      const user = userEvent.setup()
      renderEditRunDialog(mockInProgressRun)

      await user.click(screen.getByText(/Materials \(1\)/))

      expect(await screen.findByText(/Prusament Galaxy Black/)).toBeInTheDocument()
      expect(screen.getByText('Current: 115.0g')).toBeInTheDocument()
      // Find the input with value 115
      const weightInputs = screen.getAllByRole('spinbutton')
      const materialWeightInput = weightInputs.find(input => (input as HTMLInputElement).value === '115')
      expect(materialWeightInput).toHaveValue(115)
    })
  })

  describe('Change Detection', () => {
    it('should disable Save button when no changes', () => {
      renderEditRunDialog(mockInProgressRun)

      const saveButton = screen.getByRole('button', { name: /Save Changes/ })
      expect(saveButton).toBeDisabled()
    })

    it('should enable Save button when notes changed', () => {
      renderEditRunDialog(mockInProgressRun)

      const notesField = screen.getByLabelText('Notes')
      fireEvent.change(notesField, { target: { value: 'Updated notes' } })

      const saveButton = screen.getByRole('button', { name: /Save Changes/ })
      expect(saveButton).toBeEnabled()
    })

    it('should enable Save button when basic info changed', () => {
      renderEditRunDialog(mockInProgressRun)

      fireEvent.click(screen.getByText('Basic Info'))

      const printerField = screen.getByLabelText('Printer Name')
      fireEvent.change(printerField, { target: { value: 'Prusa XL' } })

      const saveButton = screen.getByRole('button', { name: /Save Changes/ })
      expect(saveButton).toBeEnabled()
    })

    it('should enable Save button when item quantity changed', async () => {
      const user = userEvent.setup()
      renderEditRunDialog(mockInProgressRun)

      await user.click(screen.getByText(/Items \(1\)/))

      const quantityField = await screen.findByLabelText('Quantity:')
      fireEvent.change(quantityField, { target: { value: '15' } })

      const saveButton = screen.getByRole('button', { name: /Save Changes/ })
      expect(saveButton).toBeEnabled()
    })

    it('should enable Save button when material weight changed', async () => {
      const user = userEvent.setup()
      renderEditRunDialog(mockInProgressRun)

      await user.click(screen.getByText(/Materials \(1\)/))

      await screen.findByText(/Prusament Galaxy Black/)
      const weightInputs = screen.getAllByRole('spinbutton')
      const materialWeightInput = weightInputs.find(input => (input as HTMLInputElement).value === '115')
      fireEvent.change(materialWeightInput!, { target: { value: '120' } })

      const saveButton = screen.getByRole('button', { name: /Save Changes/ })
      expect(saveButton).toBeEnabled()
    })
  })

  describe('Update Mutations', () => {
    it('should call updateProductionRun when notes changed on immutable run', async () => {
      mockUpdateProductionRun.mockResolvedValue({})
      const onSuccess = vi.fn()

      renderEditRunDialog(mockCompletedRun, { onSuccess })

      const notesField = screen.getByLabelText('Notes')
      fireEvent.change(notesField, { target: { value: 'Updated notes' } })

      const saveButton = screen.getByRole('button', { name: /Save Changes/ })
      fireEvent.click(saveButton)

      await waitFor(() => {
        expect(mockUpdateProductionRun).toHaveBeenCalledWith('run-2', {
          notes: 'Updated notes',
        })
      })

      expect(onSuccess).toHaveBeenCalled()
    })

    it('should call updateProductionRun with only changed basic fields', async () => {
      mockUpdateProductionRun.mockResolvedValue({})
      const onSuccess = vi.fn()

      renderEditRunDialog(mockInProgressRun, { onSuccess })

      fireEvent.click(screen.getByText('Basic Info'))

      const printerField = screen.getByLabelText('Printer Name')
      fireEvent.change(printerField, { target: { value: 'Prusa XL' } })

      const bedTempField = screen.getByLabelText(/Bed Temperature/)
      fireEvent.change(bedTempField, { target: { value: '65' } })

      const saveButton = screen.getByRole('button', { name: /Save Changes/ })
      fireEvent.click(saveButton)

      await waitFor(() => {
        expect(mockUpdateProductionRun).toHaveBeenCalledWith('run-1', {
          printer_name: 'Prusa XL',
          bed_temperature: 65,
        })
      })

      expect(onSuccess).toHaveBeenCalled()
    })

    it('should call updateProductionRunItem when quantity changed', async () => {
      const user = userEvent.setup()
      mockUpdateProductionRun.mockResolvedValue({})
      mockUpdateProductionRunItem.mockResolvedValue({})
      const onSuccess = vi.fn()

      renderEditRunDialog(mockInProgressRun, { onSuccess })

      await user.click(screen.getByText(/Items \(1\)/))

      const quantityField = await screen.findByLabelText('Quantity:')
      fireEvent.change(quantityField, { target: { value: '15' } })

      const saveButton = screen.getByRole('button', { name: /Save Changes/ })
      await user.click(saveButton)

      await waitFor(() => {
        expect(mockUpdateProductionRunItem).toHaveBeenCalledWith('run-1', 'item-1', {
          quantity: 15,
        })
      })

      expect(onSuccess).toHaveBeenCalled()
    })

    it('should call updateProductionRunMaterial when weight changed', async () => {
      const user = userEvent.setup()
      mockUpdateProductionRun.mockResolvedValue({})
      mockUpdateProductionRunMaterial.mockResolvedValue({})
      const onSuccess = vi.fn()

      renderEditRunDialog(mockInProgressRun, { onSuccess })

      await user.click(screen.getByText(/Materials \(1\)/))

      await screen.findByText(/Prusament Galaxy Black/)
      const weightInputs = screen.getAllByRole('spinbutton')
      const materialWeightInput = weightInputs.find(input => (input as HTMLInputElement).value === '115')
      fireEvent.change(materialWeightInput!, { target: { value: '120' } })

      const saveButton = screen.getByRole('button', { name: /Save Changes/ })
      await user.click(saveButton)

      await waitFor(() => {
        expect(mockUpdateProductionRunMaterial).toHaveBeenCalledWith('run-1', 'material-1', {
          estimated_model_weight_grams: 120,
        })
      })

      expect(onSuccess).toHaveBeenCalled()
    })

    it('should call all mutations when multiple fields changed', async () => {
      const user = userEvent.setup()
      mockUpdateProductionRun.mockResolvedValue({})
      mockUpdateProductionRunItem.mockResolvedValue({})
      mockUpdateProductionRunMaterial.mockResolvedValue({})
      const onSuccess = vi.fn()

      renderEditRunDialog(mockInProgressRun, { onSuccess })

      // Change notes
      const notesField = screen.getByLabelText('Notes')
      fireEvent.change(notesField, { target: { value: 'Updated notes' } })

      // Change basic info
      await user.click(screen.getByText('Basic Info'))
      const printerField = await screen.findByLabelText('Printer Name')
      fireEvent.change(printerField, { target: { value: 'Prusa XL' } })

      // Change item quantity
      await user.click(screen.getByText(/Items \(1\)/))
      const quantityField = await screen.findByLabelText('Quantity:')
      fireEvent.change(quantityField, { target: { value: '15' } })

      // Change material weight
      await user.click(screen.getByText(/Materials \(1\)/))
      await screen.findByText(/Prusament Galaxy Black/)
      const weightInputs = screen.getAllByRole('spinbutton')
      const materialWeightInput = weightInputs.find(input => (input as HTMLInputElement).value === '115')
      fireEvent.change(materialWeightInput!, { target: { value: '120' } })

      const saveButton = screen.getByRole('button', { name: /Save Changes/ })
      await user.click(saveButton)

      await waitFor(() => {
        expect(mockUpdateProductionRun).toHaveBeenCalledWith('run-1', {
          printer_name: 'Prusa XL',
          notes: 'Updated notes',
        })
        expect(mockUpdateProductionRunItem).toHaveBeenCalledWith('run-1', 'item-1', {
          quantity: 15,
        })
        expect(mockUpdateProductionRunMaterial).toHaveBeenCalledWith('run-1', 'material-1', {
          estimated_model_weight_grams: 120,
        })
      })

      expect(onSuccess).toHaveBeenCalled()
    })
  })

  describe('Error Handling', () => {
    it('should display error when update fails', async () => {
      mockUpdateProductionRun.mockRejectedValue(new Error('Update failed'))

      renderEditRunDialog(mockInProgressRun)

      const notesField = screen.getByLabelText('Notes')
      fireEvent.change(notesField, { target: { value: 'Updated notes' } })

      const saveButton = screen.getByRole('button', { name: /Save Changes/ })
      fireEvent.click(saveButton)

      await waitFor(() => {
        expect(screen.getByText(/Update failed/)).toBeInTheDocument()
      })
    })

    it('should show loading state during submission', async () => {
      mockUpdateProductionRun.mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 100))
      )

      renderEditRunDialog(mockInProgressRun)

      const notesField = screen.getByLabelText('Notes')
      fireEvent.change(notesField, { target: { value: 'Updated notes' } })

      const saveButton = screen.getByRole('button', { name: /Save Changes/ })
      fireEvent.click(saveButton)

      expect(screen.getByText(/Saving.../)).toBeInTheDocument()
    })
  })

  describe('Dialog Behavior', () => {
    it('should call onOpenChange when Cancel clicked', () => {
      const onOpenChange = vi.fn()

      renderEditRunDialog(mockInProgressRun, { onOpenChange })

      const cancelButton = screen.getByRole('button', { name: /Cancel/ })
      fireEvent.click(cancelButton)

      expect(onOpenChange).toHaveBeenCalledWith(false)
    })

    it('should not render when open is false', () => {
      renderEditRunDialog(mockInProgressRun, { open: false })

      expect(screen.queryByText('Edit Production Run')).not.toBeInTheDocument()
    })
  })

  describe('Empty States', () => {
    it('should show empty state when no items', async () => {
      const user = userEvent.setup()
      const runWithoutItems = {
        ...mockInProgressRun,
        items: [],
      }

      renderEditRunDialog(runWithoutItems)

      await user.click(screen.getByText(/Items \(0\)/))

      expect(await screen.findByText(/No items in this production run/)).toBeInTheDocument()
    })

    it('should show empty state when no materials', async () => {
      const user = userEvent.setup()
      const runWithoutMaterials = {
        ...mockInProgressRun,
        materials: [],
      }

      renderEditRunDialog(runWithoutMaterials)

      await user.click(screen.getByText(/Materials \(0\)/))

      expect(await screen.findByText(/No materials in this production run/)).toBeInTheDocument()
    })
  })

  describe('Form Field Coverage', () => {
    it('should handle slicer software input change', async () => {
      const user = userEvent.setup()

      renderEditRunDialog(mockInProgressRun)

      const slicerInput = screen.getByPlaceholderText('e.g., PrusaSlicer 2.6')
      await user.clear(slicerInput)
      await user.type(slicerInput, 'Cura 5.0')

      expect(slicerInput).toHaveValue('Cura 5.0')
    })

    it('should handle nozzle temperature input change', async () => {
      const user = userEvent.setup()

      renderEditRunDialog(mockInProgressRun)

      const nozzleInput = screen.getByPlaceholderText('210')
      await user.clear(nozzleInput)
      await user.type(nozzleInput, '220')

      expect(nozzleInput).toHaveValue(220)
    })

    it('should handle estimated print time input change', async () => {
      const user = userEvent.setup()

      renderEditRunDialog(mockInProgressRun)

      const timeInput = screen.getByPlaceholderText('5.5')
      await user.clear(timeInput)
      await user.type(timeInput, '3.5')

      expect(timeInput).toHaveValue(3.5)
    })
  })
})
