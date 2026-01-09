/**
 * RichTextEditor Component
 *
 * A WYSIWYG rich text editor built on TipTap, styled to match shadcn/ui.
 * Supports bold, italic, lists, and links.
 */

import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import { Bold, Italic, List, ListOrdered, Link as LinkIcon, Unlink } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useEffect, useCallback, useState } from 'react'

interface RichTextEditorProps {
  value?: string
  onChange?: (value: string) => void
  placeholder?: string
  className?: string
  disabled?: boolean
}

function ToolbarButton({
  isActive,
  onClick,
  disabled,
  children,
  'aria-label': ariaLabel,
}: {
  isActive?: boolean
  onClick: () => void
  disabled?: boolean
  children: React.ReactNode
  'aria-label': string
}) {
  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className={cn(
        'h-8 w-8 p-0',
        isActive && 'bg-accent text-accent-foreground'
      )}
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
    >
      {children}
    </Button>
  )
}

export function RichTextEditor({
  value = '',
  onChange,
  placeholder = 'Enter description...',
  className,
  disabled = false,
}: RichTextEditorProps) {
  const [isFocused, setIsFocused] = useState(false)

  const editor = useEditor({
    // Prevent double-initialization with React 18+ StrictMode
    immediatelyRender: false,
    extensions: [
      StarterKit.configure({
        heading: false, // Keep it simple - no headings
        codeBlock: false,
        code: false,
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: 'text-primary underline',
        },
      }),
      Placeholder.configure({
        placeholder,
      }),
    ],
    content: value,
    editable: !disabled,
    onUpdate: ({ editor }) => {
      const html = editor.getHTML()
      // If editor is empty (just <p></p>), return empty string
      const isEmpty = html === '<p></p>' || html === ''
      onChange?.(isEmpty ? '' : html)
    },
    onFocus: () => setIsFocused(true),
    onBlur: () => setIsFocused(false),
    editorProps: {
      attributes: {
        class: 'prose prose-sm max-w-none focus:outline-none min-h-[80px] px-3 py-2',
      },
    },
  })

  // Update editor content when value prop changes (e.g., form reset)
  useEffect(() => {
    if (editor && value !== editor.getHTML()) {
      editor.commands.setContent(value)
    }
  }, [editor, value])

  const setLink = useCallback(() => {
    if (!editor) return

    const previousUrl = editor.getAttributes('link').href
    const url = window.prompt('URL', previousUrl)

    // cancelled
    if (url === null) return

    // empty - remove link
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run()
      return
    }

    // update link
    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
  }, [editor])

  if (!editor) {
    return null
  }

  return (
    <div
      className={cn(
        'rounded-md border border-input bg-transparent shadow-sm transition-colors',
        isFocused && 'ring-1 ring-ring',
        disabled && 'opacity-50 cursor-not-allowed',
        className
      )}
    >
      {/* Toolbar */}
      <div className="flex items-center gap-1 border-b border-input px-2 py-1 bg-muted/30">
        <ToolbarButton
          isActive={editor.isActive('bold')}
          onClick={() => editor.chain().focus().toggleBold().run()}
          disabled={disabled}
          aria-label="Bold"
        >
          <Bold className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          isActive={editor.isActive('italic')}
          onClick={() => editor.chain().focus().toggleItalic().run()}
          disabled={disabled}
          aria-label="Italic"
        >
          <Italic className="h-4 w-4" />
        </ToolbarButton>
        <div className="w-px h-4 bg-border mx-1" />
        <ToolbarButton
          isActive={editor.isActive('bulletList')}
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          disabled={disabled}
          aria-label="Bullet List"
        >
          <List className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          isActive={editor.isActive('orderedList')}
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          disabled={disabled}
          aria-label="Numbered List"
        >
          <ListOrdered className="h-4 w-4" />
        </ToolbarButton>
        <div className="w-px h-4 bg-border mx-1" />
        <ToolbarButton
          isActive={editor.isActive('link')}
          onClick={setLink}
          disabled={disabled}
          aria-label="Add Link"
        >
          <LinkIcon className="h-4 w-4" />
        </ToolbarButton>
        {editor.isActive('link') && (
          <ToolbarButton
            onClick={() => editor.chain().focus().unsetLink().run()}
            disabled={disabled}
            aria-label="Remove Link"
          >
            <Unlink className="h-4 w-4" />
          </ToolbarButton>
        )}
      </div>

      {/* Editor Content */}
      <EditorContent editor={editor} />
    </div>
  )
}
