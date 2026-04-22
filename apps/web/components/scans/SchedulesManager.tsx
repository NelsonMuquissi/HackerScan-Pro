'use client';

import { useState, useEffect } from 'react';
import { 
  Calendar, 
  Clock, 
  Plus, 
  Trash2, 
  Zap, 
  Shield, 
  MoreVertical,
  Activity,
  CheckCircle2,
  XCircle,
  Settings2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { 
  listSchedules, 
  createSchedule, 
  updateSchedule, 
  deleteSchedule,
  listTargets
} from '@/lib/api';

export function SchedulesManager() {
  const [schedules, setSchedules] = useState<any[]>([]);
  const [targets, setTargets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [saving, setSaving] = useState(false);

  // New Schedule Form
  const [formData, setFormData] = useState({
    target: '',
    scan_type: 'quick',
    frequency: 'weekly'
  });

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [schedulesData, targetsData] = await Promise.all([
        listSchedules(),
        listTargets()
      ]);
      setSchedules(schedulesData);
      setTargets(targetsData);
    } catch (err) {
      console.error('Failed to load schedules:', err);
    } finally {
      setLoading(false);
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await createSchedule(formData);
      await loadData();
      setShowAddModal(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create schedule');
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (schedule: any) => {
    try {
      await updateSchedule(schedule.id, { is_active: !schedule.is_active });
      setSchedules(prev => prev.map(s => 
        s.id === schedule.id ? { ...s, is_active: !s.is_active } : s
      ));
    } catch (err) {
      console.error('Failed to toggle schedule:', err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this schedule?')) return;
    try {
      await deleteSchedule(id);
      setSchedules(prev => prev.filter(s => s.id !== id));
    } catch (err) {
      console.error('Failed to delete schedule:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[300px] space-y-4">
        <div className="w-10 h-10 border-2 border-neon-green border-t-transparent rounded-full animate-spin" />
        <p className="font-mono text-xs text-neon-green">CALIBRATING CRON JOBS...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Calendar className="w-5 h-5 text-neon-green" />
            AUTOMATED SCANNING
          </h2>
          <p className="text-sm text-gray-500 font-mono mt-1">RECURRING SECURITY AUDITS</p>
        </div>
        <button 
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-neon-green text-black font-bold rounded text-sm hover:bg-opacity-90 transition-all"
        >
          <Plus className="w-4 h-4" />
          NEW SCHEDULE
        </button>
      </div>

      <div className="grid gap-4">
        {schedules.length === 0 ? (
          <div className="bg-card-bg border border-dashed border-card-border rounded-xl p-12 text-center">
            <Clock className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <h3 className="text-gray-400 font-mono">NO ACTIVE SCHEDULES</h3>
            <p className="text-sm text-gray-600 mt-2">Automate your security posture with recurring scans.</p>
          </div>
        ) : (
          schedules.map((schedule) => (
            <motion.div 
              key={schedule.id}
              layout
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn(
                "bg-card-bg border rounded-xl p-5 flex items-center justify-between transition-colors",
                schedule.is_active ? "border-card-border" : "border-gray-800 opacity-60"
              )}
            >
              <div className="flex items-center gap-4">
                <div className={cn(
                  "w-12 h-12 rounded-lg flex items-center justify-center border",
                  schedule.is_active ? "border-neon-green/20 bg-neon-green-dim/20 text-neon-green" : "border-gray-700 bg-gray-800/20 text-gray-500"
                )}>
                  <Activity className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="font-bold text-foreground flex items-center gap-2">
                    {schedule.target_host}
                    <span className="text-[10px] bg-black px-2 py-0.5 rounded border border-card-border text-gray-400 font-mono uppercase">
                      {schedule.scan_type}
                    </span>
                  </h4>
                  <div className="flex items-center gap-4 mt-1 text-xs font-mono text-gray-500">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      EVERY {schedule.frequency.toUpperCase()}
                    </span>
                    <span className="flex items-center gap-1">
                      <Settings2 className="w-3 h-3" />
                      AUTO-PILOT
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => handleToggle(schedule)}
                  className={cn(
                    "px-3 py-1.5 rounded font-mono text-[10px] font-bold border transition-all",
                    schedule.is_active 
                      ? "border-neon-green text-neon-green bg-neon-green-dim" 
                      : "border-gray-600 text-gray-500 hover:border-neon-green hover:text-neon-green"
                  )}
                >
                  {schedule.is_active ? 'ENABLED' : 'DISABLED'}
                </button>
                <button 
                  onClick={() => handleDelete(schedule.id)}
                  className="p-2 text-gray-500 hover:text-neon-red transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          ))
        )}
      </div>

      {/* Add Modal */}
      <AnimatePresence>
        {showAddModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-card-bg border border-card-border rounded-2xl p-8 max-w-md w-full shadow-2xl"
            >
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold flex items-center gap-2">
                  <Zap className="w-5 h-5 text-neon-green" />
                  INITIATE AUTO-SCAN
                </h3>
                <button onClick={() => setShowAddModal(false)} className="text-gray-500 hover:text-white">
                  <XCircle className="w-6 h-6" />
                </button>
              </div>

              <form onSubmit={handleCreate} className="space-y-6">
                <div className="space-y-2">
                  <label className="text-xs font-bold text-gray-500 uppercase font-mono">Select Target</label>
                  <select 
                    required
                    value={formData.target}
                    onChange={(e) => setFormData(prev => ({ ...prev, target: e.target.value }))}
                    className="w-full bg-black border border-card-border rounded-lg p-3 text-sm focus:border-neon-green outline-none transition-colors"
                  >
                    <option value="">Choose a host...</option>
                    {targets.map(t => (
                      <option key={t.id} value={t.id}>{t.host} ({t.name})</option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-gray-500 uppercase font-mono">Scan Type</label>
                    <select 
                      value={formData.scan_type}
                      onChange={(e) => setFormData(prev => ({ ...prev, scan_type: e.target.value }))}
                      className="w-full bg-black border border-card-border rounded-lg p-3 text-sm focus:border-neon-green outline-none"
                    >
                      <option value="quick">Quick</option>
                      <option value="full">Full</option>
                      <option value="vuln">Vuln</option>
                      <option value="recon">Recon</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-gray-500 uppercase font-mono">Frequency</label>
                    <select 
                      value={formData.frequency}
                      onChange={(e) => setFormData(prev => ({ ...prev, frequency: e.target.value }))}
                      className="w-full bg-black border border-card-border rounded-lg p-3 text-sm focus:border-neon-green outline-none"
                    >
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                    </select>
                  </div>
                </div>

                <div className="bg-neon-green/5 border border-neon-green/10 p-4 rounded-lg">
                  <p className="text-[11px] text-gray-400 font-mono leading-relaxed">
                    <CheckCircle2 className="w-3 h-3 text-neon-green inline mr-2" />
                    Automatic threat isolation enabled. Reports will be delivered to your primary workspace notification channel.
                  </p>
                </div>

                <button 
                  type="submit"
                  disabled={saving || !formData.target}
                  className="w-full py-4 bg-neon-green text-black font-bold rounded-xl hover:bg-opacity-90 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {saving ? <Activity className="w-5 h-5 animate-spin" /> : <Shield className="w-5 h-5" />}
                  COMMIT SCHEDULE
                </button>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
