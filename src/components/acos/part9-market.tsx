"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  Trophy,
  Lock,
  FileText,
  ArrowRight,
  Building2,
  User,
  Globe,
  Code,
  Server,
  TrendingUp,
} from "lucide-react";
import { SectionHeader } from "./section-header";

const competitors = [
  { company: "OpenAI", approach: "Black box, cloud-only", limitation: "No local deployment, no persistent learning", logo: "O" },
  { company: "Anthropic", approach: "Safety-focused, cloud-only", limitation: "No thread isolation, no continuous learning", logo: "A" },
  { company: "Google", approach: "Integrated, cloud-first", limitation: "No user-level memory persistence", logo: "G" },
  { company: "Microsoft", approach: "Enterprise, cloud", limitation: "Vendor lock-in, no cognitive OS", logo: "M" },
  { company: "Meta", approach: "Open source, static weights", limitation: "No built-in learning capability", logo: "Me" },
  { company: "xAI", approach: "Raw capability, cloud", limitation: "No memory architecture", logo: "X" },
];

const patents = [
  {
    id: 1,
    title: "Gated-Sum Broadcast with Orthogonal Thread Memory",
    description:
      "Method for maintaining zero-interference reasoning threads through Stiefel Manifold parameterization with gated-sum broadcast aggregation. Enables multiple parallel reasoning threads without cross-contamination.",
    novelty: "First architecture with mathematically proven thread isolation",
  },
  {
    id: 2,
    title: "Riemannian Compute Routing",
    description:
      "Dynamic computational routing based on Riemannian geometry of the Stiefel Manifold. Routes computation through geodesic paths to maintain orthogonality while minimizing computational overhead.",
    novelty: "Novel geometric approach to compute allocation",
  },
];

const acosAdvantages = [
  { feature: "Local Deployment", desc: "Runs entirely on user hardware, no cloud required" },
  { feature: "Persistent Memory", desc: "Remembers user data across sessions without cloud" },
  { feature: "Continuous Learning", desc: "Learns new skills without forgetting old ones" },
  { feature: "Thread Isolation", desc: "Proven zero-interference between reasoning threads" },
  { feature: "Neuro-Symbolic", desc: "Integrates logic constraints with neural reasoning" },
];

const enterpriseOpportunities = [
  { title: "On-premise Deployment", desc: "For regulated industries (healthcare, finance, legal)" },
  { title: "Custom Knowledge Fabric", desc: "Per-organization knowledge integration" },
  { title: "Continuous Learning", desc: "From internal data without data leaving the organization" },
  { title: "No Data Leaves", desc: "Complete data sovereignty and privacy compliance" },
];

const consumerOpportunities = [
  { title: "Personal AI Assistant", desc: "With persistent memory across sessions" },
  { title: "Local-first Privacy", desc: "Guarantee — your data never leaves your device" },
  { title: "Cross-session Knowledge", desc: "Retention — remembers your preferences and workflows" },
  { title: "Learn User Workflows", desc: "Over time — adapts to individual patterns" },
];

const openSourceStrategy = [
  { component: "Core OTM Layer", strategy: "Open source", reason: "Community building and adoption", icon: <Code className="w-4 h-4" /> },
  { component: "HBTA Implementation", strategy: "Open source", reason: "Research adoption and validation", icon: <Globe className="w-4 h-4" /> },
  { component: "ACOS Orchestration", strategy: "Open core", reason: "Basic features free, enterprise paid", icon: <Server className="w-4 h-4" /> },
  { component: "AFM Model Weights", strategy: "Commercial license", reason: "Revenue generation and competitive advantage", icon: <Lock className="w-4 h-4" /> },
];

export function Part9Market() {
  return (
    <div className="space-y-8">
      <SectionHeader
        sectionNumber={9}
        title="Market Strategy"
        subtitle="Dual-track go-to-market with open source + enterprise"
        badge="DUAL-TRACK GTM"
        icon={<TrendingUp className="w-5 h-5" />}
        id="market-strategy"
      />

      {/* Competitor Table */}
      <Card className="card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <CardTitle className="text-lg">Competitor Comparison</CardTitle>
          <CardDescription>How ACOS compares to existing AI platforms</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Company</TableHead>
                  <TableHead>Approach</TableHead>
                  <TableHead>Limitation</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {competitors.map((comp, i) => (
                  <motion.tr
                    key={comp.company}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="border-b border-border/20"
                  >
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-md bg-muted/30 flex items-center justify-center text-[10px] font-bold text-muted-foreground">
                          {comp.logo}
                        </div>
                        <span className="font-semibold text-sm">{comp.company}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {comp.approach}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-[10px] bg-red-500/10 text-red-400 border-red-500/20">
                        {comp.limitation}
                      </Badge>
                    </TableCell>
                  </motion.tr>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* ACOS Differentiation */}
      <Card className="card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-emerald-400" />
            <CardTitle className="text-lg text-emerald-400">ACOS Differentiation</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm font-semibold text-foreground mb-4">
            &quot;Deploy locally. It remembers your data. It does not forget old skills.&quot;
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {acosAdvantages.map((adv, i) => (
              <motion.div
                key={adv.feature}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.08 }}
                className="p-3 rounded-lg bg-card/50 border border-emerald-500/15"
              >
                <div className="text-sm font-semibold text-emerald-400">
                  {adv.feature}
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  {adv.desc}
                </div>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Patent Opportunities */}
      <Card className="card-hover-lift border-border/30">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Lock className="w-5 h-5 text-teal-400" />
            <CardTitle className="text-lg">Patent Opportunities</CardTitle>
          </div>
          <CardDescription className="text-teal-400/70">Key patentable innovations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {patents.map((patent, i) => (
              <motion.div
                key={patent.id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.15 }}
                className="p-4 rounded-lg bg-muted/20 border border-border/20"
              >
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400 font-bold text-xs flex-shrink-0">
                    #{patent.id}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-foreground">
                      {patent.title}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {patent.description}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <ArrowRight className="w-3 h-3 text-teal-400" />
                      <span className="text-[10px] font-mono text-teal-400">
                        Novelty: {patent.novelty}
                      </span>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Enterprise Opportunities */}
      <Card className="card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Building2 className="w-5 h-5 text-emerald-400" />
            <CardTitle className="text-lg text-emerald-400">Enterprise Opportunities</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {enterpriseOpportunities.map((item, i) => (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="p-3 rounded-lg bg-card/50 border border-emerald-500/15"
              >
                <div className="text-sm font-semibold text-emerald-400">{item.title}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{item.desc}</div>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Consumer Opportunities */}
      <Card className="card-hover-lift border-teal-500/20 bg-gradient-to-r from-teal-900/10 to-emerald-900/10">
        <CardHeader>
          <div className="flex items-center gap-2">
            <User className="w-5 h-5 text-teal-400" />
            <CardTitle className="text-lg text-teal-400">Consumer Opportunities</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {consumerOpportunities.map((item, i) => (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="p-3 rounded-lg bg-card/50 border border-teal-500/15"
              >
                <div className="text-sm font-semibold text-teal-400">{item.title}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{item.desc}</div>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Open Source Strategy */}
      <Card className="card-hover-lift border-border/30">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Globe className="w-5 h-5 text-green-400" />
            <CardTitle className="text-lg">Open Source Strategy</CardTitle>
          </div>
          <CardDescription className="text-green-400/70">Licensing approach for each component</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {openSourceStrategy.map((item, i) => (
              <motion.div
                key={item.component}
                initial={{ opacity: 0, x: -15 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="flex flex-col md:flex-row md:items-center gap-3 p-3 rounded-lg bg-muted/20 border border-border/20"
              >
                <div className="flex items-center gap-2 min-w-[180px]">
                  <div className="w-10 h-10 rounded-lg bg-green-500/10 border border-green-500/20 flex items-center justify-center text-green-400 flex-shrink-0">
                    {item.icon}
                  </div>
                  <span className="text-sm font-semibold">{item.component}</span>
                </div>
                <Badge
                  variant="outline"
                  className={`text-[10px] ${
                    item.strategy === "Open source"
                      ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                      : item.strategy === "Open core"
                        ? "bg-amber-500/20 text-amber-400 border-amber-500/30"
                        : "bg-red-500/10 text-red-400 border-red-500/20"
                  }`}
                >
                  {item.strategy}
                </Badge>
                <span className="text-xs text-muted-foreground flex-1">{item.reason}</span>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
