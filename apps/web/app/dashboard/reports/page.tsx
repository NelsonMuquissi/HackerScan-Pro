'use client';

import { useState, useEffect } from 'react';
import { 
  FileText, 
  Download, 
  Trash2, 
  Clock, 
  CheckCircle, 
  AlertCircle, 
  Loader2, 
  Search,
  ExternalLink
} from 'lucide-react';
import { listReports, deleteReport } from '@/lib/api';

export default function ReportsPage() {
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchReports = async () => {
    try {
      const data = await listReports();
      // Handle both plain arrays and paginated responses { results: [...] }
      let list: any[] = [];
      if (Array.isArray(data)) {
        list = data;
      } else if (data && typeof data === 'object' && 'results' in data) {
        list = (data as any).results;
      }
      setReports(list);
    } catch (error) {
      console.error('Failed to fetch reports:', error);
      setReports([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
    // Poll for status updates every 10 seconds if there are processing reports
    const interval = setInterval(() => {
      const hasProcessing = reports.some(r => r.status === 'PENDING' || r.status === 'PROCESSING');
      if (hasProcessing) {
        fetchReports();
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [reports]);

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this report?')) return;
    try {
      await deleteReport(id);
      setReports(reports.filter(r => r.id !== id));
    } catch (error) {
      alert('Failed to delete report');
    }
  };

  const filteredReports = reports.filter(r => 
    r.target_host.toLowerCase().includes(searchTerm.toLowerCase()) ||
    r.target_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const StatusBadge = ({ status }: { status: string }) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 border border-green-500/20 text-[10px] font-bold uppercase">
            <CheckCircle className="w-3 h-3" />
            Ready
          </span>
        );
      case 'PROCESSING':
      case 'PENDING':
        return (
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-bold uppercase">
            <Loader2 className="w-3 h-3 animate-spin" />
            Generating
          </span>
        );
      case 'FAILED':
        return (
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 text-[10px] font-bold uppercase">
            <AlertCircle className="w-3 h-3" />
            Failed
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-mono font-bold text-foreground flex items-center gap-2">
            <FileText className="w-6 h-6 text-neon-green" />
            Reports
          </h1>
          <p className="text-gray-400 font-mono text-sm mt-1">
            Manage and download your generated security audits.
          </p>
        </div>

        <div className="relative w-full md:w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search targets..."
            className="w-full bg-card-bg border border-card-border rounded-md pl-10 pr-4 py-2 text-sm font-mono focus:outline-none focus:border-neon-green transition-colors"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 text-neon-green animate-spin" />
          <span className="ml-3 font-mono text-gray-400">Fetching intelligence archives...</span>
        </div>
      ) : filteredReports.length > 0 ? (
        <div className="grid grid-cols-1 gap-4">
          {filteredReports.map((report) => (
            <div 
              key={report.id}
              className="bg-card-bg border border-card-border rounded-lg p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-neon-green/30 transition-all group"
            >
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded bg-neon-green/10 flex items-center justify-center text-neon-green flex-shrink-0">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-mono font-bold text-foreground">{report.target_host}</h3>
                    <StatusBadge status={report.status} />
                  </div>
                  <p className="text-xs text-gray-500 font-mono mt-0.5">
                    {report.type} {report.format} • Created {new Date(report.created_at).toLocaleString()}
                  </p>
                  <p className="text-[10px] text-gray-600 font-mono mt-1">
                    Scan ID: {report.scan.substring(0, 8)}...
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {report.status === 'COMPLETED' && report.file_url && (
                  <a 
                    href={report.file_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-neon-green text-black font-bold font-mono text-xs rounded hover:bg-[#00cc00] transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download
                  </a>
                )}
                
                <button 
                  onClick={() => handleDelete(report.id)}
                  className="p-2 text-gray-500 hover:text-red-500 hover:bg-red-500/10 rounded transition-colors"
                  title="Delete Report"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-card-bg border border-dashed border-card-border rounded-lg py-20 flex flex-col items-center justify-center">
          <Clock className="w-12 h-12 text-gray-600 mb-4" />
          <h3 className="text-lg font-mono font-bold text-gray-400">No reports found</h3>
          <p className="text-gray-500 font-mono text-sm max-w-sm text-center mt-2 px-6">
            Generate a report from the Scan Detail page to see it here.
          </p>
        </div>
      )}
    </div>
  );
}
