import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Batchivo',
  tagline: 'Complete 3D printing business management platform',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  // GitHub Pages deployment
  url: 'https://techize.github.io',
  baseUrl: '/batchivo/',

  organizationName: 'techize',
  projectName: 'batchivo',
  deploymentBranch: 'gh-pages',
  trailingSlash: false,

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/techize/batchivo/tree/main/docs-site/',
          showLastUpdateTime: true,
          showLastUpdateAuthor: true,
        },
        blog: {
          showReadingTime: true,
          feedOptions: {
            type: ['rss', 'atom'],
            xslt: true,
          },
          editUrl: 'https://github.com/techize/batchivo/tree/main/docs-site/',
          blogTitle: 'Batchivo Updates',
          blogDescription: 'Release notes and updates for Batchivo',
          onInlineTags: 'warn',
          onInlineAuthors: 'warn',
          onUntruncatedBlogPosts: 'warn',
        },
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/batchivo-social-card.png',
    colorMode: {
      defaultMode: 'dark',
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Batchivo',
      logo: {
        alt: 'Batchivo Logo',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Documentation',
        },
        {
          to: '/docs/api-reference/overview',
          label: 'API',
          position: 'left',
        },
        {to: '/blog', label: 'Blog', position: 'left'},
        {
          href: 'https://github.com/techize/batchivo',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Documentation',
          items: [
            {
              label: 'Getting Started',
              to: '/docs/getting-started/quickstart',
            },
            {
              label: 'Self-Hosting',
              to: '/docs/self-hosting/overview',
            },
            {
              label: 'API Reference',
              to: '/docs/api-reference/overview',
            },
          ],
        },
        {
          title: 'Community',
          items: [
            {
              label: 'GitHub Discussions',
              href: 'https://github.com/techize/batchivo/discussions',
            },
            {
              label: 'Contributing',
              href: 'https://github.com/techize/batchivo/blob/main/CONTRIBUTING.md',
            },
            {
              label: 'Code of Conduct',
              href: 'https://github.com/techize/batchivo/blob/main/CODE_OF_CONDUCT.md',
            },
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'Blog',
              to: '/blog',
            },
            {
              label: 'GitHub',
              href: 'https://github.com/techize/batchivo',
            },
            {
              label: 'Roadmap',
              href: 'https://github.com/techize/batchivo/blob/main/ROADMAP.md',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Batchivo Contributors. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'python', 'json', 'yaml', 'typescript'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
