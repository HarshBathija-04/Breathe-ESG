/*

Dashboard page - overview of ingestion status, emissions, and recent activity.
*/
import { useEffect, useState } from 'react';
import { dashboardApi, type DashboardStats } from '@/api/dashboard';
import {
  Activity,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Lock,
  BarChart3,
  Zap,
  Fuel,
  Plane,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

const STATUS_COLORS = {
  PENDING_REVIEW: '#f59e0b',
  FLAGGED: '#ef4444',
  APPROVED: '#22c55e',
  LOCKED: '#6366f1',
  REJECTED: '#6b7280',
};

const SCOPE_COLORS = {
  Scope1: '#f97316',
  Scope2: '#3b82f6',
  Scope3: '#10b981',
};

const CATEGORY_ICONS = {
  fuel: Fuel,
  electricity: Zap,
  travel: Plane,
};

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const data = await dashboardApi.getStats();
      setStats(data);
    } catch {
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-4 border-emerald-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="text-center py-12 text-gray-500">
        <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-gray-400" />
        <p>{error || 'No data available'}</p>
        <button onClick={loadStats} className="mt-4 text-emerald-600 hover:underline">
          Retry
        </button>
      </div>
    );
  }

  // Prepare chart data
  const statusChartData = [
    { name: 'Pending Review', value: stats.activities.pending_review, color: STATUS_COLORS.PENDING_REVIEW },
    { name: 'Flagged', value: stats.activities.flagged, color: STATUS_COLORS.FLAGGED },
    { name: 'Approved', value: stats.activities.approved, color: STATUS_COLORS.APPROVED },
    { name: 'Locked', value: stats.activities.locked, color: STATUS_COLORS.LOCKED },
    { name: 'Rejected', value: stats.activities.rejected, color: STATUS_COLORS.REJECTED },
  ].filter(d => d.value > 0);

  const scopeChartData = stats.emissions_by_scope.map((item) => ({
    name: item.scope,
    co2e: parseFloat(item.total_co2e?.toString() || '0'),
    count: item.count,
  }));

  const categoryData = stats.emissions_by_category.map((item) => ({
    name: item.category,
    co2e: parseFloat(item.total_co2e?.toString() || '0'),
    count: item.count,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">Overview of your ESG data ingestion pipeline</p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          title="Total Records"
          value={stats.activities.total}
          icon={Activity}
          color="bg-blue-50 text-blue-600"
        />
        <StatCard
          title="Pending Review"
          value={stats.activities.pending_review}
          icon={Clock}
          color="bg-amber-50 text-amber-600"
        />
        <StatCard
          title="Flagged"
          value={stats.activities.flagged}
          icon={AlertTriangle}
          color="bg-red-50 text-red-600"
        />
        <StatCard
          title="Approved"
          value={stats.activities.approved}
          icon={CheckCircle2}
          color="bg-green-50 text-green-600"
        />
        <StatCard
          title="Locked"
          value={stats.activities.locked}
          icon={Lock}
          color="bg-indigo-50 text-indigo-600"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-gray-500" />
              Records by Status
            </CardTitle>
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
                  dataKey="value"
                >
                  {statusChartData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Emissions by scope */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-gray-500" />
              CO₂e by Scope (kg)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={scopeChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="co2e">
                  {scopeChartData.map((entry, index) => (
                    <Cell key={index} fill={SCOPE_COLORS[entry.name as keyof typeof SCOPE_COLORS] || '#8884d8'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Emissions by category + Recent jobs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Emissions by Category</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {categoryData.map((item) => {
                const Icon = CATEGORY_ICONS[item.name as keyof typeof CATEGORY_ICONS] || Activity;
                return (
                  <div key={item.name} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center shadow-sm">
                        <Icon className="w-4 h-4 text-gray-600" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900 capitalize">{item.name}</p>
                        <p className="text-sm text-gray-500">{item.count} records</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-gray-900">{item.co2e.toFixed(0)}</p>
                      <p className="text-xs text-gray-500">kg CO₂e</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Ingestion Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stats.recent_jobs.map((job) => (
                <div key={job.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`
                      w-2 h-2 rounded-full shrink-0
                      ${job.status === 'COMPLETED' ? 'bg-green-500' : 
                        job.status === 'FAILED' ? 'bg-red-500' :
                        job.status === 'PARTIAL' ? 'bg-amber-500' :
                        'bg-blue-500'}
                    `} />
                    <div className="min-w-0">
                      <p className="font-medium text-gray-900 truncate">{job.original_filename}</p>
                      <p className="text-sm text-gray-500">
                        {job.source_type} · {job.parsed_rows} rows
                      </p>
                    </div>
                  </div>
                  <span className="text-xs text-gray-400 shrink-0 ml-3">
                    {new Date(job.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
              {stats.recent_jobs.length === 0 && (
                <p className="text-center text-gray-500 py-4">No ingestion jobs yet</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  color,
}: {
  title: string;
  value: number;
  icon: typeof Activity;
  color: string;
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <p className="text-sm text-gray-500">{title}</p>
            <p className="text-2xl font-bold text-gray-900">{value.toLocaleString()}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
