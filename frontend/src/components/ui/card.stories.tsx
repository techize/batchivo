import type { Meta, StoryObj } from '@storybook/react-vite'

import { Button } from './button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from './card'

/**
 * Card component for grouping related content.
 * Includes subcomponents for Header, Title, Description, Content, and Footer.
 */
const meta: Meta<typeof Card> = {
  title: 'UI/Card',
  component: Card,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
}

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  render: () => (
    <Card className="w-[350px]">
      <CardHeader>
        <CardTitle>Card Title</CardTitle>
        <CardDescription>Card description goes here.</CardDescription>
      </CardHeader>
      <CardContent>
        <p>Card content with any custom components or text.</p>
      </CardContent>
      <CardFooter>
        <Button>Action</Button>
      </CardFooter>
    </Card>
  ),
}

export const SimpleContent: Story = {
  render: () => (
    <Card className="w-[350px]">
      <CardContent className="pt-6">
        <p>A simple card with just content, no header or footer.</p>
      </CardContent>
    </Card>
  ),
}

export const WithForm: Story = {
  render: () => (
    <Card className="w-[350px]">
      <CardHeader>
        <CardTitle>Create Product</CardTitle>
        <CardDescription>Add a new product to your inventory.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="name" className="text-sm font-medium">
            Product Name
          </label>
          <input
            id="name"
            placeholder="Enter product name"
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
          />
        </div>
        <div className="space-y-2">
          <label htmlFor="price" className="text-sm font-medium">
            Price
          </label>
          <input
            id="price"
            type="number"
            placeholder="0.00"
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
          />
        </div>
      </CardContent>
      <CardFooter className="flex justify-between">
        <Button variant="outline">Cancel</Button>
        <Button>Create</Button>
      </CardFooter>
    </Card>
  ),
}

export const StatsCard: Story = {
  render: () => (
    <Card className="w-[200px]">
      <CardHeader className="pb-2">
        <CardDescription>Total Revenue</CardDescription>
        <CardTitle className="text-3xl">$12,345</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-xs text-muted-foreground">+20.1% from last month</p>
      </CardContent>
    </Card>
  ),
}

/**
 * Multiple cards in a grid layout.
 */
export const CardGrid: Story = {
  render: () => (
    <div className="grid grid-cols-3 gap-4">
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>Products</CardDescription>
          <CardTitle className="text-2xl">156</CardTitle>
        </CardHeader>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>Orders</CardDescription>
          <CardTitle className="text-2xl">42</CardTitle>
        </CardHeader>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>Revenue</CardDescription>
          <CardTitle className="text-2xl">$8.2k</CardTitle>
        </CardHeader>
      </Card>
    </div>
  ),
}
