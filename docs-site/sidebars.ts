import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    {
      type: 'doc',
      id: 'intro',
      label: 'Introduction',
    },
    {
      type: 'category',
      label: 'Getting Started',
      collapsed: false,
      items: [
        'getting-started/quickstart',
        'getting-started/prerequisites',
        'getting-started/installation',
      ],
    },
    {
      type: 'category',
      label: 'Self-Hosting',
      items: [
        'self-hosting/overview',
        'self-hosting/docker-compose',
        'self-hosting/kubernetes',
        'self-hosting/environment-variables',
        'self-hosting/backup-restore',
      ],
    },
    {
      type: 'category',
      label: 'User Guide',
      items: [
        'guides/inventory-management',
        'guides/products-catalog',
        'guides/production-runs',
        'guides/costing-pricing',
      ],
    },
    {
      type: 'category',
      label: 'API Reference',
      items: [
        'api-reference/overview',
        'api-reference/authentication',
        'api-reference/spools',
        'api-reference/products',
        'api-reference/production-runs',
      ],
    },
    {
      type: 'category',
      label: 'Development',
      items: [
        'development/contributing',
        'development/architecture',
        'development/testing',
        'development/roadmap',
      ],
    },
  ],
};

export default sidebars;
