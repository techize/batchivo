/**
 * ModelFilesEditor Component
 *
 * Manages 3D model files: upload, set primary, delete.
 * Supports STL, 3MF, and gcode files.
 * Supports both uploading files and linking local file paths.
 */

import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  CheckCircle2,
  Download,
  File,
  FileBox,
  FileCog,
  FolderOpen,
  Link2,
  Loader2,
  Star,
  Trash2,
  Upload,
} from 'lucide-react'

import {
  getModelFiles,
  uploadModelFile,
  updateModelFile,
  deleteModelFile,
  getModelFileDownloadUrl,
  linkLocalModelFile,
  validateLocalPath,
  type ModelFile,
  type ModelFileType,
  type LocalPathValidationResponse,
} from '@/lib/api/models'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface ModelFilesEditorProps {
  modelId: string
}

// File type labels for display
const FILE_TYPE_LABELS: Record<ModelFileType, string> = {
  source_stl: 'STL File',
  source_3mf: '3MF File',
  slicer_project: 'Slicer Project',
  gcode: 'G-code',
  plate_layout: 'Plate Layout',
}

// File type icons
function FileTypeIcon({ type }: { type: ModelFileType }) {
  switch (type) {
    case 'source_stl':
    case 'source_3mf':
      return <FileBox className="h-5 w-5" />
    case 'slicer_project':
      return <FileCog className="h-5 w-5" />
    case 'gcode':
    case 'plate_layout':
      return <File className="h-5 w-5" />
    default:
      return <File className="h-5 w-5" />
  }
}

// Format file size
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function ModelFilesEditor({ modelId }: ModelFilesEditorProps) {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [selectedFileType, setSelectedFileType] = useState<ModelFileType>('source_3mf')

  // Local file linking state
  const [localPath, setLocalPath] = useState('')
  const [isValidatingPath, setIsValidatingPath] = useState(false)
  const [pathValidation, setPathValidation] = useState<LocalPathValidationResponse | null>(null)
  const [isLinking, setIsLinking] = useState(false)

  // Fetch files
  const { data: files = [], isLoading } = useQuery({
    queryKey: ['model-files', modelId],
    queryFn: () => getModelFiles(modelId),
  })

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: ({ file, fileType }: { file: File; fileType: ModelFileType }) =>
      uploadModelFile(modelId, file, fileType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['model-files', modelId] })
      queryClient.invalidateQueries({ queryKey: ['model', modelId] })
      setUploadError(null)
    },
    onError: (error: Error) => {
      setUploadError(error.message || 'Failed to upload file')
    },
  })

  // Set primary mutation
  const setPrimaryMutation = useMutation({
    mutationFn: (fileId: string) =>
      updateModelFile(modelId, fileId, { is_primary: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['model-files', modelId] })
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (fileId: string) => deleteModelFile(modelId, fileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['model-files', modelId] })
    },
  })

  // Link local file mutation
  const linkMutation = useMutation({
    mutationFn: ({ path, fileType }: { path: string; fileType: ModelFileType }) =>
      linkLocalModelFile(modelId, path, fileType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['model-files', modelId] })
      queryClient.invalidateQueries({ queryKey: ['model', modelId] })
      setLocalPath('')
      setPathValidation(null)
      setUploadError(null)
    },
    onError: (error: Error) => {
      setUploadError(error.message || 'Failed to link local file')
    },
  })

  // Validate local path when it changes (debounced)
  const handlePathChange = async (path: string) => {
    setLocalPath(path)
    setPathValidation(null)

    if (!path.trim()) return

    setIsValidatingPath(true)
    try {
      const result = await validateLocalPath(path)
      setPathValidation(result)
    } catch {
      setPathValidation(null)
    } finally {
      setIsValidatingPath(false)
    }
  }

  const handleLinkLocalFile = async () => {
    if (!localPath.trim() || !pathValidation?.exists || !pathValidation?.is_file) return

    setIsLinking(true)
    setUploadError(null)

    try {
      await linkMutation.mutateAsync({ path: localPath, fileType: selectedFileType })
    } catch {
      // Error handled by mutation
    } finally {
      setIsLinking(false)
    }
  }

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const inputFiles = event.target.files
    if (!inputFiles || inputFiles.length === 0) return

    setIsUploading(true)
    setUploadError(null)

    for (const file of Array.from(inputFiles)) {
      try {
        await uploadMutation.mutateAsync({ file, fileType: selectedFileType })
      } catch {
        // Error handled by mutation
      }
    }

    setIsUploading(false)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleDrop = async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()

    const droppedFiles = event.dataTransfer.files
    if (!droppedFiles || droppedFiles.length === 0) return

    setIsUploading(true)
    setUploadError(null)

    for (const file of Array.from(droppedFiles)) {
      // Auto-detect file type from extension
      const ext = file.name.toLowerCase().split('.').pop()
      let fileType: ModelFileType = selectedFileType
      if (ext === 'stl') fileType = 'source_stl'
      else if (ext === '3mf') fileType = 'source_3mf'
      else if (ext === 'gcode' || ext === 'gco' || ext === 'g') fileType = 'gcode'

      try {
        await uploadMutation.mutateAsync({ file, fileType })
      } catch {
        // Error handled by mutation
      }
    }

    setIsUploading(false)
  }

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
  }

  const handleDownload = (file: ModelFile) => {
    const url = getModelFileDownloadUrl(modelId, file.id)
    const token = localStorage.getItem('access_token')
    // Create a temporary link with auth header via fetch
    fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((response) => response.blob())
      .then((blob) => {
        const blobUrl = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = blobUrl
        link.download = file.original_filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(blobUrl)
      })
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileBox className="h-5 w-5" />
            3D Model Files
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileBox className="h-5 w-5" />
          3D Model Files
          {files.length > 0 && (
            <Badge variant="secondary" className="ml-2">
              {files.length}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Upload/Link tabs */}
        <Tabs defaultValue="upload" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="upload" className="flex items-center gap-2">
              <Upload className="h-4 w-4" />
              Upload File
            </TabsTrigger>
            <TabsTrigger value="link" className="flex items-center gap-2">
              <Link2 className="h-4 w-4" />
              Link Local File
            </TabsTrigger>
          </TabsList>

          {/* Upload tab content */}
          <TabsContent value="upload">
            <div
              className={cn(
                'border-2 border-dashed rounded-lg p-6 text-center transition-colors',
                'hover:border-primary/50 hover:bg-muted/50',
                isUploading && 'opacity-50 pointer-events-none'
              )}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".stl,.3mf,.gcode,.gco,.g"
                multiple
                onChange={handleFileSelect}
              />

              <div className="flex flex-col items-center gap-3">
                <Upload className="h-8 w-8 text-muted-foreground" />
                <div className="text-sm text-muted-foreground">
                  Drag and drop files here, or click to select
                </div>
                <div className="text-xs text-muted-foreground">
                  Supports STL, 3MF, and G-code files (up to 500MB)
                </div>

                <div className="flex items-center gap-2 mt-2">
                  <Select
                    value={selectedFileType}
                    onValueChange={(v) => setSelectedFileType(v as ModelFileType)}
                  >
                    <SelectTrigger className="w-[180px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="source_stl">STL File</SelectItem>
                      <SelectItem value="source_3mf">3MF File</SelectItem>
                      <SelectItem value="slicer_project">Slicer Project</SelectItem>
                      <SelectItem value="gcode">G-code</SelectItem>
                      <SelectItem value="plate_layout">Plate Layout</SelectItem>
                    </SelectContent>
                  </Select>

                  <Button
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading}
                  >
                    {isUploading ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <Upload className="h-4 w-4 mr-2" />
                    )}
                    Select Files
                  </Button>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* Link local file tab content */}
          <TabsContent value="link">
            <div className="border rounded-lg p-4 space-y-4">
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <FolderOpen className="h-5 w-5 text-muted-foreground" />
                  <span className="text-sm font-medium">Local File Path</span>
                </div>
                <div className="text-xs text-muted-foreground">
                  Enter the full path to a file on your local filesystem (e.g., OrcaSlicer project)
                </div>
              </div>

              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Input
                    placeholder="/path/to/your/file.3mf"
                    value={localPath}
                    onChange={(e) => handlePathChange(e.target.value)}
                    className={cn(
                      'pr-10',
                      pathValidation?.exists && pathValidation?.is_file && 'border-green-500',
                      pathValidation && !pathValidation.exists && 'border-red-500'
                    )}
                  />
                  {isValidatingPath && (
                    <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
                  )}
                  {!isValidatingPath && pathValidation?.exists && pathValidation?.is_file && (
                    <CheckCircle2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-green-500" />
                  )}
                  {!isValidatingPath && pathValidation && !pathValidation.exists && (
                    <AlertCircle className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-red-500" />
                  )}
                </div>
              </div>

              {pathValidation && (
                <div
                  className={cn(
                    'text-sm p-2 rounded',
                    pathValidation.exists && pathValidation.is_file
                      ? 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300'
                      : 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300'
                  )}
                >
                  {pathValidation.exists && pathValidation.is_file ? (
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4" />
                      <span>
                        Found: {pathValidation.filename}
                        {pathValidation.file_size && ` (${formatFileSize(pathValidation.file_size)})`}
                      </span>
                    </div>
                  ) : pathValidation.exists && !pathValidation.is_file ? (
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4" />
                      <span>Path exists but is not a file (might be a directory)</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4" />
                      <span>File not found at this path</span>
                    </div>
                  )}
                </div>
              )}

              <div className="flex items-center gap-2">
                <Select
                  value={selectedFileType}
                  onValueChange={(v) => setSelectedFileType(v as ModelFileType)}
                >
                  <SelectTrigger className="w-[180px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="source_stl">STL File</SelectItem>
                    <SelectItem value="source_3mf">3MF File</SelectItem>
                    <SelectItem value="slicer_project">Slicer Project</SelectItem>
                    <SelectItem value="gcode">G-code</SelectItem>
                    <SelectItem value="plate_layout">Plate Layout</SelectItem>
                  </SelectContent>
                </Select>

                <Button
                  onClick={handleLinkLocalFile}
                  disabled={isLinking || !pathValidation?.exists || !pathValidation?.is_file}
                >
                  {isLinking ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Link2 className="h-4 w-4 mr-2" />
                  )}
                  Link File
                </Button>
              </div>
            </div>
          </TabsContent>
        </Tabs>

        {/* Error message */}
        {uploadError && (
          <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
            {uploadError}
          </div>
        )}

        {/* File list */}
        {files.length > 0 && (
          <div className="space-y-2">
            {files.map((file) => (
              <div
                key={file.id}
                className={cn(
                  'flex items-center gap-3 p-3 rounded-lg border',
                  file.is_primary && 'border-primary bg-primary/5'
                )}
              >
                {/* File icon */}
                <div className="text-muted-foreground">
                  <FileTypeIcon type={file.file_type as ModelFileType} />
                </div>

                {/* File info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">
                      {file.original_filename}
                    </span>
                    {file.is_primary && (
                      <Badge variant="default" className="shrink-0">
                        <Star className="h-3 w-3 mr-1" />
                        Primary
                      </Badge>
                    )}
                    {file.file_location === 'local_reference' && (
                      <Badge
                        variant={file.local_path_exists ? 'secondary' : 'destructive'}
                        className="shrink-0"
                      >
                        <Link2 className="h-3 w-3 mr-1" />
                        {file.local_path_exists ? 'Local' : 'Missing'}
                      </Badge>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground flex items-center gap-2 flex-wrap">
                    <span>{FILE_TYPE_LABELS[file.file_type as ModelFileType]}</span>
                    {file.file_size && (
                      <>
                        <span>|</span>
                        <span>{formatFileSize(file.file_size)}</span>
                      </>
                    )}
                    {file.part_name && (
                      <>
                        <span>|</span>
                        <span>Part: {file.part_name}</span>
                      </>
                    )}
                    {file.version && (
                      <>
                        <span>|</span>
                        <span>{file.version}</span>
                      </>
                    )}
                    {file.file_location === 'local_reference' && file.local_path && (
                      <>
                        <span>|</span>
                        <span className="truncate max-w-[200px]" title={file.local_path}>
                          {file.local_path}
                        </span>
                      </>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1">
                  {/* Download */}
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDownload(file)}
                    title="Download"
                  >
                    <Download className="h-4 w-4" />
                  </Button>

                  {/* Set Primary */}
                  {!file.is_primary && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setPrimaryMutation.mutate(file.id)}
                      disabled={setPrimaryMutation.isPending}
                      title="Set as primary"
                    >
                      <Star className="h-4 w-4" />
                    </Button>
                  )}

                  {/* Delete */}
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive hover:text-destructive"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Delete File</AlertDialogTitle>
                        <AlertDialogDescription>
                          Are you sure you want to delete "{file.original_filename}"?
                          This action cannot be undone.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => deleteMutation.mutate(file.id)}
                          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                          Delete
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {files.length === 0 && (
          <div className="text-center py-6 text-muted-foreground">
            No files uploaded yet. Upload STL, 3MF, or G-code files to get started.
          </div>
        )}
      </CardContent>
    </Card>
  )
}
