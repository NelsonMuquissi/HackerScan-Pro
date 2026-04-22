import { MarketplaceContent } from '@/components/marketplace/MarketplaceContent';

export const metadata = {
  title: 'Security Marketplace | HackerScan Pro',
  description: 'Extend your security capabilities with premium modules and services.',
};

export default function MarketplacePage() {
  return (
    <div className="container mx-auto py-8">
      <MarketplaceContent />
    </div>
  );
}
