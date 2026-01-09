"use client"

import * as React from "react"
import { Check, ChevronsUpDown } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

export interface ComboboxOption {
  value: string
  label: string
  disabled?: boolean
}

export interface ComboboxProps {
  options: ComboboxOption[]
  value?: string
  onValueChange?: (value: string) => void
  placeholder?: string
  searchPlaceholder?: string
  emptyText?: string
  className?: string
  disabled?: boolean
  /** Custom render function for options */
  renderOption?: (option: ComboboxOption, isSelected: boolean) => React.ReactNode
  /** Custom render function for the selected value display */
  renderValue?: (option: ComboboxOption | undefined) => React.ReactNode
}

/**
 * Combobox component providing searchable dropdown functionality.
 * Built on top of shadcn Command and Popover components.
 */
const Combobox = React.forwardRef<HTMLButtonElement, ComboboxProps>(
  (
    {
      options,
      value,
      onValueChange,
      placeholder = "Select option...",
      searchPlaceholder = "Search...",
      emptyText = "No results found.",
      className,
      disabled = false,
      renderOption,
      renderValue,
    },
    ref
  ) => {
    const [open, setOpen] = React.useState(false)

    const selectedOption = options.find((option) => option.value === value)

    const handleSelect = (currentValue: string) => {
      const newValue = currentValue === value ? "" : currentValue
      onValueChange?.(newValue)
      setOpen(false)
    }

    const defaultRenderValue = (option: ComboboxOption | undefined) => {
      return option ? option.label : placeholder
    }

    const defaultRenderOption = (option: ComboboxOption, isSelected: boolean) => {
      return (
        <>
          <Check
            className={cn(
              "mr-2 h-4 w-4",
              isSelected ? "opacity-100" : "opacity-0"
            )}
          />
          {option.label}
        </>
      )
    }

    return (
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            ref={ref}
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={disabled}
            className={cn(
              "w-full justify-between",
              !value && "text-muted-foreground",
              className
            )}
          >
            {renderValue ? renderValue(selectedOption) : defaultRenderValue(selectedOption)}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
          <Command>
            <CommandInput placeholder={searchPlaceholder} />
            <CommandList>
              <CommandEmpty>{emptyText}</CommandEmpty>
              <CommandGroup>
                {options.map((option) => {
                  const isSelected = value === option.value
                  return (
                    <CommandItem
                      key={option.value}
                      value={option.value}
                      disabled={option.disabled}
                      onSelect={handleSelect}
                      className="cursor-pointer"
                    >
                      {renderOption
                        ? renderOption(option, isSelected)
                        : defaultRenderOption(option, isSelected)}
                    </CommandItem>
                  )
                })}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    )
  }
)
Combobox.displayName = "Combobox"

export { Combobox }
