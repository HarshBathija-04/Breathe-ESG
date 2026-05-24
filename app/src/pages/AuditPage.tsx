/*

Audit Log page - immutable timeline of all system actions.
*/
import { useEffect, useState } from 'react';
import { auditApi, type AuditLogEntry } from '@/api/audit';
import {
  ShieldCheck,
  Upload,
  CheckCircle2,
  Edit3,
  Lock,
  AlertTriangle,
  Loader2,
  Search,
  ArrowDownUp,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

const ACTION_ICONS: Record<string, typeof Upload> = {
  INGEST: Upload,
  NORMALIZE: ArrowDownUp,
  REVIEW: CheckCircle2,
  EDIT: Edit3,
  LOCK: Lock,
  ANOMALY_FLAG: AlertTriangle,
  ANOMALY_CLEAR: CheckCircle2,
};

const ACTION_COLORS: Record<string, string> = {
  INGEST: 'bg-blue-100 text-blue-800',
  NORMALIZE: 'bg-purple-100 text-purple-800',
  REVIEW: 'bg-green-100 text-green-800',
  EDIT: 'bg-amber-100 text-amber-800',
  LOCK: 'bg-indigo-100 text-indigo-800',
  ANOMALY_FLAG: 'bg-red-100 text-red-800',
  ANOMALY_CLEAR: 'bg-gray-100 text-gray-800',
  STATUS_CHANGE: 'bg-orange-100 text-orange-800',
};

export function AuditPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [filtered, setFiltered] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [actionFilter, setActionFilter] = useState<string>('all');
  const [expandedLog, setExpandedLog] = useState<string | null>(null);

  useEffect(() => {
    loadLogs();
  }, []);

  useEffect(() => {
    filterLogs();
  }, [logs, search, actionFilter]);

  const loadLogs = async () => {
    try {
      const data = await auditApi.getTimeline();
      setLogs(data.results || []);
    } catch {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  const filterLogs = () => {
    let result = [...logs];

    if (actionFilter !== 'all') {
      result = result.filter(l => l.action === actionFilter);
    }

    if (search) {
      const q = search.toLowerCase();
      result = result.filter(l =>
        l.action.toLowerCase().includes(q) ||
        l.entity_type.toLowerCase().includes(q) ||
        l.actor_name.toLowerCase().includes(q) ||
        l.reason.toLowerCase().includes(q)
      );
    }

    setFiltered(result);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
        <p className="text-gray-500 mt-1">
          Immutable record of all system actions for compliance
        </p>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            placeholder="Search actions, users, entities..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white"
        >
          <option value="all">All Actions</option>
          <option value="INGEST">Ingest</option>
          <option value="NORMALIZE">Normalize</option>
          <option value="REVIEW">Review</option>
          <option value="EDIT">Edit</option>
          <option value="LOCK">Lock</option>
          <option value="ANOMALY_FLAG">Anomaly Flag</option>
        </select>
      </div>

      {/* Timeline */}
      <div className="space-y-3">
        {filtered.map((log) => {
          const Icon = ACTION_ICONS[log.action] || ShieldCheck;
          const colorClass = ACTION_COLORS[log.action] || 'bg-gray-100 text-gray-800';
          const isExpanded = expandedLog === log.id;

          return (
            <Card
              key={log.id}
              className="cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => setExpandedLog(isExpanded ? null : log.id)}
            >
              <CardContent className="p-4">
                <div className="flex items-start gap-4">
                  {/* Icon */}
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${colorClass}`}>
                    <Icon className="w-5 h-5" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="secondary" className={colorClass}>
                        {log.action}
                      </Badge>
                      <span className="text-sm text-gray-500">
                        {log.entity_type}:{log.entity_id.slice(0, 8)}...
                      </span>
                      <span className="text-xs text-gray-400 ml-auto">
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                    </div>

                    <div className="mt-1 flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900">
                        {log.actor_name || 'System'}
                      </span>
                      {log.reason && (
                        <span className="text-sm text-gray-500 truncate">
                          — {log.reason}
                        </span>
                      )}
                    </div>

                    {/* Expanded details */}
                    {isExpanded && (
                      <div className="mt-3 p-3 bg-gray-50 rounded-lg space-y-2">
                        {(Object.keys(log.before).length > 0 || Object.keys(log.after).length > 0) && (
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <p className="text-xs font-medium text-gray-500 mb-1">Before</p>
                              <pre className="text-xs text-gray-600 bg-white p-2 rounded border overflow-auto max-h-40">
                                {JSON.stringify(log.before, null, 2)}
                              </pre>
                            </div>
                            <div>
                              <p className="text-xs font-medium text-gray-500 mb-1">After</p>
                              <pre className="text-xs text-gray-600 bg-white p-2 rounded border overflow-auto max-h-40">
                                {JSON.stringify(log.after, null, 2)}
                              </pre>
                            </div>
                          </div>
                        )}
                        <div className="flex gap-4 text-xs text-gray-500">
                          <span>Actor: {log.actor_email || 'System'}</span>
                          <span>Entity: {log.entity_type}</span>
                          <span>ID: {log.entity_id}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}

        {filtered.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <ShieldCheck className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>No audit records found</p>
          </div>
        )}
      </div>
    </div>
  );
}
