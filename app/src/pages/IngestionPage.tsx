/*

Ingestion page - upload files for SAP, Utility, and Travel data sources.
*/
import { useState, useRef } from 'react';
import { ingestionApi, type IngestionJob } from '@/api/ingestion';
import {
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Database,
  Zap,
  Plane,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface UploadZoneProps {
  title: string;
  description: string;
  icon: typeof Database;
  acceptedTypes: string;
  onUpload: (file: File) => Promise<void>;
  color: string;
}

function UploadZone({ title, description, icon: Icon, acceptedTypes, onUpload, color }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) onUpload(file);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
  };

  return (
    <Card className={`transition-all ${isDragging ? 'ring-2 ring-emerald-500 border-emerald-500' : ''}`}>
      <CardContent className="p-6">
        <div
          className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-gray-400 transition-colors"
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <div className={`w-12 h-12 ${color} rounded-xl flex items-center justify-center mx-auto mb-4`}>
            <Icon className="w-6 h-6 text-white" />
          </div>
          <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
          <p className="text-sm text-gray-500 mb-4">{description}</p>
          <p className="text-xs text-gray-400">Drop CSV here or click to browse</p>
          <input
            ref={fileInputRef}
            type="file"
            accept={acceptedTypes}
            className="hidden"
            onChange={handleFileSelect}
          />
        </div>
      </CardContent>
    </Card>
  );
}

interface JobResultProps {
  job: IngestionJob;
}

function JobResult({ job }: JobResultProps) {
  const [expanded, setExpanded] = useState(false);

  const isSuccess = job.status === 'COMPLETED' || job.status === 'PARTIAL';
  const isFailed = job.status === 'FAILED';

  return (
    <Card className={`${isFailed ? 'border-red-300' : isSuccess ? 'border-green-300' : ''}`}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {isFailed ? (
            <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
          ) : (
            <CheckCircle2 className="w-5 h-5 text-green-500 shrink-0 mt-0.5" />
          )}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <p className="font-medium text-gray-900 truncate">{job.original_filename}</p>
              <span className={`text-xs px-2 py-1 rounded-full shrink-0 ml-2 ${
                isFailed ? 'bg-red-100 text-red-700' :
                job.status === 'PARTIAL' ? 'bg-amber-100 text-amber-700' :
                'bg-green-100 text-green-700'
              }`}>
                {job.status}
              </span>
            </div>
            <p className="text-sm text-gray-500">
              {job.source_type} · {job.parsed_rows} parsed · {job.normalized_rows} normalized
              {job.flagged_rows > 0 && ` · ${job.flagged_rows} flagged`}
            </p>

            {/* Progress bars */}
            <div className="mt-3 space-y-2">
              {job.total_rows > 0 && (
                <div>
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>Parsed</span>
                    <span>{job.parsed_rows}/{job.total_rows}</span>
                  </div>
                  <Progress
                    value={job.total_rows > 0 ? (job.parsed_rows / job.total_rows) * 100 : 0}
                    className="h-2"
                  />
                </div>
              )}
              {job.parsed_rows > 0 && (
                <div>
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>Normalized</span>
                    <span>{job.normalized_rows}/{job.parsed_rows}</span>
                  </div>
                  <Progress
                    value={job.parsed_rows > 0 ? (job.normalized_rows / job.parsed_rows) * 100 : 0}
                    className="h-2"
                  />
                </div>
              )}
            </div>

            {/* Logs */}
            {job.logs.length > 0 && (
              <div className="mt-3">
                <button
                  onClick={() => setExpanded(!expanded)}
                  className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
                >
                  {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                  {expanded ? 'Hide logs' : 'Show logs'}
                </button>
                {expanded && (
                  <div className="mt-2 max-h-40 overflow-y-auto bg-gray-50 rounded-lg p-3 text-xs font-mono space-y-1">
                    {job.logs.map((log, idx) => (
                      <div key={idx} className={`${
                        log.level === 'ERROR' ? 'text-red-600' :
                        log.level === 'WARN' ? 'text-amber-600' :
                        'text-gray-600'
                      }`}>
                        <span className="text-gray-400">[{log.level}]</span> {log.message}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function IngestionPage() {
  const [uploading, setUploading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [jobs, setJobs] = useState<IngestionJob[]>([]);

  const handleUpload = async (type: 'sap' | 'utility' | 'travel', file: File) => {
    setUploading(type);
    setError(null);

    try {
      let job: IngestionJob;
      switch (type) {
        case 'sap':
          job = await ingestionApi.uploadSAP(file);
          break;
        case 'utility':
          job = await ingestionApi.uploadUtility(file);
          break;
        case 'travel':
          job = await ingestionApi.uploadTravel(file);
          break;
      }
      setJobs(prev => [job, ...prev]);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setError(message);
    } finally {
      setUploading(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Data Ingestion</h1>
        <p className="text-gray-500 mt-1">Upload data from SAP, utility portals, and travel platforms</p>
      </div>

      {/* Error */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="w-4 h-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Upload zones */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <UploadZone
          title="SAP Fuel & Procurement"
          description="Upload SAP CSV export with fuel and material data"
          icon={Database}
          acceptedTypes=".csv"
          color="bg-amber-600"
          onUpload={(file) => handleUpload('sap', file)}
        />
        <UploadZone
          title="Utility Electricity"
          description="Upload utility portal CSV with meter readings"
          icon={Zap}
          acceptedTypes=".csv"
          color="bg-blue-600"
          onUpload={(file) => handleUpload('utility', file)}
        />
        <UploadZone
          title="Corporate Travel"
          description="Upload travel platform CSV with flights, hotels, ground"
          icon={Plane}
          acceptedTypes=".csv"
          color="bg-purple-600"
          onUpload={(file) => handleUpload('travel', file)}
        />
      </div>

      {/* Uploading indicator */}
      {uploading && (
        <div className="flex items-center gap-3 p-4 bg-blue-50 rounded-lg">
          <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
          <p className="text-sm text-blue-700">
            Processing {uploading} upload... This may take a moment.
          </p>
        </div>
      )}

      {/* Results */}
      {jobs.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">Recent Uploads</h2>
          <div className="space-y-3">
            {jobs.map((job) => (
              <JobResult key={job.id} job={job} />
            ))}
          </div>
        </div>
      )}

      {/* Sample data info */}
      <Card className="bg-gray-50 border-dashed">
        <CardHeader>
          <CardTitle className="text-sm text-gray-600">Sample Data</CardTitle>
          <CardDescription>
            The following sample files are included in the repository for testing:
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-gray-600">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-gray-400" />
            <span>sap_fuel.csv - SAP export (English headers, 54 rows with inconsistencies)</span>
          </div>
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-gray-400" />
            <span>sap_fuel_german.csv - SAP export (German headers, semicolon-delimited)</span>
          </div>
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-gray-400" />
            <span>utility_electricity.csv - Utility portal export (41 rows)</span>
          </div>
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-gray-400" />
            <span>travel_data.csv - Travel platform export (63 rows)</span>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Each file contains intentional inconsistencies (negative values, duplicates, 
            invalid units, missing data) to test the anomaly detection pipeline.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
