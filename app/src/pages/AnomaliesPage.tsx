/*

Anomalies page - view and manage detected data anomalies.
*/
import { useEffect, useState } from 'react';
import { anomalyApi, type AnomalyFlag } from '@/api/anomaly';
import { useAuth } from '@/context/AuthContext';
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Search,
  TrendingUp,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';

const TYPE_COLORS: Record<string, string> = {
  ELECTRICITY_SPIKE: '#ef4444',
  NEGATIVE_VALUE: '#f97316',
  ZERO_VALUE: '#f59e0b',
  MISSING_AIRPORT: '#3b82f6',
  DUPLICATE: '#8b5cf6',
  INVALID_UNIT: '#ec4899',
  OUT_OF_RANGE: '#10b981',
  MISSING_DISTANCE: '#06b6d4',
  DATE_INCONSISTENCY: '#6366f1',
};

const STATUS_CONFIG = {
  OPEN: { label: 'Open', className: 'bg-red-100 text-red-800' },
  RESOLVED: { label: 'Resolved', className: 'bg-green-100 text-green-800' },
  CONFIRMED: { label: 'Confirmed', className: 'bg-amber-100 text-amber-800' },
  IGNORED: { label: 'Ignored', className: 'bg-gray-100 text-gray-800' },
};

export function AnomaliesPage() {
  const { user } = useAuth();
  const [flags, setFlags] = useState<AnomalyFlag[]>([]);
  const [stats, setStats] = useState<{ by_status: Array<{ status: string; count: number }>; by_type: Array<{ anomaly_type: string; count: number }> } | null>(null);
  const [, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('OPEN');
  const [search, setSearch] = useState('');
  const [selectedFlag, setSelectedFlag] = useState<AnomalyFlag | null>(null);
  const [resolutionNote, setResolutionNote] = useState('');
  const [showResolveDialog, setShowResolveDialog] = useState(false);
  const [resolveStatus, setResolveStatus] = useState('RESOLVED');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [flagsData, statsData] = await Promise.all([
        anomalyApi.list({ status: statusFilter }),
        anomalyApi.getStats(),
      ]);
      setFlags(flagsData.results || []);
      setStats(statsData);
    } catch {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!selectedFlag) return;

    setActionLoading(true);
    try {
      await anomalyApi.resolve(selectedFlag.id, resolveStatus, resolutionNote);
      setFlags(prev => prev.filter(f => f.id !== selectedFlag.id));
      setShowResolveDialog(false);
      setResolutionNote('');
    } catch {
      // Handle error
    } finally {
      setActionLoading(false);
    }
  };

  const filteredFlags = flags.filter(f =>
    search === '' ||
    f.description.toLowerCase().includes(search.toLowerCase()) ||
    f.anomaly_type.toLowerCase().includes(search.toLowerCase())
  );

  // Chart data
  const typeChartData = (stats?.by_type || [])
    .filter(t => TYPE_COLORS[t.anomaly_type])
    .map(t => ({
      name: t.anomaly_type.replace(/_/g, ' '),
      count: t.count,
      fill: TYPE_COLORS[t.anomaly_type] || '#8884d8',
    }));

  const statusChartData = (stats?.by_status || []).map(s => ({
    name: s.status,
    count: s.count,
  }));

  const STATUS_CHART_COLORS = ['#ef4444', '#22c55e', '#f59e0b', '#6b7280'];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Anomalies</h1>
        <p className="text-gray-500 mt-1">
          Detected data quality issues flagged by the pipeline
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {stats?.by_status?.map((s) => (
          <Card
            key={s.status}
            className={`cursor-pointer transition-colors ${statusFilter === s.status ? 'ring-2 ring-emerald-500' : ''}`}
            onClick={() => setStatusFilter(s.status)}
          >
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <div>
                  <p className="text-2xl font-bold text-gray-900">{s.count}</p>
                  <p className="text-xs text-gray-500 capitalize">{s.status.toLowerCase()}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-gray-500" />
              Anomalies by Type
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={typeChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count">
                  {typeChartData.map((entry, index) => (
                    <Cell key={index} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Status Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={statusChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={4}
                  dataKey="count"
                >
                  {statusChartData.map((_, index) => (
                    <Cell key={index} fill={STATUS_CHART_COLORS[index % STATUS_CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            placeholder="Search anomalies..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Flags table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Type</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Description</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Category</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">CO₂e</th>
                  <th className="text-center px-4 py-3 font-medium text-gray-600">Confidence</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                  {statusFilter === 'OPEN' && <th className="text-left px-4 py-3 font-medium text-gray-600">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredFlags.map((flag) => {
                  const statusConfig = STATUS_CONFIG[flag.status as keyof typeof STATUS_CONFIG];

                  return (
                    <tr key={flag.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <span className="text-xs font-mono text-gray-600">
                          {flag.anomaly_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 max-w-xs">
                        <p className="text-gray-900 text-sm">{flag.description}</p>
                        {Object.keys(flag.details).length > 0 && (
                          <p className="text-xs text-gray-400 mt-1">
                            {JSON.stringify(flag.details).slice(0, 80)}...
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3 capitalize text-gray-700">
                        {flag.activity_details?.category}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-gray-700">
                        {flag.activity_details?.co2e ? parseFloat(flag.activity_details.co2e).toFixed(1) : '-'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-amber-500 rounded-full"
                              style={{ width: `${parseFloat(flag.confidence) * 100}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-500">
                            {(parseFloat(flag.confidence) * 100).toFixed(0)}%
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {statusConfig && (
                          <Badge variant="secondary" className={statusConfig.className}>
                            {statusConfig.label}
                          </Badge>
                        )}
                      </td>
                      {statusFilter === 'OPEN' && (
                        <td className="px-4 py-3">
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-green-600 hover:text-green-700 hover:bg-green-50"
                              onClick={() => {
                                setSelectedFlag(flag);
                                setResolveStatus('RESOLVED');
                                setShowResolveDialog(true);
                              }}
                              disabled={!user?.can_review}
                            >
                              <CheckCircle2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {filteredFlags.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              <CheckCircle2 className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p>No anomalies in this category</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Resolve Dialog */}
      <Dialog open={showResolveDialog} onOpenChange={setShowResolveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Resolve Anomaly</DialogTitle>
            <DialogDescription>
              {selectedFlag?.description}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700">Resolution</label>
              <select
                value={resolveStatus}
                onChange={(e) => setResolveStatus(e.target.value)}
                className="w-full mt-1 px-3 py-2 border border-gray-200 rounded-lg text-sm"
              >
                <option value="RESOLVED">Resolved (false positive)</option>
                <option value="CONFIRMED">Confirmed (real issue)</option>
                <option value="IGNORED">Ignored</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Note</label>
              <Textarea
                value={resolutionNote}
                onChange={(e) => setResolutionNote(e.target.value)}
                placeholder="Add a note about this resolution..."
                className="mt-1"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowResolveDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleResolve}
              disabled={actionLoading}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Resolve'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
