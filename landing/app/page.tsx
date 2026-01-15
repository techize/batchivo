import Image from "next/image";
import Link from "next/link";

const features = [
  {
    icon: "📦",
    title: "Inventory Management",
    description:
      "Track filament spools with unique IDs, monitor remaining weight, and get low-stock alerts before you run out.",
  },
  {
    icon: "🏭",
    title: "Product Catalog",
    description:
      "Define products with multi-material bills of materials. Automatic cost calculation keeps your pricing profitable.",
  },
  {
    icon: "📊",
    title: "Production Tracking",
    description:
      "Track print jobs from start to finish. Spool weighing for accurate material usage and variance analysis.",
  },
  {
    icon: "💰",
    title: "Cost Analysis",
    description:
      "Know your true costs per product. Material, labor, and overhead tracking for data-driven pricing decisions.",
  },
  {
    icon: "🏠",
    title: "Self-Hosted",
    description:
      "Your data stays on your infrastructure. No subscription fees, no vendor lock-in, complete control.",
  },
  {
    icon: "💻",
    title: "Open Source",
    description:
      "MIT licensed and community-driven. Inspect the code, contribute features, or customize for your needs.",
  },
];

const steps = [
  {
    number: "1",
    title: "Deploy in Minutes",
    description:
      "Run a single Docker Compose command and you're up and running. No complex setup required.",
  },
  {
    number: "2",
    title: "Add Your Inventory",
    description:
      "Import your spools or add them manually. Track materials, colors, brands, and costs.",
  },
  {
    number: "3",
    title: "Define Products",
    description:
      "Create your product catalog with bills of materials. Batchivo calculates costs automatically.",
  },
  {
    number: "4",
    title: "Track Production",
    description:
      "Log print jobs, weigh spools, and analyze variance. Make data-driven decisions.",
  },
];

export default function Home() {
  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <Image src="/logo.svg" alt="Batchivo" width={32} height={32} />
              <span className="font-bold text-xl">Batchivo</span>
            </div>
            <div className="hidden md:flex items-center gap-8">
              <Link
                href="#features"
                className="text-slate-600 dark:text-slate-300 hover:text-cyan-600 dark:hover:text-cyan-400"
              >
                Features
              </Link>
              <Link
                href="#how-it-works"
                className="text-slate-600 dark:text-slate-300 hover:text-cyan-600 dark:hover:text-cyan-400"
              >
                How It Works
              </Link>
              <Link
                href="https://techize.github.io/batchivo/"
                className="text-slate-600 dark:text-slate-300 hover:text-cyan-600 dark:hover:text-cyan-400"
              >
                Docs
              </Link>
              <Link
                href="https://github.com/techize/batchivo"
                className="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
              >
                View on GitHub
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="hero-gradient pt-32 pb-20 px-4">
        <div className="max-w-5xl mx-auto text-center text-white">
          <div className="mb-6">
            <span className="inline-block bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full text-sm font-medium">
              Open Source & Self-Hosted
            </span>
          </div>
          <h1 className="text-4xl md:text-6xl font-bold mb-6 leading-tight">
            Run Your 3D Printing Business
            <br />
            <span className="text-cyan-200">Like a Pro</span>
          </h1>
          <p className="text-xl md:text-2xl text-cyan-100 mb-10 max-w-3xl mx-auto">
            Complete business management platform for 3D printing. Track
            inventory, manage products, monitor production, and optimize costs.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="https://techize.github.io/batchivo/docs/getting-started/quickstart"
              className="bg-white text-cyan-700 hover:bg-cyan-50 px-8 py-4 rounded-xl font-semibold text-lg transition-colors shadow-lg"
            >
              Get Started Free
            </Link>
            <Link
              href="https://github.com/techize/batchivo"
              className="bg-transparent border-2 border-white text-white hover:bg-white/10 px-8 py-4 rounded-xl font-semibold text-lg transition-colors"
            >
              Star on GitHub
            </Link>
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section className="py-12 bg-slate-50 dark:bg-slate-800/50 border-y border-slate-200 dark:border-slate-700">
        <div className="max-w-5xl mx-auto px-4 text-center">
          <p className="text-slate-600 dark:text-slate-400 mb-6">
            Built with modern technologies
          </p>
          <div className="flex flex-wrap justify-center items-center gap-8 md:gap-12 text-slate-500 dark:text-slate-400">
            <div className="flex items-center gap-2">
              <span className="text-2xl">⚡</span>
              <span className="font-medium">FastAPI</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-2xl">⚛️</span>
              <span className="font-medium">React</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-2xl">🐳</span>
              <span className="font-medium">Docker</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-2xl">🐘</span>
              <span className="font-medium">PostgreSQL</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-2xl">📊</span>
              <span className="font-medium">OpenTelemetry</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Everything You Need to Succeed
            </h2>
            <p className="text-xl text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
              From inventory tracking to production analytics, Batchivo has the
              tools to run your 3D printing business efficiently.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="feature-card bg-white dark:bg-slate-800 rounded-2xl p-8 shadow-sm border border-slate-200 dark:border-slate-700"
              >
                <div className="text-4xl mb-4">{feature.icon}</div>
                <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                <p className="text-slate-600 dark:text-slate-400">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section
        id="how-it-works"
        className="py-20 px-4 bg-slate-50 dark:bg-slate-800/50"
      >
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Up and Running in Minutes
            </h2>
            <p className="text-xl text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
              No complex setup. Deploy with Docker and start managing your
              business immediately.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {steps.map((step, index) => (
              <div key={index} className="text-center">
                <div className="w-16 h-16 bg-cyan-600 text-white rounded-2xl flex items-center justify-center text-2xl font-bold mx-auto mb-4">
                  {step.number}
                </div>
                <h3 className="text-lg font-semibold mb-2">{step.title}</h3>
                <p className="text-slate-600 dark:text-slate-400">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Code Preview */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Deploy with One Command
            </h2>
            <p className="text-xl text-slate-600 dark:text-slate-400">
              Get Batchivo running in under 5 minutes
            </p>
          </div>
          <div className="bg-slate-900 rounded-2xl p-6 md:p-8 shadow-xl">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span className="ml-2 text-slate-500 text-sm">terminal</span>
            </div>
            <pre className="text-sm md:text-base text-slate-300 overflow-x-auto">
              <code>{`# Clone the repository
git clone https://github.com/techize/batchivo.git
cd batchivo

# Configure and start
cp backend/.env.example backend/.env
docker-compose up -d

# That's it! Open http://localhost:5173`}</code>
            </pre>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-4 hero-gradient">
        <div className="max-w-4xl mx-auto text-center text-white">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            Ready to Take Control of Your Business?
          </h2>
          <p className="text-xl text-cyan-100 mb-10 max-w-2xl mx-auto">
            Join the community of 3D printing businesses using Batchivo to
            manage their operations. Free, open source, forever.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="https://techize.github.io/batchivo/docs/getting-started/quickstart"
              className="bg-white text-cyan-700 hover:bg-cyan-50 px-8 py-4 rounded-xl font-semibold text-lg transition-colors shadow-lg"
            >
              Read the Docs
            </Link>
            <Link
              href="https://github.com/techize/batchivo/discussions"
              className="bg-transparent border-2 border-white text-white hover:bg-white/10 px-8 py-4 rounded-xl font-semibold text-lg transition-colors"
            >
              Join the Community
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-4 bg-slate-900 text-slate-400">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Image src="/logo.svg" alt="Batchivo" width={24} height={24} />
                <span className="font-bold text-white">Batchivo</span>
              </div>
              <p className="text-sm">
                Complete 3D printing business management platform. Self-hosted,
                open source, forever free.
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-4">Documentation</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link
                    href="https://techize.github.io/batchivo/docs/getting-started/quickstart"
                    className="hover:text-cyan-400"
                  >
                    Getting Started
                  </Link>
                </li>
                <li>
                  <Link
                    href="https://techize.github.io/batchivo/docs/self-hosting/overview"
                    className="hover:text-cyan-400"
                  >
                    Self-Hosting
                  </Link>
                </li>
                <li>
                  <Link
                    href="https://techize.github.io/batchivo/docs/api-reference/overview"
                    className="hover:text-cyan-400"
                  >
                    API Reference
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-4">Community</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link
                    href="https://github.com/techize/batchivo/discussions"
                    className="hover:text-cyan-400"
                  >
                    GitHub Discussions
                  </Link>
                </li>
                <li>
                  <Link
                    href="https://github.com/techize/batchivo/blob/main/CONTRIBUTING.md"
                    className="hover:text-cyan-400"
                  >
                    Contributing
                  </Link>
                </li>
                <li>
                  <Link
                    href="https://github.com/techize/batchivo/blob/main/ROADMAP.md"
                    className="hover:text-cyan-400"
                  >
                    Roadmap
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-4">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link
                    href="https://github.com/techize/batchivo/blob/main/LICENSE"
                    className="hover:text-cyan-400"
                  >
                    MIT License
                  </Link>
                </li>
                <li>
                  <Link
                    href="https://github.com/techize/batchivo/blob/main/CODE_OF_CONDUCT.md"
                    className="hover:text-cyan-400"
                  >
                    Code of Conduct
                  </Link>
                </li>
                <li>
                  <Link
                    href="https://github.com/techize/batchivo/blob/main/SECURITY.md"
                    className="hover:text-cyan-400"
                  >
                    Security Policy
                  </Link>
                </li>
              </ul>
            </div>
          </div>
          <div className="border-t border-slate-800 pt-8 text-center text-sm">
            <p>
              &copy; {new Date().getFullYear()} Batchivo Contributors. Built by
              makers, for makers.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
