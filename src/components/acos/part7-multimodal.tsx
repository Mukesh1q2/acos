"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  MessageSquare,
  Mic,
  Eye,
  Video,
  Music,
  FileText,
  FileSpreadsheet,
  Presentation,
  Code,
  BookOpen,
  Brain,
  CheckCircle2,
  Clock,
  Rocket,
  Layers,
  Monitor,
} from "lucide-react";
import { SectionHeader } from "./section-header";

const capabilities = [
  { name: "Chat", icon: MessageSquare, status: "planned", priority: "high", desc: "Real-time conversational AI with memory" },
  { name: "Voice (STT/TTS)", icon: Mic, status: "planned", priority: "high", desc: "Speech-to-text and text-to-speech" },
  { name: "Vision (OCR)", icon: Eye, status: "planned", priority: "medium", desc: "Optical character recognition" },
  { name: "Vision (Understanding)", icon: Eye, status: "planned", priority: "high", desc: "Image understanding and description" },
  { name: "Vision (Generation)", icon: Eye, status: "future", priority: "low", desc: "AI image generation" },
  { name: "Video", icon: Video, status: "future", priority: "low", desc: "Video understanding and generation" },
  { name: "Audio", icon: Music, status: "planned", priority: "medium", desc: "Audio processing and generation" },
  { name: "Documents (PDF)", icon: FileText, status: "planned", priority: "high", desc: "PDF parsing, understanding, generation" },
  { name: "Documents (Word)", icon: FileText, status: "planned", priority: "medium", desc: "Word document processing" },
  { name: "Documents (Excel)", icon: FileSpreadsheet, status: "planned", priority: "medium", desc: "Spreadsheet analysis and generation" },
  { name: "Documents (PPT)", icon: Presentation, status: "future", priority: "low", desc: "Presentation creation and editing" },
  { name: "Coding Workspace", icon: Code, status: "planned", priority: "high", desc: "Full IDE with AI assistance" },
  { name: "Research Workspace", icon: BookOpen, status: "planned", priority: "high", desc: "Academic research and paper analysis" },
  { name: "Knowledge Workspace", icon: Brain, status: "planned", priority: "high", desc: "Knowledge management and visualization" },
];

const statusConfig: Record<string, { label: string; icon: React.ElementType; color: string; bgColor: string }> = {
  planned: { label: "Planned", icon: Clock, color: "text-teal-400", bgColor: "bg-teal-500/20 border-teal-500/30" },
  future: { label: "Future", icon: Rocket, color: "text-slate-400", bgColor: "bg-slate-500/20 border-slate-500/30" },
  active: { label: "Active", icon: CheckCircle2, color: "text-emerald-400", bgColor: "bg-emerald-500/20 border-emerald-500/30" },
};

const priorityConfig: Record<string, string> = {
  high: "bg-red-500/20 text-red-400 border-red-500/30",
  medium: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  low: "bg-slate-500/20 text-slate-400 border-slate-500/30",
};

const implementationStack = [
  {
    modality: "Vision",
    icon: <Eye className="w-5 h-5" />,
    color: "emerald",
    tech: "CLIP/SigLIP encoder",
    integration: "HBTA as \"super-tokens\" — image patches encoded as hierarchical token sequences processed by the attention tree",
  },
  {
    modality: "Voice",
    icon: <Mic className="w-5 h-5" />,
    color: "teal",
    tech: "Whisper (STT) + Tortoise/Spark (TTS)",
    integration: "Audio transcribed -> processed as text thread -> response synthesized back to speech. Low-latency pipeline for real-time chat.",
  },
  {
    modality: "Documents",
    icon: <FileText className="w-5 h-5" />,
    color: "green",
    tech: "pdfplumber + custom parsers",
    integration: "Multi-format document parsing with layout understanding. Extracted content stored in Episodic Memory for retrieval.",
  },
  {
    modality: "Coding",
    icon: <Code className="w-5 h-5" />,
    color: "cyan",
    tech: "Monaco Editor + AFM Code Thread",
    integration: "Dedicated Coding Thread with Panini constraints for syntax verification. DeepSeek-Coder for specialized code generation.",
  },
];

const stackColorMap: Record<string, { bg: string; border: string; text: string; badge: string }> = {
  emerald: { bg: "bg-emerald-500/10", border: "border-emerald-500/20", text: "text-emerald-400", badge: "bg-emerald-500/20 text-emerald-400" },
  teal: { bg: "bg-teal-500/10", border: "border-teal-500/20", text: "text-teal-400", badge: "bg-teal-500/20 text-teal-400" },
  green: { bg: "bg-green-500/10", border: "border-green-500/20", text: "text-green-400", badge: "bg-green-500/20 text-green-400" },
  cyan: { bg: "bg-cyan-500/10", border: "border-cyan-500/20", text: "text-cyan-400", badge: "bg-cyan-500/20 text-cyan-400" },
};

export function Part7Multimodal() {
  return (
    <div className="space-y-8">
      <SectionHeader
        sectionNumber={7}
        title="Multimodal Platform"
        subtitle="Full-stack vision for multi-modal intelligence"
        badge="FULL-STACK VISION"
        icon={<Monitor className="w-5 h-5" />}
        id="multimodal-platform"
      />

      {/* Capability Matrix */}
      <Card className="card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <CardTitle className="text-lg">Capability Matrix</CardTitle>
          <CardDescription>14 capabilities across text, voice, vision, and knowledge</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {capabilities.map((cap, i) => {
              const status = statusConfig[cap.status];
              const StatusIcon = status.icon;
              const CapIcon = cap.icon;
              return (
                <motion.div
                  key={cap.name}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className={`flex items-start gap-3 p-3 rounded-lg bg-muted/20 border border-border/20 ${
                    cap.priority === "high" ? "ring-1 ring-emerald-500/10" : ""
                  }`}
                >
                  <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
                    <CapIcon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold">{cap.name}</span>
                      <Badge
                        variant="outline"
                        className={`text-[9px] ${status.bgColor}`}
                      >
                        <StatusIcon className="w-2.5 h-2.5 mr-1" />
                        {status.label}
                      </Badge>
                      <Badge
                        variant="outline"
                        className={`text-[9px] ${priorityConfig[cap.priority]}`}
                      >
                        {cap.priority}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {cap.desc}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Planned", count: capabilities.filter((c) => c.status === "planned").length, color: "text-teal-400", bg: "bg-teal-500/10" },
          { label: "Future", count: capabilities.filter((c) => c.status === "future").length, color: "text-slate-400", bg: "bg-slate-500/10" },
          { label: "High Priority", count: capabilities.filter((c) => c.priority === "high").length, color: "text-emerald-400", bg: "bg-emerald-500/10" },
        ].map((stat) => (
          <Card key={stat.label} className="card-hover-lift border-border/30">
            <CardContent className="p-4 text-center">
              <div className={`text-3xl font-bold ${stat.color}`}>{stat.count}</div>
              <div className="text-xs text-muted-foreground mt-1">{stat.label}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Implementation Stack */}
      <Card className="card-hover-lift border-emerald-500/20 bg-gradient-to-r from-emerald-900/10 to-teal-900/10">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-emerald-400" />
            <CardTitle className="text-lg text-emerald-400">Implementation Stack</CardTitle>
          </div>
          <CardDescription className="text-emerald-400/70">Technical stack for each modality</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {implementationStack.map((stack, i) => {
              const colors = stackColorMap[stack.color];
              return (
                <motion.div
                  key={stack.modality}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="p-4 rounded-lg bg-card/50 border border-border/20"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <div className={`w-10 h-10 rounded-lg ${colors.bg} ${colors.border} border flex items-center justify-center ${colors.text}`}>
                      {stack.icon}
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-foreground">{stack.modality}</div>
                      <Badge variant="outline" className={`text-[10px] ${colors.badge} border ${colors.border}`}>
                        {stack.tech}
                      </Badge>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {stack.integration}
                  </p>
                </motion.div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
