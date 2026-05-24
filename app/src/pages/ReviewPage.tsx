/*

Review Queue page - analysts can review, approve, or reject normalized activities.
*/
import { useEffect, useState } from 'react';
import { reviewApi, type NormalizedActivity, type ReviewDecision } from '@/api/review';
import { useAuth } from '@/context/AuthContext';
import {
  ClipboardCheck,
  CheckCircle2,
  XCircle,
  Search,
  Eye,
  Loader2,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
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

const STATUS_BADGES = {
  PENDING_REVIEW: { label: 'Pending', className: 'bg-amber-100 text-amber-800 hover:bg-amber-100' },
  FLAGGED: { label: 'Flagged', className: 'bg-red-100 text-red-800 hover:bg-red-100' },
  APPROVED: { label: 'Approved', className: 'bg-green-100 text-green-800 hover:bg-green-100' },
  REJECTED: { label: 'Rejected', className: 'bg-gray-100 text-gray-800 hover:bg-gray-100' },
  LOCKED: { label: 'Locked', className: 'bg-indigo-100 text-indigo-800 hover:bg-indigo-100' },
};

const SCOPE_COLORS = {
  Scope1: 'bg-orange-100 text-orange-800',
  Scope2: 'bg-blue-100 text-blue-800',
  Scope3: 'bg-green-100 text-green-800',
};

export function ReviewPage() {
  const { user } = useAuth();
  const [activities, setActivities] = useState<NormalizedActivity[]>([]);
  const [filtered, setFiltered] = useState<NormalizedActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedActivity, setSelectedActivity] = useState<NormalizedActivity | null>(null);
  const [decisionReason, setDecisionReason] = useState('');
  const [showDecisionDialog, setShowDecisionDialog] = useState(false);
  const [decisionType, setDecisionType] = useState<'APPROVE' | 'REJECT' | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [history, setHistory] = useState<ReviewDecision[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    loadActivities();
  }, []);

  useEffect(() => {
    filterActivities();
  }, [activities, search, statusFilter]);

  const loadActivities = async () => {
    try {
      const data = await reviewApi.getPending();
      setActivities(data);
    } catch {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  const filterActivities = () => {
    let result = [...activities];

    if (statusFilter !== 'all') {
      result = result.filter(a => a.status === statusFilter);
    }

    if (search) {
      const q = search.toLowerCase();
      result = result.filter(a =>
        a.facility_code.toLowerCase().includes(q) ||
        a.vendor.toLowerCase().includes(q) ||
        a.sub_category.toLowerCase().includes(q) ||
        a.category.toLowerCase().includes(q)
      );
    }

    setFiltered(result);
  };

  const handleDecision = async () => {
    if (!selectedActivity || !decisionType) return;

    setActionLoading(selectedActivity.id);
    try {
      await reviewApi.submitDecision(
        selectedActivity.id,
        decisionType,
        decisionReason
      );
      // Remove from list or update status
      setActivities(prev =>
        prev.filter(a => a.id !== selectedActivity.id)
      );
      setShowDecisionDialog(false);
      setDecisionReason('');
    } catch {
      // Handle error
    } finally {
      setActionLoading(null);
    }
  };

  const openDecision = (activity: NormalizedActivity, type: 'APPROVE' | 'REJECT') => {
    setSelectedActivity(activity);
    setDecisionType(type);
    setShowDecisionDialog(true);
  };

  const viewHistory = async (activity: NormalizedActivity) => {
    setSelectedActivity(activity);
    try {
      const data = await reviewApi.getHistory(activity.id);
      setHistory(data.decisions || []);
      setShowHistory(true);
    } catch {
      setHistory([]);
    }
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Review Queue</h1>
          <p className="text-gray-500 mt-1">
            Review and approve normalized activities before audit lock
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="bg-amber-100 text-amber-800">
            {activities.filter(a => a.status === 'PENDING_REVIEW').length} pending
          </Badge>
          <Badge variant="secondary" className="bg-red-100 text-red-800">
            {activities.filter(a => a.status === 'FLAGGED').length} flagged
          </Badge>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            placeholder="Search by facility, vendor, category..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white"
        >
          <option value="all">All Status</option>
          <option value="PENDING_REVIEW">Pending Review</option>
          <option value="FLAGGED">Flagged</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
        </select>
      </div>

      {/* Activity table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Source</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Scope</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Category</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">Value</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">CO₂e (kg)</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Period</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((activity) => {
                  const badge = STATUS_BADGES[activity.status as keyof typeof STATUS_BADGES];
                  const scopeColor = SCOPE_COLORS[activity.scope as keyof typeof SCOPE_COLORS];

                  return (
                    <tr key={activity.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <span className="font-medium text-gray-900">{activity.source_type}</span>
                        {activity.edited_flag && (
                          <span className="ml-1 text-xs text-amber-600">(edited)</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="secondary" className={scopeColor}>
                          {activity.scope}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 capitalize text-gray-700">
                        {activity.category}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-gray-700">
                        {parseFloat(activity.activity_value).toLocaleString(undefined, { maximumFractionDigits: 2 })}
                        <span className="text-gray-400 ml-1">{activity.normalized_unit}</span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-gray-700">
                        {parseFloat(activity.co2e).toLocaleString(undefined, { maximumFractionDigits: 1 })}
                      </td>
                      <td className="px-4 py-3 text-gray-600">
                        {new Date(activity.period_start).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })}
                      </td>
                      <td className="px-4 py-3">
                        {badge && (
                          <Badge variant="secondary" className={badge.className}>
                            {badge.label}
                          </Badge>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          {activity.status !== 'APPROVED' && activity.status !== 'LOCKED' && (
                            <>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-green-600 hover:text-green-700 hover:bg-green-50"
                                onClick={() => openDecision(activity, 'APPROVE')}
                                disabled={actionLoading === activity.id || !user?.can_approve}
                              >
                                <CheckCircle2 className="w-4 h-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                onClick={() => openDecision(activity, 'REJECT')}
                                disabled={actionLoading === activity.id}
                              >
                                <XCircle className="w-4 h-4" />
                              </Button>
                            </>
                          )}
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-gray-500 hover:text-gray-700"
                            onClick={() => viewHistory(activity)}
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {filtered.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              <ClipboardCheck className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p>No activities to review</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Decision Dialog */}
      <Dialog open={showDecisionDialog} onOpenChange={setShowDecisionDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {decisionType === 'APPROVE' ? 'Approve Activity' : 'Reject Activity'}
            </DialogTitle>
            <DialogDescription>
              {selectedActivity && (
                <span>
                  {selectedActivity.category} · {selectedActivity.sub_category} ·{' '}
                  {parseFloat(selectedActivity.co2e).toFixed(1)} kg CO₂e
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700">Reason (optional)</label>
              <Textarea
                value={decisionReason}
                onChange={(e) => setDecisionReason(e.target.value)}
                placeholder="Add a note about this decision..."
                className="mt-1"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDecisionDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleDecision}
              disabled={!!actionLoading}
              className={decisionType === 'APPROVE' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}
            >
              {actionLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : decisionType === 'APPROVE' ? (
                'Approve'
              ) : (
                'Reject'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* History Dialog */}
      <Dialog open={showHistory} onOpenChange={setShowHistory}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Review History</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            {history.length === 0 && (
              <p className="text-gray-500 text-center py-4">No decisions recorded yet</p>
            )}
            {history.map((decision) => (
              <div key={decision.id} className="p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between">
                  <Badge
                    variant="secondary"
                    className={decision.decision === 'APPROVE' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}
                  >
                    {decision.decision}
                  </Badge>
                  <span className="text-xs text-gray-500">
                    {decision.reviewed_by_name} · {new Date(decision.created_at).toLocaleDateString()}
                  </span>
                </div>
                {decision.reason && (
                  <p className="text-sm text-gray-600 mt-2">{decision.reason}</p>
                )}
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
