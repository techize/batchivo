import type { Meta, StoryObj } from '@storybook/react-vite'
import { AlertCircle, CheckCircle2, Info as InfoIcon, Terminal } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from './alert'

/**
 * Alert component for displaying important messages.
 * Supports default and destructive variants with optional icons.
 */
const meta: Meta<typeof Alert> = {
  title: 'UI/Alert',
  component: Alert,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['default', 'destructive'],
      description: 'Visual style variant',
    },
  },
}

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  render: () => (
    <Alert className="w-[450px]">
      <Terminal className="h-4 w-4" />
      <AlertTitle>Heads up!</AlertTitle>
      <AlertDescription>
        You can add components to your app using the CLI.
      </AlertDescription>
    </Alert>
  ),
}

export const Destructive: Story = {
  render: () => (
    <Alert variant="destructive" className="w-[450px]">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Error</AlertTitle>
      <AlertDescription>
        Your session has expired. Please log in again to continue.
      </AlertDescription>
    </Alert>
  ),
}

export const InfoAlert: Story = {
  render: () => (
    <Alert className="w-[450px]">
      <InfoIcon className="h-4 w-4" />
      <AlertTitle>Information</AlertTitle>
      <AlertDescription>
        This product is currently out of stock. We'll notify you when it's available.
      </AlertDescription>
    </Alert>
  ),
}

export const Success: Story = {
  render: () => (
    <Alert className="w-[450px] border-green-500/50 text-green-600 [&>svg]:text-green-600">
      <CheckCircle2 className="h-4 w-4" />
      <AlertTitle>Success</AlertTitle>
      <AlertDescription>
        Your order has been placed successfully. You'll receive a confirmation email shortly.
      </AlertDescription>
    </Alert>
  ),
}

export const WithoutIcon: Story = {
  render: () => (
    <Alert className="w-[450px]">
      <AlertTitle>Note</AlertTitle>
      <AlertDescription>
        Alerts can be displayed without icons for simpler messages.
      </AlertDescription>
    </Alert>
  ),
}

export const DescriptionOnly: Story = {
  render: () => (
    <Alert className="w-[450px]">
      <InfoIcon className="h-4 w-4" />
      <AlertDescription>
        A simple alert with only a description, no title needed.
      </AlertDescription>
    </Alert>
  ),
}

/**
 * All alert variants displayed together.
 */
export const AllVariants: Story = {
  render: () => (
    <div className="w-[450px] space-y-4">
      <Alert>
        <InfoIcon className="h-4 w-4" />
        <AlertTitle>Default</AlertTitle>
        <AlertDescription>Default alert for general information.</AlertDescription>
      </Alert>
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Destructive</AlertTitle>
        <AlertDescription>Destructive alert for errors and warnings.</AlertDescription>
      </Alert>
      <Alert className="border-green-500/50 text-green-600 [&>svg]:text-green-600">
        <CheckCircle2 className="h-4 w-4" />
        <AlertTitle>Success (Custom)</AlertTitle>
        <AlertDescription>Custom styled success alert.</AlertDescription>
      </Alert>
    </div>
  ),
}
