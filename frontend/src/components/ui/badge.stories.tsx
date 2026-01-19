import type { Meta, StoryObj } from '@storybook/react-vite'

import { Badge } from './badge'

/**
 * Badge component for displaying labels, tags, and status indicators.
 * Supports multiple color variants including success and warning states.
 */
const meta: Meta<typeof Badge> = {
  title: 'UI/Badge',
  component: Badge,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['default', 'secondary', 'destructive', 'outline', 'success', 'warning'],
      description: 'Visual style variant',
    },
  },
}

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  args: {
    children: 'Badge',
    variant: 'default',
  },
}

export const Secondary: Story = {
  args: {
    children: 'Secondary',
    variant: 'secondary',
  },
}

export const Destructive: Story = {
  args: {
    children: 'Destructive',
    variant: 'destructive',
  },
}

export const Outline: Story = {
  args: {
    children: 'Outline',
    variant: 'outline',
  },
}

export const Success: Story = {
  args: {
    children: 'Success',
    variant: 'success',
  },
}

export const Warning: Story = {
  args: {
    children: 'Warning',
    variant: 'warning',
  },
}

/**
 * All badge variants displayed together for comparison.
 */
export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <Badge variant="default">Default</Badge>
      <Badge variant="secondary">Secondary</Badge>
      <Badge variant="destructive">Error</Badge>
      <Badge variant="outline">Outline</Badge>
      <Badge variant="success">Success</Badge>
      <Badge variant="warning">Warning</Badge>
    </div>
  ),
}

/**
 * Example usage for status indicators in a table or list.
 */
export const StatusExamples: Story = {
  render: () => (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="w-24 text-sm text-muted-foreground">Order:</span>
        <Badge variant="success">Completed</Badge>
      </div>
      <div className="flex items-center gap-2">
        <span className="w-24 text-sm text-muted-foreground">Stock:</span>
        <Badge variant="warning">Low</Badge>
      </div>
      <div className="flex items-center gap-2">
        <span className="w-24 text-sm text-muted-foreground">Payment:</span>
        <Badge variant="destructive">Failed</Badge>
      </div>
      <div className="flex items-center gap-2">
        <span className="w-24 text-sm text-muted-foreground">Product:</span>
        <Badge variant="secondary">Draft</Badge>
      </div>
    </div>
  ),
}
