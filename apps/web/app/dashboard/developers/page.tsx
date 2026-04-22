import { DevelopersContent } from '@/components/developers/DevelopersContent';

export const metadata = {
  title: 'Developer Console | HackerScan Pro',
  description: 'Manage API keys and programmatic access for CI/CD integrations.',
};

export default function DevelopersPage() {
  return (
    <div className="container mx-auto py-8">
      <DevelopersContent />
    </div>
  );
}
