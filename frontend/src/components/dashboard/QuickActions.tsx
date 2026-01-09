/**
 * Quick Actions Panel
 *
 * Provides quick access to common actions from the dashboard.
 */

import { Link } from '@tanstack/react-router';
import {
  Plus,
  Printer,
  Package,
  Boxes,
  Scale,
  FileText,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface QuickAction {
  label: string;
  description: string;
  icon: React.ReactNode;
  to: string;
  variant?: 'default' | 'secondary' | 'outline';
}

const quickActions: QuickAction[] = [
  {
    label: 'New Print Run',
    description: 'Start a production run',
    icon: <Printer className="h-4 w-4" />,
    to: '/production-runs/new',
    variant: 'default',
  },
  {
    label: 'Add Spool',
    description: 'Register new filament',
    icon: <Plus className="h-4 w-4" />,
    to: '/inventory/new',
    variant: 'outline',
  },
  {
    label: 'New Model',
    description: 'Add 3D model',
    icon: <Boxes className="h-4 w-4" />,
    to: '/models/new',
    variant: 'outline',
  },
  {
    label: 'New Product',
    description: 'Create sellable item',
    icon: <Package className="h-4 w-4" />,
    to: '/products/new',
    variant: 'outline',
  },
  {
    label: 'Weigh Spool',
    description: 'Update spool weight',
    icon: <Scale className="h-4 w-4" />,
    to: '/inventory',
    variant: 'outline',
  },
  {
    label: 'View Reports',
    description: 'Analytics & insights',
    icon: <FileText className="h-4 w-4" />,
    to: '/reports',
    variant: 'outline',
  },
];

export function QuickActions() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle>Quick Actions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-2">
          {quickActions.map((action) => (
            <Button
              key={action.label}
              variant={action.variant}
              className="h-auto flex-col items-start gap-1 p-3"
              asChild
            >
              <Link to={action.to}>
                <div className="flex items-center gap-2 w-full">
                  {action.icon}
                  <span className="font-medium">{action.label}</span>
                </div>
                <span className="text-xs text-muted-foreground font-normal w-full text-left">
                  {action.description}
                </span>
              </Link>
            </Button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
