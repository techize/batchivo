import type { Meta, StoryObj } from '@storybook/react-vite'
import { Search } from 'lucide-react'

import { Input } from './input'
import { Label } from './label'

/**
 * Input component for form fields.
 * Supports all native input types and states.
 */
const meta: Meta<typeof Input> = {
  title: 'UI/Input',
  component: Input,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    type: {
      control: 'select',
      options: ['text', 'email', 'password', 'number', 'search', 'tel', 'url'],
      description: 'HTML input type',
    },
    disabled: {
      control: 'boolean',
      description: 'Disable the input',
    },
    placeholder: {
      control: 'text',
      description: 'Placeholder text',
    },
  },
}

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  args: {
    placeholder: 'Enter text...',
  },
  decorators: [
    (Story) => (
      <div className="w-[300px]">
        <Story />
      </div>
    ),
  ],
}

export const WithLabel: Story = {
  render: () => (
    <div className="w-[300px] space-y-2">
      <Label htmlFor="email">Email</Label>
      <Input id="email" type="email" placeholder="name@example.com" />
    </div>
  ),
}

export const Password: Story = {
  render: () => (
    <div className="w-[300px] space-y-2">
      <Label htmlFor="password">Password</Label>
      <Input id="password" type="password" placeholder="Enter password" />
    </div>
  ),
}

export const Number: Story = {
  render: () => (
    <div className="w-[300px] space-y-2">
      <Label htmlFor="quantity">Quantity</Label>
      <Input id="quantity" type="number" placeholder="0" min={0} />
    </div>
  ),
}

export const Disabled: Story = {
  args: {
    placeholder: 'Disabled input',
    disabled: true,
  },
  decorators: [
    (Story) => (
      <div className="w-[300px]">
        <Story />
      </div>
    ),
  ],
}

export const WithValue: Story = {
  args: {
    defaultValue: 'Pre-filled value',
  },
  decorators: [
    (Story) => (
      <div className="w-[300px]">
        <Story />
      </div>
    ),
  ],
}

export const WithIcon: Story = {
  render: () => (
    <div className="relative w-[300px]">
      <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
      <Input placeholder="Search products..." className="pl-8" />
    </div>
  ),
}

export const File: Story = {
  render: () => (
    <div className="w-[300px] space-y-2">
      <Label htmlFor="file">Upload file</Label>
      <Input id="file" type="file" />
    </div>
  ),
}

/**
 * Form field with validation error styling.
 */
export const WithError: Story = {
  render: () => (
    <div className="w-[300px] space-y-2">
      <Label htmlFor="email-error">Email</Label>
      <Input
        id="email-error"
        type="email"
        placeholder="name@example.com"
        className="border-destructive focus-visible:ring-destructive"
        aria-invalid="true"
      />
      <p className="text-sm text-destructive">Please enter a valid email address.</p>
    </div>
  ),
}

/**
 * Multiple input types displayed together.
 */
export const AllTypes: Story = {
  render: () => (
    <div className="w-[300px] space-y-4">
      <div className="space-y-2">
        <Label>Text</Label>
        <Input type="text" placeholder="Text input" />
      </div>
      <div className="space-y-2">
        <Label>Email</Label>
        <Input type="email" placeholder="email@example.com" />
      </div>
      <div className="space-y-2">
        <Label>Password</Label>
        <Input type="password" placeholder="Password" />
      </div>
      <div className="space-y-2">
        <Label>Number</Label>
        <Input type="number" placeholder="0" />
      </div>
      <div className="space-y-2">
        <Label>Search</Label>
        <Input type="search" placeholder="Search..." />
      </div>
    </div>
  ),
}
