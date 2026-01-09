/**
 * TeamSettings Component
 *
 * Manages team members, roles, and invitations.
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  Crown,
  Loader2,
  MoreHorizontal,
  Shield,
  Trash2,
  User,
  UserPlus,
  Users,
} from 'lucide-react'

import {
  listTenantMembers,
  inviteTenantMember,
  updateMemberRole,
  removeTenantMember,
  type TenantMember,
  type UserRole,
} from '@/lib/api/settings'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'

const ROLE_OPTIONS: { value: UserRole; label: string; description: string }[] = [
  { value: 'owner', label: 'Owner', description: 'Full access including billing and user management' },
  { value: 'admin', label: 'Admin', description: 'Full access except billing' },
  { value: 'member', label: 'Member', description: 'Can create and edit data' },
  { value: 'viewer', label: 'Viewer', description: 'Read-only access' },
]

const inviteFormSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  role: z.enum(['owner', 'admin', 'member', 'viewer']).default('member'),
})

type InviteFormValues = z.infer<typeof inviteFormSchema>

function getRoleIcon(role: UserRole) {
  switch (role) {
    case 'owner':
      return <Crown className="h-4 w-4 text-yellow-500" />
    case 'admin':
      return <Shield className="h-4 w-4 text-blue-500" />
    default:
      return <User className="h-4 w-4 text-gray-500" />
  }
}

function getRoleBadgeVariant(role: UserRole): 'default' | 'secondary' | 'outline' {
  switch (role) {
    case 'owner':
      return 'default'
    case 'admin':
      return 'secondary'
    default:
      return 'outline'
  }
}

export function TeamSettings() {
  const queryClient = useQueryClient()
  const [inviteOpen, setInviteOpen] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<TenantMember | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['tenant-members'],
    queryFn: listTenantMembers,
  })

  const form = useForm<InviteFormValues>({
    resolver: zodResolver(inviteFormSchema),
    defaultValues: {
      email: '',
      role: 'member',
    },
  })

  const inviteMutation = useMutation({
    mutationFn: inviteTenantMember,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenant-members'] })
      setInviteOpen(false)
      form.reset()
    },
  })

  const updateRoleMutation = useMutation({
    mutationFn: ({ memberId, role }: { memberId: string; role: UserRole }) =>
      updateMemberRole(memberId, { role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenant-members'] })
    },
  })

  const removeMutation = useMutation({
    mutationFn: removeTenantMember,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenant-members'] })
      setDeleteConfirm(null)
    },
  })

  const onInviteSubmit = (data: InviteFormValues) => {
    inviteMutation.mutate({
      email: data.email,
      role: data.role,
    })
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>Failed to load team members</AlertDescription>
      </Alert>
    )
  }

  const members = data?.members ?? []

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              <CardTitle>Team Members</CardTitle>
            </div>
            <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
              <DialogTrigger asChild>
                <Button>
                  <UserPlus className="mr-2 h-4 w-4" />
                  Invite Member
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Invite Team Member</DialogTitle>
                  <DialogDescription>
                    Invite a user to join your organization. They must have an existing account.
                  </DialogDescription>
                </DialogHeader>
                <Form {...form}>
                  <form onSubmit={form.handleSubmit(onInviteSubmit)} className="space-y-4">
                    <FormField
                      control={form.control}
                      name="email"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Email Address</FormLabel>
                          <FormControl>
                            <Input
                              type="email"
                              placeholder="user@example.com"
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="role"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Role</FormLabel>
                          <Select
                            onValueChange={field.onChange}
                            defaultValue={field.value}
                          >
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {ROLE_OPTIONS.map((option) => (
                                <SelectItem key={option.value} value={option.value}>
                                  <div>
                                    <span>{option.label}</span>
                                    <span className="ml-2 text-xs text-muted-foreground">
                                      - {option.description}
                                    </span>
                                  </div>
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {inviteMutation.isError && (
                      <Alert variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>
                          {inviteMutation.error instanceof Error
                            ? inviteMutation.error.message
                            : 'Failed to invite member'}
                        </AlertDescription>
                      </Alert>
                    )}

                    <DialogFooter>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => setInviteOpen(false)}
                      >
                        Cancel
                      </Button>
                      <Button type="submit" disabled={inviteMutation.isPending}>
                        {inviteMutation.isPending && (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        )}
                        Send Invite
                      </Button>
                    </DialogFooter>
                  </form>
                </Form>
              </DialogContent>
            </Dialog>
          </div>
          <CardDescription>
            Manage who has access to your organization
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="divide-y">
            {members.map((member) => (
              <div
                key={member.id}
                className="flex items-center justify-between py-4 first:pt-0 last:pb-0"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
                    {getRoleIcon(member.role)}
                  </div>
                  <div>
                    <p className="font-medium">
                      {member.full_name || member.email}
                    </p>
                    <p className="text-sm text-muted-foreground">{member.email}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={getRoleBadgeVariant(member.role)}>
                    {member.role}
                  </Badge>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      {ROLE_OPTIONS.map((option) => (
                        <DropdownMenuItem
                          key={option.value}
                          disabled={member.role === option.value || updateRoleMutation.isPending}
                          onClick={() =>
                            updateRoleMutation.mutate({
                              memberId: member.id,
                              role: option.value,
                            })
                          }
                        >
                          Make {option.label}
                        </DropdownMenuItem>
                      ))}
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        className="text-destructive"
                        onClick={() => setDeleteConfirm(member)}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Remove
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
            ))}

            {members.length === 0 && (
              <p className="py-8 text-center text-muted-foreground">
                No team members yet. Invite someone to get started.
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteConfirm} onOpenChange={() => setDeleteConfirm(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove Team Member</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to remove {deleteConfirm?.full_name || deleteConfirm?.email} from
              the organization? They will lose access to all data.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteConfirm && removeMutation.mutate(deleteConfirm.id)}
            >
              {removeMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
