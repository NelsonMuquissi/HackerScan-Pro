'use client';

import { useEffect, useState } from 'react';
import { adminListBountyPrograms, adminListBountySubmissions } from '@/lib/api';
import { Shield, Target, Award, Eye, Clock, CheckCircle, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

export default function BountyAdmin() {
  const [programs, setPrograms] = useState<any[]>([]);
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'programs' | 'submissions'>('programs');

  useEffect(() => {
    async function loadData() {
      try {
        const [pData, sData] = await Promise.all([
          adminListBountyPrograms(),
          adminListBountySubmissions()
        ]);
        setPrograms(pData);
        setSubmissions(sData);
      } catch (error) {
        toast.error("Failed to load bounty data");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) return <div className="text-neon-green animate-pulse font-mono">Synchronizing global bounty network...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-mono font-bold text-foreground">Global Bounty Hub</h1>
        <div className="flex gap-4">
          <button 
            onClick={() => setActiveTab('programs')}
            className={`font-mono text-sm px-4 py-2 border-b-2 transition-colors ${activeTab === 'programs' ? 'border-neon-green text-neon-green' : 'border-transparent text-gray-500 hover:text-white'}`}
          >
            Programs ({programs.length})
          </button>
          <button 
            onClick={() => setActiveTab('submissions')}
            className={`font-mono text-sm px-4 py-2 border-b-2 transition-colors ${activeTab === 'submissions' ? 'border-neon-green text-neon-green' : 'border-transparent text-gray-500 hover:text-white'}`}
          >
            Submissions ({submissions.length})
          </button>
        </div>
      </div>

      {activeTab === 'programs' ? (
        <div className="grid grid-cols-1 gap-4">
          {programs.map(prog => (
            <div key={prog.id} className="bg-card-bg border border-card-border p-6 rounded-lg flex justify-between items-center hover:border-neon-green transition-colors">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-background rounded-full border border-card-border">
                  <Target className="w-6 h-6 text-primary" />
                </div>
                <div>
                  <h3 className="text-lg font-mono font-bold">{prog.title}</h3>
                  <p className="text-xs text-gray-500 font-mono">Workspace: <span className="text-gray-300">{prog.workspace_name}</span></p>
                </div>
              </div>
              <div className="flex gap-8 text-center">
                <div>
                  <p className="text-[10px] text-gray-500 uppercase font-mono">Assets</p>
                  <p className="font-mono font-bold">{prog.scope?.length || 0}</p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500 uppercase font-mono">Max Payout</p>
                  <p className="font-mono font-bold text-emerald-500">${Number(Object.values(prog.rewards || {}).sort((a: any, b: any) => b - a)[0] || 0)}</p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500 uppercase font-mono">Status</p>
                  <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${prog.status === 'ACTIVE' ? 'bg-emerald-500/20 text-emerald-500' : 'bg-gray-500/20 text-gray-400'}`}>
                    {prog.status}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-card-bg border border-card-border rounded-lg overflow-hidden">
          <table className="w-full text-left font-mono text-sm">
            <thead className="bg-background border-b border-card-border text-gray-400">
              <tr>
                <th className="px-6 py-4 font-semibold uppercase">Submission</th>
                <th className="px-6 py-4 font-semibold uppercase">Researcher</th>
                <th className="px-6 py-4 font-semibold uppercase">Severity</th>
                <th className="px-6 py-4 font-semibold uppercase">Payout</th>
                <th className="px-6 py-4 font-semibold uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-card-border">
              {submissions.map((sub) => (
                <tr key={sub.id} className="hover:bg-white/5 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex flex-col">
                      <span className="text-foreground font-bold">{sub.title}</span>
                      <span className="text-xs text-gray-500">{sub.program_title}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-xs text-gray-300">{sub.researcher_email}</td>
                  <td className="px-6 py-4">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                      sub.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-500' :
                      sub.severity === 'HIGH' ? 'bg-orange-500/20 text-orange-500' :
                      'bg-blue-500/20 text-blue-500'
                    }`}>
                      {sub.severity}
                    </span>
                  </td>
                  <td className="px-6 py-4 font-bold text-emerald-500">${sub.payout_amount}</td>
                  <td className="px-6 py-4">
                    <span className="text-xs text-gray-400">{sub.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
