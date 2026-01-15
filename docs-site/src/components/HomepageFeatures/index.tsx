import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  icon: string;
  description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Inventory Management',
    icon: '📦',
    description: (
      <>
        Track filament spools with unique IDs, monitor remaining weight,
        and get low-stock alerts. Know exactly what materials you have
        and what you need to order.
      </>
    ),
  },
  {
    title: 'Product Catalog',
    icon: '🏭',
    description: (
      <>
        Define products with multi-material bills of materials.
        Automatic cost calculation keeps your pricing profitable
        across all your marketplace listings.
      </>
    ),
  },
  {
    title: 'Production Tracking',
    icon: '📊',
    description: (
      <>
        Track print jobs from start to finish. Spool weighing for
        accurate material usage, variance analysis, and quality ratings
        help optimize your workflow.
      </>
    ),
  },
  {
    title: 'Self-Hosted',
    icon: '🏠',
    description: (
      <>
        Your data stays on your infrastructure. Deploy with Docker Compose
        or Kubernetes. No subscription fees, no vendor lock-in,
        complete control over your business data.
      </>
    ),
  },
  {
    title: 'Open Source',
    icon: '💻',
    description: (
      <>
        MIT licensed and community-driven. Inspect the code, contribute
        features, or customize for your needs. Built by makers, for makers.
      </>
    ),
  },
  {
    title: 'Modern Stack',
    icon: '⚡',
    description: (
      <>
        FastAPI backend with async Python, React frontend with TypeScript.
        Full observability with OpenTelemetry. Enterprise-grade architecture
        for your growing business.
      </>
    ),
  },
];

function Feature({title, icon, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className={styles.featureCard}>
        <div className={styles.featureIcon}>{icon}</div>
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <Heading as="h2" className="text--center margin-bottom--lg">
          Everything You Need to Run Your 3D Printing Business
        </Heading>
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
