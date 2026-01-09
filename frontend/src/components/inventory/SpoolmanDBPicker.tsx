import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { spoolmandbApi } from '@/lib/api/spoolmandb'
import type { SpoolmanDBFilament } from '@/types/spoolmandb'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { ChevronsUpDown, Database, Loader2, X } from 'lucide-react'


interface SpoolmanDBPickerProps {
  onSelect: (filament: SpoolmanDBFilament) => void
  onClear?: () => void
  selectedFilament?: SpoolmanDBFilament | null
}

export function SpoolmanDBPicker({ onSelect, onClear, selectedFilament }: SpoolmanDBPickerProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [selectedManufacturer, setSelectedManufacturer] = useState<string>('__all__')
  const [selectedMaterial, setSelectedMaterial] = useState<string>('__all__')

  // Fetch manufacturers for filtering
  const { data: manufacturersData, isLoading: loadingManufacturers } = useQuery({
    queryKey: ['spoolmandb-manufacturers'],
    queryFn: () => spoolmandbApi.listManufacturers(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Fetch materials for filtering
  const { data: materialsData, isLoading: loadingMaterials } = useQuery({
    queryKey: ['spoolmandb-materials'],
    queryFn: () => spoolmandbApi.listMaterials(),
    staleTime: 5 * 60 * 1000,
  })

  // Fetch filaments with filters
  const manufacturerFilter = selectedManufacturer === '__all__' ? undefined : selectedManufacturer
  const materialFilter = selectedMaterial === '__all__' ? undefined : selectedMaterial

  const { data: filamentsData, isLoading: loadingFilaments } = useQuery({
    queryKey: ['spoolmandb-filaments', { manufacturer_name: manufacturerFilter, material: materialFilter, search, page_size: 50 }],
    queryFn: () => spoolmandbApi.listFilaments({
      manufacturer_name: manufacturerFilter,
      material: materialFilter,
      search: search || undefined,
      page_size: 50,
    }),
    staleTime: 60 * 1000, // 1 minute
    enabled: open, // Only fetch when popover is open
  })

  const manufacturers = manufacturersData?.manufacturers || []
  const filaments = filamentsData?.filaments || []

  // Sort materials by popularity (count) - use query data directly in useMemo
  const sortedMaterials = useMemo(() => {
    const materials = materialsData?.materials || []
    return [...materials].sort((a, b) => b.count - a.count)
  }, [materialsData?.materials])

  // Helper to get colour preview
  const getColorStyle = (hex: string | null): React.CSSProperties => {
    if (!hex) return {}
    // Handle RGBA (8 char) or RGB (6 char)
    const normalizedHex = hex.length === 8 ? hex.slice(2) : hex
    return { backgroundColor: `#${normalizedHex}` }
  }

  const handleSelect = (filament: SpoolmanDBFilament) => {
    onSelect(filament)
    setOpen(false)
    setSearch('')
  }

  const handleClear = () => {
    setSelectedManufacturer('__all__')
    setSelectedMaterial('__all__')
    setSearch('')
    onClear?.()
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Database className="h-4 w-4 text-muted-foreground" />
        <Label className="text-sm font-medium">SpoolmanDB Lookup</Label>
        {selectedFilament && (
          <Badge variant="secondary" className="ml-auto">
            <div
              className="w-3 h-3 rounded-full mr-1.5 border border-border"
              style={getColorStyle(selectedFilament.color_hex)}
            />
            {selectedFilament.manufacturer_name} - {selectedFilament.name}
            <button
              type="button"
              onClick={handleClear}
              className="ml-1.5 hover:text-destructive"
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        )}
      </div>

      {!selectedFilament && (
        <>
          {/* Filter row */}
          <div className="grid grid-cols-2 gap-2">
            <Select
              value={selectedManufacturer}
              onValueChange={setSelectedManufacturer}
              disabled={loadingManufacturers}
            >
              <SelectTrigger className="h-9">
                <SelectValue placeholder="Any manufacturer" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">Any manufacturer</SelectItem>
                {manufacturers.map((m) => (
                  <SelectItem key={m.id} value={m.name}>
                    {m.name} ({m.filament_count})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={selectedMaterial}
              onValueChange={setSelectedMaterial}
              disabled={loadingMaterials}
            >
              <SelectTrigger className="h-9">
                <SelectValue placeholder="Any material" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">Any material</SelectItem>
                {sortedMaterials.slice(0, 20).map((m) => (
                  <SelectItem key={m.material} value={m.material}>
                    {m.material} ({m.count})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Filament picker */}
          <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                aria-expanded={open}
                className="w-full justify-between h-9"
              >
                <span className="text-muted-foreground">Search filaments...</span>
                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[400px] p-0" align="start">
              <Command shouldFilter={false}>
                <CommandInput
                  placeholder="Search by name or colour..."
                  value={search}
                  onValueChange={setSearch}
                />
                <CommandList className="max-h-[300px]">
                  {loadingFilaments ? (
                    <div className="flex items-center justify-center py-6">
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      <span className="text-sm text-muted-foreground">Loading filaments...</span>
                    </div>
                  ) : filaments.length === 0 ? (
                    <CommandEmpty>
                      No filaments found.
                      {!selectedManufacturer && !selectedMaterial && !search && (
                        <span className="block mt-1 text-xs">
                          Try selecting a manufacturer or material first.
                        </span>
                      )}
                    </CommandEmpty>
                  ) : (
                    <CommandGroup>
                      {filaments.map((filament) => (
                        <CommandItem
                          key={filament.id}
                          value={filament.id}
                          onSelect={() => handleSelect(filament)}
                          className="cursor-pointer"
                        >
                          <div className="flex items-center gap-2 w-full">
                            <div
                              className="w-5 h-5 rounded-full border border-border flex-shrink-0"
                              style={getColorStyle(filament.color_hex)}
                            />
                            <div className="flex-1 min-w-0">
                              <div className="font-medium truncate">
                                {filament.manufacturer_name} - {filament.name}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {filament.material} • {filament.weight}g • {filament.diameter}mm
                                {filament.spool_weight && ` • Spool: ${filament.spool_weight}g`}
                              </div>
                            </div>
                          </div>
                        </CommandItem>
                      ))}
                      {filamentsData && filamentsData.total > filaments.length && (
                        <div className="py-2 px-3 text-xs text-muted-foreground text-center">
                          Showing {filaments.length} of {filamentsData.total} results. Refine your search to see more.
                        </div>
                      )}
                    </CommandGroup>
                  )}
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>

          <p className="text-xs text-muted-foreground">
            Select a filament from the community database to auto-fill details
          </p>
        </>
      )}
    </div>
  )
}
