/**
 * Module system types for dynamic navigation based on tenant type.
 */

/**
 * Tenant types matching backend TenantType enum.
 */
export type TenantType =
  | 'three_d_print'
  | 'hand_knitting'
  | 'machine_knitting'
  | 'generic';

/**
 * Module status matching backend ModuleStatus enum.
 */
export type ModuleStatus = 'active' | 'disabled' | 'coming_soon';

/**
 * Route definition for a module.
 */
export interface ModuleRoute {
  path: string;
  label: string;
  icon?: string;
  exact?: boolean;
  badge?: number;
}

/**
 * Module definition from the backend API.
 */
export interface Module {
  name: string;
  display_name: string;
  description: string;
  icon: string;
  status: ModuleStatus;
  routes: ModuleRoute[];
  order: number;
  settings_schema?: Record<string, unknown>;
}

/**
 * Response from GET /api/v1/modules endpoint.
 */
export interface ModulesResponse {
  tenant_type: TenantType;
  modules: Module[];
}

/**
 * Icon mapping for dynamic icon resolution.
 * Maps icon names from backend to Lucide icon components.
 */
export const ICON_MAP: Record<string, string> = {
  // Dashboard
  'layout-dashboard': 'LayoutDashboard',

  // 3D Printing
  'package': 'Package',
  'layers': 'Layers',
  'box': 'Box',
  'play': 'Play',
  'printer': 'Printer',
  'wrench': 'Wrench',

  // Knitting
  'yarn': 'Palette',  // Using Palette as yarn icon
  'needle': 'Pen',    // Using Pen as needle icon
  'pattern': 'FileText',
  'project': 'FolderKanban',

  // Sales/Orders
  'store': 'Store',
  'shopping-bag': 'ShoppingBag',
  'folder-open': 'FolderOpen',
  'brush': 'Brush',

  // Settings
  'settings': 'Settings',
  'help-circle': 'HelpCircle',
};
