"use client";

import { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import {
  FlaskConical,
  CheckCircle,
  AlertTriangle,
  XCircle,
  HelpCircle,
  Database,
  Cpu,
  FileWarning,
  Activity,
  ChevronRight,
  Lightbulb,
  ThumbsUp,
  ThumbsDown,
  Minimize2,
  Compass,
  ArrowRightLeft,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AFMFinding {
  id: string;
  claim: string;
  classification:
    | "CONFIRMED"
    | "PARTIALLY CONFIRMED"
    | "ARTIFACT"
    | "FAILED"
    | "UNRESOLVED";
  baseline: string;
  afm: string;
  notes: string;
}

interface AFMArchitecture {
  totalParams: number;
  encoder: string;
  latent: string;
  decoder: string;
  keyMechanism: string;
  equivalentTo: string;
  baselineParams: number;
  paramMatch: boolean;
}

interface AFMData {
  version: string;
  experimentId: string;
  runDate: string;
  dataAvailable: boolean;
  dataWarning: string;
  architecture: AFMArchitecture;
  findings: AFMFinding[];
  summary: {
    CONFIRMED: number;
    "PARTIALLY CONFIRMED": number;
    ARTIFACT: number;
    FAILED: number;
    UNRESOLVED: number;
  };
  v02Status: {
    executed: boolean;
    plannedPhases: string[];
  };
  honestAssessment: {
    whatWorks: string[];
    whatDoesnt: string[];
    simplestEquivalent: string;
    recommendation: string;
  };
}

// ---------------------------------------------------------------------------
// Classification helpers
// ---------------------------------------------------------------------------

type Classification = AFMFinding["classification"];

const classificationConfig: Record<
  Classification,
  {
    badgeClass: string;
    icon: React.ReactNode;
  }
> = {
  CONFIRMED: {
    badgeClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    icon: <CheckCircle className="w-3.5 h-3.5" />,
  },
  "PARTIALLY CONFIRMED": {
    badgeClass: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    icon: <AlertTriangle className="w-3.5 h-3.5" />,
  },
  ARTIFACT: {
    badgeClass: "bg-orange-500/10 text-orange-400 border-orange-500/20",
    icon: <AlertTriangle className="w-3.5 h-3.5" />,
  },
  FAILED: {
    badgeClass: "bg-red-500/10 text-red-400 border-red-500/20",
    icon: <XCircle className="w-3.5 h-3.5" />,
  },
  UNRESOLVED: {
    badgeClass: "bg-gray-500/10 text-gray-400 border-gray-500/20",
    icon: <HelpCircle className="w-3.5 h-3.5" />,
  },
};

function ClassificationBadge({ type }: { type: Classification }) {
  const config = classificationConfig[type];
  return (
    <Badge
      variant="outline"
      className={`gap-1 text-xs font-medium ${config.badgeClass}`}
    >
      {config.icon}
      {type}
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-6 w-16" />
      </div>
      <Card className="border-emerald-500/20">
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-36" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function AFMResearchPanel() {
  const [data, setData] = useState<AFMData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      try {
        setLoading(true);
        setError(null);
        const res = await fetch("/api/afm");
        if (!res.ok) {
          throw new Error(`API returned ${res.status}: ${res.statusText}`);
        }
        const json: AFMData = await res.json();
        if (!cancelled) {
          setData(json);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to fetch AFM data"
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchData();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <LoadingSkeleton />;
  }

  if (error) {
    return (
      <Card className="border-red-500/20 bg-red-500/5">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400 flex-shrink-0">
              <XCircle className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg text-red-400">
                Failed to Load AFM Data
              </CardTitle>
              <CardDescription className="text-red-400/70">
                Could not fetch experiment findings from the API
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm hover:bg-red-500/20 transition-colors"
          >
            Retry
          </button>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  const totalFindings = Object.values(data.summary).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-6">
      {/* 1. Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
            <FlaskConical className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">
              AFM-Lite Research Panel
            </h2>
            <p className="text-sm text-muted-foreground">
              Experiment {data.experimentId} &middot; {data.runDate}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 sm:ml-auto">
          <Badge
            variant="outline"
            className="bg-teal-500/10 text-teal-400 border-teal-500/20 text-xs"
          >
            {data.version}
          </Badge>
          {!data.dataAvailable && (
            <Badge
              variant="outline"
              className="bg-yellow-500/10 text-yellow-400 border-yellow-500/20 text-xs gap-1"
            >
              <FileWarning className="w-3 h-3" />
              Data Unavailable
            </Badge>
          )}
        </div>
      </div>

      {/* Data warning banner */}
      {!data.dataAvailable && (
        <Card className="border-yellow-500/20 bg-yellow-500/5">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <FileWarning className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-yellow-200/80">{data.dataWarning}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 2. Architecture Card */}
      <Card className="border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg">Model Architecture</CardTitle>
              <CardDescription>
                AFM-Lite: 602,650 param Stiefel-VAE used in v0.1 experiments
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-3 rounded-lg bg-card/50 border border-border/20">
              <div className="flex items-center gap-2 mb-1">
                <Database className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                  Parameters
                </span>
              </div>
              <p className="text-lg font-bold text-foreground">
                {data.architecture.totalParams.toLocaleString()}
              </p>
              <p className="text-[10px] text-muted-foreground mt-1">
                {data.architecture.paramMatch
                  ? "Matched with baseline"
                  : "Unmatched with baseline"}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-card/50 border border-border/20">
              <div className="flex items-center gap-2 mb-1">
                <ArrowRightLeft className="w-3.5 h-3.5 text-teal-400" />
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                  Encoder → Latent → Decoder
                </span>
              </div>
              <p className="text-sm font-mono font-bold text-foreground">
                {data.architecture.encoder}
              </p>
              <p className="text-sm font-mono text-emerald-400">
                {data.architecture.latent}
              </p>
              <p className="text-sm font-mono font-bold text-foreground">
                {data.architecture.decoder}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-card/50 border border-border/20">
              <div className="flex items-center gap-2 mb-1">
                <FlaskConical className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                  Equivalent To
                </span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {data.architecture.equivalentTo}
              </p>
            </div>
          </div>
          <div className="mt-4 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
            <p className="text-xs text-muted-foreground">
              <span className="text-emerald-400 font-semibold">
                Key Mechanism:{" "}
              </span>
              {data.architecture.keyMechanism}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 3. Findings Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400 flex-shrink-0">
              <FlaskConical className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg">Experiment Findings</CardTitle>
              <CardDescription>
                {totalFindings} findings from AFM-Lite v0.1 &middot;
                classification based on empirical evidence
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">ID</TableHead>
                  <TableHead>Claim</TableHead>
                  <TableHead>Classification</TableHead>
                  <TableHead className="hidden md:table-cell">
                    Baseline
                  </TableHead>
                  <TableHead className="hidden md:table-cell">AFM</TableHead>
                  <TableHead className="hidden lg:table-cell">Notes</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.findings.map((finding) => (
                  <TableRow key={finding.id}>
                    <TableCell className="font-mono text-xs font-semibold text-muted-foreground">
                      {finding.id}
                    </TableCell>
                    <TableCell className="font-medium text-sm max-w-[200px] lg:max-w-none">
                      {finding.claim}
                    </TableCell>
                    <TableCell>
                      <ClassificationBadge type={finding.classification} />
                    </TableCell>
                    <TableCell className="hidden md:table-cell font-mono text-xs text-muted-foreground">
                      {finding.baseline}
                    </TableCell>
                    <TableCell className="hidden md:table-cell font-mono text-xs text-muted-foreground">
                      {finding.afm}
                    </TableCell>
                    <TableCell className="hidden lg:table-cell text-xs text-muted-foreground max-w-[260px]">
                      {finding.notes}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Mobile-only: show details for each finding */}
          <div className="md:hidden mt-4 space-y-3">
            {data.findings.map((finding) => (
              <div
                key={finding.id}
                className="p-3 rounded-lg bg-muted/20 border border-border/20 space-y-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs font-semibold text-muted-foreground">
                    {finding.id}
                  </span>
                  <ClassificationBadge type={finding.classification} />
                </div>
                <p className="text-sm font-medium">{finding.claim}</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-muted-foreground">Baseline: </span>
                    <span className="font-mono">{finding.baseline}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">AFM: </span>
                    <span className="font-mono">{finding.afm}</span>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">{finding.notes}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 4. Summary Card */}
      <Card className="border-emerald-500/20">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg">Classification Summary</CardTitle>
              <CardDescription>
                Distribution of {totalFindings} findings across classification
                categories
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {(
              [
                {
                  key: "CONFIRMED" as Classification,
                  count: data.summary.CONFIRMED,
                  config: classificationConfig.CONFIRMED,
                },
                {
                  key: "PARTIALLY CONFIRMED" as Classification,
                  count: data.summary["PARTIALLY CONFIRMED"],
                  config: classificationConfig["PARTIALLY CONFIRMED"],
                },
                {
                  key: "ARTIFACT" as Classification,
                  count: data.summary.ARTIFACT,
                  config: classificationConfig.ARTIFACT,
                },
                {
                  key: "FAILED" as Classification,
                  count: data.summary.FAILED,
                  config: classificationConfig.FAILED,
                },
                {
                  key: "UNRESOLVED" as Classification,
                  count: data.summary.UNRESOLVED,
                  config: classificationConfig.UNRESOLVED,
                },
              ] as const
            ).map(({ key, count, config }) => (
              <div
                key={key}
                className={`p-4 rounded-lg border ${config.badgeClass} flex flex-col items-center justify-center gap-1`}
              >
                <span className="text-3xl font-bold">{count}</span>
                <span className="text-[9px] uppercase tracking-wider font-medium flex items-center gap-1 text-center">
                  {config.icon}
                  {key}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 5. v0.2 Status Card */}
      <Card className="border-yellow-500/20 bg-gradient-to-r from-yellow-900/5 to-orange-900/5">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-yellow-500/10 border border-yellow-500/20 flex items-center justify-center text-yellow-400 flex-shrink-0">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg">v0.2 Validation Status</CardTitle>
              <CardDescription>
                Planned but not executed &mdash; 7 falsification phases remain
                unstarted
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 mb-4">
            <Badge
              variant="outline"
              className="bg-yellow-500/10 text-yellow-400 border-yellow-500/20 text-xs"
            >
              NOT EXECUTED
            </Badge>
            <span className="text-xs text-muted-foreground">
              {data.v02Status.plannedPhases.length} planned phases
            </span>
          </div>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {data.v02Status.plannedPhases.map((phase, i) => (
              <div
                key={i}
                className="flex items-start gap-3 p-3 rounded-lg bg-card/50 border border-border/20"
              >
                <div className="w-6 h-6 rounded-md bg-yellow-500/10 border border-yellow-500/20 flex items-center justify-center text-yellow-400 flex-shrink-0 text-xs font-mono">
                  {i + 1}
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                <p className="text-sm text-muted-foreground">{phase}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 6. Honest Assessment Card */}
      <Card className="border-border/30">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
              <Lightbulb className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg">Honest Assessment</CardTitle>
              <CardDescription>
                An evidence-based evaluation of what the AFM-Lite experiments
                actually demonstrated
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* What Works */}
            <div className="p-4 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
              <div className="flex items-center gap-2 mb-3">
                <ThumbsUp className="w-4 h-4 text-emerald-400" />
                <h4 className="text-sm font-semibold text-emerald-400">
                  What Works
                </h4>
              </div>
              <ul className="space-y-2">
                {data.honestAssessment.whatWorks.map((item, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-muted-foreground"
                  >
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500/60 flex-shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* What Doesn't */}
            <div className="p-4 rounded-lg bg-red-500/5 border border-red-500/20">
              <div className="flex items-center gap-2 mb-3">
                <ThumbsDown className="w-4 h-4 text-red-400" />
                <h4 className="text-sm font-semibold text-red-400">
                  What Doesn&apos;t
                </h4>
              </div>
              <ul className="space-y-2">
                {data.honestAssessment.whatDoesnt.map((item, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-muted-foreground"
                  >
                    <XCircle className="w-3.5 h-3.5 text-red-500/60 flex-shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Simplest Equivalent */}
            <div className="p-4 rounded-lg bg-teal-500/5 border border-teal-500/20">
              <div className="flex items-center gap-2 mb-3">
                <Minimize2 className="w-4 h-4 text-teal-400" />
                <h4 className="text-sm font-semibold text-teal-400">
                  Simplest Equivalent
                </h4>
              </div>
              <p className="text-sm text-muted-foreground">
                {data.honestAssessment.simplestEquivalent}
              </p>
            </div>

            {/* Recommendation */}
            <div className="p-4 rounded-lg bg-amber-500/5 border border-amber-500/20">
              <div className="flex items-center gap-2 mb-3">
                <Compass className="w-4 h-4 text-amber-400" />
                <h4 className="text-sm font-semibold text-amber-400">
                  Recommendation
                </h4>
              </div>
              <p className="text-sm text-muted-foreground">
                {data.honestAssessment.recommendation}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
