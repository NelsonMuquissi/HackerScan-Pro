'use client';

import { useState, useEffect, useRef } from 'react';
import { Bell, Check, X, Info, ShieldAlert, Zap, Loader2 } from 'lucide-react';
import { getNotifications, markNotificationAsRead, markAllNotificationsAsRead } from '@/lib/api';
import { cn } from '@/lib/utils';
import Link from 'next/link';

export function NotificationCenter() {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchNotifications = async () => {
    try {
      const data = await getNotifications();
      // Handle both plain arrays and paginated responses { results: [...] }
      let list: any[] = [];
      if (Array.isArray(data)) {
        list = data;
      } else if (data && typeof data === 'object' && 'results' in data) {
        list = (data as any).results;
      }
      setNotifications(list);
    } catch (e) {
      console.error('Failed to fetch notifications:', e);
    }
  };

  useEffect(() => {
    fetchNotifications();
    // Poll for new notifications every 60 seconds
    const interval = setInterval(fetchNotifications, 60000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const unreadCount = notifications.filter(n => !n.is_read).length;

  const handleMarkRead = async (id: string) => {
    try {
      await markNotificationAsRead(id);
      setNotifications(notifications.map(n => 
        n.id === id ? { ...n, is_read: true } : n
      ));
    } catch (e) {
      console.error(e);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsAsRead();
      setNotifications(notifications.map(n => ({ ...n, is_read: true })));
    } catch (e) {
      console.error(e);
    }
  };

  const getIcon = (type: string) => {
    switch (type) {
      case 'SCAN_COMPLETED': return <Check className="w-4 h-4 text-neon-green" />;
      case 'VULNERABILITY_FOUND': return <ShieldAlert className="w-4 h-4 text-red-500" />;
      case 'BILLING_ALERT': return <Zap className="w-4 h-4 text-yellow-400" />;
      default: return <Info className="w-4 h-4 text-blue-400" />;
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-400 hover:text-neon-green transition-colors focus:outline-none"
      >
        <Bell className={cn("w-5 h-5", isOpen && "text-neon-green")} />
        {unreadCount > 0 && (
          <span className="absolute top-1.5 right-1.5 w-4 h-4 bg-red-500 text-white text-[10px] font-bold flex items-center justify-center rounded-full border-2 border-card-bg">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-card-bg border border-card-border rounded-lg shadow-2xl z-50 overflow-hidden flex flex-col max-h-[480px]">
          <div className="p-4 border-b border-card-border flex items-center justify-between bg-card-bg/50 backdrop-blur-md">
            <h3 className="font-mono font-bold text-sm text-foreground">Notifications</h3>
            {unreadCount > 0 && (
              <button 
                onClick={handleMarkAllRead}
                className="text-[10px] font-mono text-neon-green hover:underline"
              >
                Clear all
              </button>
            )}
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {notifications.length > 0 ? (
              <div className="divide-y divide-card-border/50">
                {notifications.map((n) => (
                  <div 
                    key={n.id} 
                    className={cn(
                      "p-4 transition-colors relative group",
                      !n.is_read ? "bg-neon-green/5" : "bg-transparent opacity-70"
                    )}
                  >
                    <div className="flex gap-3">
                      <div className="mt-1 flex-shrink-0">
                        {getIcon(n.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={cn("text-xs font-mono mb-1", !n.is_read ? "text-foreground font-bold" : "text-gray-400")}>
                          {n.title}
                        </p>
                        <p className="text-[10px] font-mono text-gray-500 line-clamp-2">
                          {n.message}
                        </p>
                        <p className="text-[9px] font-mono text-gray-600 mt-2">
                          {new Date(n.created_at).toLocaleString()}
                        </p>
                      </div>
                      {!n.is_read && (
                        <button 
                          onClick={() => handleMarkRead(n.id)}
                          className="flex-shrink-0 opacity-0 group-hover:opacity-100 p-1 hover:bg-neon-green/10 rounded transition-all"
                          title="Mark as read"
                        >
                          <Check className="w-3.5 h-3.5 text-neon-green" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-12 flex flex-col items-center justify-center text-center px-6">
                <Bell className="w-8 h-8 text-gray-700 mb-3" />
                <p className="text-xs font-mono text-gray-500">Secure perimeter established. No alerts currently logged.</p>
              </div>
            )}
          </div>

          <div className="p-3 border-t border-card-border bg-card-bg/50 backdrop-blur-md text-center">
            <Link 
              href="/dashboard/settings" 
              className="text-[10px] font-mono text-gray-400 hover:text-foreground transition-colors"
              onClick={() => setIsOpen(false)}
            >
              Advanced Preferences & Channels
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
