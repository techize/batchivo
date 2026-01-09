/**
 * SalesChannelList Component
 *
 * Displays a list of sales channels with platform type filtering.
 * Shows fee structure and monthly costs for each channel.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { Loader2, Plus, Search, Store } from 'lucide-react'

import {
  listSalesChannels,
  getPlatformDisplayName,
  getPlatformColor,
  type PlatformType,
} from '@/lib/api/sales-channels'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'

const PLATFORM_TYPES: PlatformType[] = [
  'fair',
  'online_shop',
  'shopify',
  'ebay',
  'etsy',
  'amazon',
  'other',
]

export function SalesChannelList() {
  const [search, setSearch] = useState('')
  const [platformFilter, setPlatformFilter] = useState<PlatformType | 'all'>('all')
  const [isActive, setIsActive] = useState<boolean | undefined>(undefined)

  const { data, isLoading, error } = useQuery({
    queryKey: ['sales-channels', { search, platformFilter, isActive }],
    queryFn: () =>
      listSalesChannels({
        search: search || undefined,
        platform_type: platformFilter === 'all' ? undefined : platformFilter,
        is_active: isActive,
        limit: 100,
      }),
  })

  const handleSearchChange = (value: string) => {
    setSearch(value)
  }

  const formatCurrency = (value: string | number) => {
    const numValue = typeof value === 'string' ? parseFloat(value) : value
    return `£${numValue.toFixed(2)}`
  }

  const formatPercentage = (value: string | number) => {
    const numValue = typeof value === 'string' ? parseFloat(value) : value
    return `${numValue.toFixed(1)}%`
  }

  const channels = data?.channels || []
  const activeCount = channels.filter((c) => c.is_active).length
  const inactiveCount = channels.filter((c) => !c.is_active).length

  if (error) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-semibold text-destructive">Error loading sales channels</p>
          <p className="text-sm text-muted-foreground">{(error as Error).message}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Sales Channels</h2>
          <p className="text-muted-foreground">
            {data?.total || 0} channels • {activeCount} active • Configure where you sell
          </p>
        </div>
        <Button asChild>
          <Link to="/sales-channels/new">
            <Plus className="mr-2 h-4 w-4" />
            New Channel
          </Link>
        </Button>
      </div>

      {/* Filters Card */}
      <Card>
        <CardContent className="pt-6 space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by name..."
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-2">
            <Select
              value={platformFilter}
              onValueChange={(v) => setPlatformFilter(v as PlatformType | 'all')}
            >
              <SelectTrigger className="w-[160px] h-8">
                <SelectValue placeholder="Platform type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Platforms</SelectItem>
                {PLATFORM_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>
                    {getPlatformDisplayName(type)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button
              variant={isActive === true ? 'default' : 'outline'}
              size="sm"
              onClick={() => setIsActive(isActive === true ? undefined : true)}
              className="h-8"
            >
              <span className="mr-1.5 h-2 w-2 rounded-full bg-green-500" />
              Active ({activeCount})
            </Button>
            <Button
              variant={isActive === false ? 'default' : 'outline'}
              size="sm"
              onClick={() => setIsActive(isActive === false ? undefined : false)}
              className="h-8"
            >
              <span className="mr-1.5 h-2 w-2 rounded-full bg-gray-400" />
              Inactive ({inactiveCount})
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Store className="h-4 w-4" />
            Channels
            {data && (
              <Badge variant="secondary" className="ml-2">
                {data.total}
              </Badge>
            )}
          </CardTitle>
          <CardDescription>
            Click on a channel to view details and edit settings
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Loading State */}
          {isLoading && (
            <div className="flex h-[200px] items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <span className="ml-3">Loading channels...</span>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && channels.length === 0 && (
            <div className="flex h-[200px] items-center justify-center">
              <div className="text-center">
                <Store className="mx-auto h-12 w-12 text-muted-foreground/50" />
                <p className="mt-4 text-muted-foreground">
                  {search
                    ? 'No channels match your search'
                    : 'No sales channels yet. Create your first channel to get started.'}
                </p>
                {!search && (
                  <Button asChild className="mt-4">
                    <Link to="/sales-channels/new">
                      <Plus className="mr-2 h-4 w-4" />
                      Create Channel
                    </Link>
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* Card View - Mobile */}
          {!isLoading && channels.length > 0 && (
            <div className="lg:hidden space-y-3">
              {channels.map((channel) => (
                <Link
                  key={channel.id}
                  to="/sales-channels/$channelId"
                  params={{ channelId: channel.id }}
                  className="block rounded-lg border p-4 space-y-3 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="font-medium">{channel.name}</div>
                      <Badge
                        variant="outline"
                        className={getPlatformColor(channel.platform_type)}
                      >
                        {getPlatformDisplayName(channel.platform_type)}
                      </Badge>
                    </div>
                    <Badge
                      variant="outline"
                      className={
                        channel.is_active
                          ? 'bg-green-500/10 text-green-600 border-green-200'
                          : 'bg-gray-500/10 text-gray-500 border-gray-200'
                      }
                    >
                      {channel.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                    <span>Fee: {formatPercentage(channel.fee_percentage)}</span>
                    {parseFloat(channel.fee_fixed) > 0 && (
                      <span>+ {formatCurrency(channel.fee_fixed)}</span>
                    )}
                    {parseFloat(channel.monthly_cost) > 0 && (
                      <span>Monthly: {formatCurrency(channel.monthly_cost)}</span>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}

          {/* Table View - Desktop */}
          {!isLoading && channels.length > 0 && (
            <div className="hidden lg:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead className="w-[150px]">Platform</TableHead>
                    <TableHead className="w-[100px]">Status</TableHead>
                    <TableHead className="w-[100px] text-right">Fee %</TableHead>
                    <TableHead className="w-[100px] text-right">Fixed Fee</TableHead>
                    <TableHead className="w-[100px] text-right">Monthly</TableHead>
                    <TableHead className="w-[80px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {channels.map((channel) => (
                    <TableRow key={channel.id} className="group">
                      <TableCell>
                        <Link
                          to="/sales-channels/$channelId"
                          params={{ channelId: channel.id }}
                          className="font-medium hover:text-primary transition-colors"
                        >
                          {channel.name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={getPlatformColor(channel.platform_type)}
                        >
                          {getPlatformDisplayName(channel.platform_type)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={
                            channel.is_active
                              ? 'bg-green-500/10 text-green-600 border-green-200'
                              : 'bg-gray-500/10 text-gray-500 border-gray-200'
                          }
                        >
                          {channel.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatPercentage(channel.fee_percentage)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatCurrency(channel.fee_fixed)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatCurrency(channel.monthly_cost)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          asChild
                          className="opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <Link
                            to="/sales-channels/$channelId"
                            params={{ channelId: channel.id }}
                          >
                            View
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
