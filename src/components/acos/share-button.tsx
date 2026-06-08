"use client";

import { useCallback } from "react";
import { motion } from "framer-motion";
import { Link2 } from "lucide-react";
import { toast } from "sonner";

interface ShareButtonProps {
  sectionId: string;
}

export function ShareButton({ sectionId }: ShareButtonProps) {
  const handleShare = useCallback(() => {
    const url = `${window.location.origin}${window.location.pathname}#${sectionId}`;
    navigator.clipboard.writeText(url).then(
      () => {
        toast.success("Section link copied!", {
          description: `Link to section "${sectionId}" is ready to share.`,
          duration: 3000,
        });
      },
      () => {
        // Fallback: select the URL in the address bar
        window.location.hash = sectionId;
        toast.success("Section link ready!", {
          description: "URL updated in the address bar — copy it to share.",
          duration: 3000,
        });
      }
    );
  }, [sectionId]);

  return (
    <motion.button
      onClick={handleShare}
      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium
        transition-all duration-200 border
        bg-muted/30 text-muted-foreground border-border/30
        hover:text-foreground hover:bg-muted/50"
      whileTap={{ scale: 0.95 }}
      aria-label="Share section link"
    >
      <Link2 className="w-3.5 h-3.5" />
      <span>Share</span>
    </motion.button>
  );
}
