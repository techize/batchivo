import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <img
          src="/batchivo/img/logo.svg"
          alt="Batchivo Logo"
          className={styles.heroLogo}
        />
        <Heading as="h1" className="hero__title">
          {siteConfig.title}
        </Heading>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/">
            Get Started
          </Link>
          <Link
            className="button button--outline button--secondary button--lg"
            to="https://github.com/techize/batchivo"
            style={{marginLeft: '1rem'}}>
            View on GitHub
          </Link>
        </div>
      </div>
    </header>
  );
}

function HomepageCallout() {
  return (
    <section className={styles.callout}>
      <div className="container">
        <div className="row">
          <div className="col col--8 col--offset-2">
            <Heading as="h2" className="text--center">
              Built for 3D Printing Businesses
            </Heading>
            <p className="text--center text--lg">
              Batchivo started as a spreadsheet for tracking personal 3D printing projects.
              Now it's a full-featured, self-hosted platform that helps you run your
              3D printing operation professionally and profitably.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title="Documentation"
      description="Complete 3D printing business management platform - track inventory, products, production runs, and costs">
      <HomepageHeader />
      <main>
        <HomepageCallout />
        <HomepageFeatures />
      </main>
    </Layout>
  );
}
