import { SchedulesManager } from '@/components/scans/SchedulesManager';

export const metadata = {
  title: 'Scan Scheduling | HackerScan Pro',
  description: 'Manage recurring security audits and automated vulnerability assessments.',
};

export default function SchedulingPage() {
  return (
    <div className="container mx-auto py-8">
      <SchedulesManager />
    </div>
  );
}
