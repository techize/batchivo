/**
 * ProductImagesEditor Component
 *
 * Manages product images: upload, reorder, set primary, delete.
 * Used on the ProductDetail page.
 */

import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Eye,
  ImagePlus,
  Loader2,
  RotateCw,
  Star,
  Trash2,
  Upload,
  X,
} from 'lucide-react'

import {
  getProductImages,
  uploadProductImage,
  setPrimaryImage,
  deleteProductImage,
  rotateProductImage,
  type ProductImage,
} from '@/lib/api/products'
import { config } from '@/lib/config'

// Get the API base URL for image URLs - supports runtime config
const API_BASE_URL = config.apiUrl

// Helper to get full image URL with cache-busting (images are served from API, not frontend)
function getImageUrl(path: string | undefined, updatedAt?: string): string {
  if (!path) return ''
  // If already absolute URL, return as-is
  let url = path.startsWith('http') ? path : `${API_BASE_URL}${path}`
  // Add cache-busting query param based on updated_at timestamp
  if (updatedAt) {
    const timestamp = new Date(updatedAt).getTime()
    url += `?v=${timestamp}`
  }
  return url
}
import { Button } from '@/components/ui/button'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'

interface ProductImagesEditorProps {
  productId: string
}

export function ProductImagesEditor({ productId }: ProductImagesEditorProps) {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [previewImage, setPreviewImage] = useState<ProductImage | null>(null)

  // Fetch images
  const { data: images = [], isLoading } = useQuery({
    queryKey: ['product-images', productId],
    queryFn: () => getProductImages(productId),
  })

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadProductImage(productId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product-images', productId] })
      queryClient.invalidateQueries({ queryKey: ['product', productId] })
      setUploadError(null)
    },
    onError: (error: Error) => {
      setUploadError(error.message || 'Failed to upload image')
    },
  })

  // Set primary mutation
  const setPrimaryMutation = useMutation({
    mutationFn: (imageId: string) => setPrimaryImage(productId, imageId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product-images', productId] })
      queryClient.invalidateQueries({ queryKey: ['product', productId] })
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (imageId: string) => deleteProductImage(productId, imageId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product-images', productId] })
      queryClient.invalidateQueries({ queryKey: ['product', productId] })
    },
  })

  // Rotate mutation
  const rotateMutation = useMutation({
    mutationFn: (imageId: string) => rotateProductImage(productId, imageId, 90),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product-images', productId] })
      queryClient.invalidateQueries({ queryKey: ['product', productId] })
    },
  })

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    setIsUploading(true)
    setUploadError(null)

    // Upload files one at a time
    for (const file of Array.from(files)) {
      try {
        await uploadMutation.mutateAsync(file)
      } catch {
        // Error handled by mutation
      }
    }

    setIsUploading(false)
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleDrop = async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()

    const files = event.dataTransfer.files
    if (!files || files.length === 0) return

    setIsUploading(true)
    setUploadError(null)

    for (const file of Array.from(files)) {
      if (file.type.startsWith('image/')) {
        try {
          await uploadMutation.mutateAsync(file)
        } catch {
          // Error handled by mutation
        }
      }
    }

    setIsUploading(false)
  }

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
  }

  // Sort images: primary first, then by display_order
  const sortedImages = [...images].sort((a, b) => {
    if (a.is_primary && !b.is_primary) return -1
    if (!a.is_primary && b.is_primary) return 1
    return a.display_order - b.display_order
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Upload Area */}
      <div
        className={cn(
          'border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors',
          'hover:border-primary hover:bg-primary/5',
          isUploading && 'opacity-50 pointer-events-none'
        )}
        onClick={() => fileInputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          className="hidden"
          onChange={handleFileSelect}
        />
        {isUploading ? (
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <span className="text-sm text-muted-foreground">Uploading...</span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <Upload className="h-8 w-8 text-muted-foreground" />
            <div>
              <span className="text-sm font-medium">Click to upload</span>
              <span className="text-sm text-muted-foreground"> or drag and drop</span>
            </div>
            <span className="text-xs text-muted-foreground">
              JPEG, PNG or WebP (max 10MB)
            </span>
          </div>
        )}
      </div>

      {/* Error Message */}
      {uploadError && (
        <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-lg flex items-center justify-between">
          <span>{uploadError}</span>
          <button onClick={() => setUploadError(null)}>
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Images Grid */}
      {sortedImages.length > 0 ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {sortedImages.map((image) => (
            <ImageCard
              key={`${image.id}-${image.updated_at}`}
              image={image}
              onSetPrimary={() => setPrimaryMutation.mutate(image.id)}
              onDelete={() => deleteMutation.mutate(image.id)}
              onRotate={() => rotateMutation.mutate(image.id)}
              onPreview={() => setPreviewImage(image)}
              isSettingPrimary={setPrimaryMutation.isPending}
              isDeleting={deleteMutation.isPending}
              isRotating={rotateMutation.isPending}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-muted-foreground">
          <ImagePlus className="h-12 w-12 mx-auto mb-2 opacity-50" />
          <p>No images yet</p>
          <p className="text-sm">Upload images to display in the shop</p>
        </div>
      )}

      {/* Full Image Preview Dialog */}
      <Dialog open={!!previewImage} onOpenChange={(open) => !open && setPreviewImage(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh] p-0 overflow-hidden">
          <DialogTitle className="sr-only">
            {previewImage?.original_filename || 'Image Preview'}
          </DialogTitle>
          {previewImage && (
            <div className="relative">
              <img
                src={getImageUrl(previewImage.image_url, previewImage.updated_at)}
                alt={previewImage.alt_text || 'Product image'}
                className="w-full h-auto max-h-[85vh] object-contain"
              />
              <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white p-3 text-sm">
                {previewImage.original_filename || 'Image'}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

interface ImageCardProps {
  image: ProductImage
  onSetPrimary: () => void
  onDelete: () => void
  onRotate: () => void
  onPreview: () => void
  isSettingPrimary: boolean
  isDeleting: boolean
  isRotating: boolean
}

function ImageCard({
  image,
  onSetPrimary,
  onDelete,
  onRotate,
  onPreview,
  isSettingPrimary,
  isDeleting,
  isRotating,
}: ImageCardProps) {
  // Use thumbnail if available, otherwise full image (with API base URL and cache-busting)
  const displayUrl = getImageUrl(image.thumbnail_url || image.image_url, image.updated_at)

  return (
    <div className="group relative rounded-lg border bg-card overflow-hidden">
      {/* Image */}
      <div className="aspect-square bg-muted">
        <img
          key={displayUrl}
          src={displayUrl}
          alt={image.alt_text || 'Product image'}
          className="w-full h-full object-cover"
        />
      </div>

      {/* Primary Badge */}
      {image.is_primary && (
        <div className="absolute top-2 left-2 bg-primary text-primary-foreground text-xs px-2 py-1 rounded-full flex items-center gap-1">
          <Star className="h-3 w-3 fill-current" />
          Primary
        </div>
      )}

      {/* Actions Overlay */}
      <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
        {/* Preview button */}
        <Button
          size="sm"
          variant="secondary"
          onClick={onPreview}
          title="View full image"
        >
          <Eye className="h-4 w-4" />
        </Button>

        {!image.is_primary && (
          <Button
            size="sm"
            variant="secondary"
            onClick={onSetPrimary}
            disabled={isSettingPrimary}
          >
            {isSettingPrimary ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Star className="h-4 w-4" />
            )}
            Set Primary
          </Button>
        )}

        <Button
          size="sm"
          variant="secondary"
          onClick={onRotate}
          disabled={isRotating}
          title="Rotate 90° clockwise"
        >
          {isRotating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RotateCw className="h-4 w-4" />
          )}
        </Button>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button size="sm" variant="destructive" disabled={isDeleting}>
              {isDeleting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Image</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to delete this image? This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={onDelete}>Delete</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      {/* File info */}
      <div className="p-2 text-xs text-muted-foreground truncate">
        {image.original_filename || 'Image'}
      </div>
    </div>
  )
}
