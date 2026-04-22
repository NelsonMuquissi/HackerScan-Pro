'use client';

import React from 'react';
import { 
  Shield, 
  Search, 
  Globe, 
  Code, 
  Server, 
  Cpu, 
  Hash,
  ExternalLink,
  Terminal,
  Activity
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface FindingEvidenceProps {
  finding: any;
}

export function FindingEvidence({ finding }: FindingEvidenceProps) {
  const { plugin_slug, evidence } = finding;

  if (!evidence) return <div className="text-gray-500 italic text-sm">No evidence provided for this finding.</div>;

  // 1. Port Scan / OS Fingerprint
  if (plugin_slug === 'port_scan') {
    if (evidence.os) {
      return (
        <div className="bg-[#0a0a0a] border border-neon-green/20 rounded p-4 flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-neon-green-dim flex items-center justify-center border border-neon-green/30">
            <Cpu className="w-6 h-6 text-neon-green" />
          </div>
          <div>
            <div className="text-[10px] text-gray-500 uppercase font-bold tracking-tighter">Operating System Identified</div>
            <div className="text-xl font-bold text-foreground">{evidence.os}</div>
            <div className="text-xs text-neon-green/60 font-mono mt-1">Accuracy: {evidence.accuracy}% Confidence</div>
          </div>
        </div>
      );
    }
    
    if (evidence.port) {
      return (
        <div className="overflow-hidden border border-card-border rounded">
          <table className="w-full text-sm text-left font-mono">
            <thead className="bg-[#111] text-gray-400 text-[10px] uppercase tracking-wider">
              <tr>
                <th className="px-4 py-2">Port</th>
                <th className="px-4 py-2">Proto</th>
                <th className="px-4 py-2">Service</th>
                <th className="px-4 py-2">Product/Version</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-card-border">
              <tr className="hover:bg-[#111] transition-colors">
                <td className="px-4 py-3 font-bold text-neon-green">{evidence.port}</td>
                <td className="px-4 py-3 text-gray-400">{evidence.protocol}</td>
                <td className="px-4 py-3 text-foreground">{evidence.service}</td>
                <td className="px-4 py-3 text-gray-400">
                  {evidence.product} {evidence.version || <span className="italic text-gray-600">v?</span>}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      );
    }
  }

  // 2. JS Secret Scraper
  if (plugin_slug === 'js_secrets') {
    return (
      <div className="space-y-4">
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-[#111] border border-card-border p-3 rounded flex items-center gap-3">
            <Globe className="w-4 h-4 text-blue-400" />
            <div>
              <div className="text-[10px] text-gray-500 uppercase font-bold">Source URL</div>
              <a href={evidence.source} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-400 hover:underline flex items-center gap-1">
                {evidence.source} <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
          <div className="bg-[#111] border border-card-border p-3 rounded flex items-center gap-3">
            <Hash className="w-4 h-4 text-neon-yellow" />
            <div>
              <div className="text-[10px] text-gray-500 uppercase font-bold">Match Snippet</div>
              <div className="text-xs font-mono text-neon-yellow">{evidence.match_snippet}</div>
            </div>
          </div>
        </div>
        
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-[10px] text-gray-500 uppercase font-bold px-1">
            <Code className="w-3 h-3" /> Source Code Context
          </div>
          <div className="relative group">
            <div className="absolute inset-0 bg-neon-green/5 blur-xl group-hover:bg-neon-green/10 transition-all pointer-events-none" />
            <pre className="relative bg-black/80 border border-card-border p-4 rounded text-xs font-mono text-gray-300 overflow-x-auto whitespace-pre-wrap leading-relaxed">
              {evidence.context}
            </pre>
          </div>
        </div>
      </div>
    );
  }

  // 3. DNS Audit
  if (plugin_slug === 'dns_audit') {
    if (evidence.ns) {
      return (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-neon-red px-2 py-1 bg-neon-red-dim border border-neon-red/20 rounded-md w-fit">
            <AlertTriangle className="w-3 h-3" />
            <span className="text-[10px] font-bold uppercase">AXFR Vulnerability Detected</span>
          </div>
          <div className="bg-[#111] border border-card-border p-4 rounded-lg">
            <div className="text-xs text-gray-500 mb-2">Vulnerable Name Server: <span className="text-foreground font-bold">{evidence.ns}</span></div>
            <div className="flex items-center gap-2 text-[10px] text-gray-500 uppercase font-bold mb-2">
              <Terminal className="w-3 h-3" /> Raw Transfer Data
            </div>
            <pre className="bg-black p-3 rounded border border-card-border text-[10px] font-mono text-gray-400 h-40 overflow-y-auto custom-scrollbar">
              {evidence.output_preview}
            </pre>
          </div>
        </div>
      );
    }
    
    if (evidence.record) {
      return (
        <div className="bg-[#111] border border-card-border p-4 rounded-lg flex items-start gap-4">
          <div className="mt-1 p-2 bg-blue-500/10 rounded-full border border-blue-500/20">
            <Search className="w-4 h-4 text-blue-500" />
          </div>
          <div className="flex-1">
            <div className="text-[10px] text-gray-500 uppercase font-bold mb-1">Detected DNS Record</div>
            <div className="font-mono text-sm text-foreground break-all">{evidence.record}</div>
          </div>
        </div>
      );
    }
  }

  // 4. SQLMap / XSS (XSStrike) - Terminal style
  if (plugin_slug === 'sqlmap_scan' || plugin_slug === 'xss_scan') {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2 text-[10px] text-gray-500 uppercase font-bold">
            <Terminal className="w-3 h-3" /> Tool Output Log
          </div>
          <span className="text-[10px] text-neon-green font-mono animate-pulse">LIVE_EVIDENCE_RECONSTRUCTED</span>
        </div>
        <div className="relative group">
          <div className="absolute -inset-1 bg-gradient-to-r from-neon-green/20 to-blue-500/20 rounded-lg blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200"></div>
          <pre className="relative bg-black border border-card-border p-4 rounded text-[11px] font-mono text-green-400/90 h-64 overflow-y-auto custom-scrollbar leading-tight shadow-2xl">
            <div className="text-gray-500 mb-2"># {plugin_slug} --output-dir /tmp/hs_scan --target {finding.title}</div>
            {typeof evidence === 'string' ? evidence : JSON.stringify(evidence, null, 2)}
          </pre>
        </div>
      </div>
    );
  }

  // Fallback for unknown evidence structure
  return (
    <pre className="bg-black/50 border border-card-border p-4 rounded text-xs font-mono text-gray-400 whitespace-pre-wrap overflow-x-auto">
      {typeof evidence === 'object'
        ? JSON.stringify(evidence, null, 2)
        : String(evidence ?? 'No Evidence Provided')}
    </pre>
  );
}

// Sub-components/Icons for better UX
function AlertTriangle(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
      <path d="M12 9v4" />
      <path d="M12 17h.01" />
    </svg>
  );
}
