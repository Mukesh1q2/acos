"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain,
  Send,
  X,
  Trash2,
  MessageSquare,
  Loader2,
  Bot,
  User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatMarkdown } from "./chat-markdown";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

const SUGGESTED_QUESTIONS = [
  "What is Orthogonal Thread Memory?",
  "How does HBTA achieve O(N log N)?",
  "Why is Path C the recommended training strategy?",
  "What are the main failure points?",
  "How does continuous learning work?",
  "What makes ACOS different from ChatGPT?",
];

export function ChatPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return;

      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: content.trim(),
        timestamp: Date.now(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setInput("");
      setIsLoading(true);

      try {
        const apiMessages = [...messages, userMessage].map((m) => ({
          role: m.role,
          content: m.content,
        }));

        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ messages: apiMessages }),
        });

        const data = await res.json();

        if (data.success && data.response) {
          const assistantMessage: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: data.response,
            timestamp: Date.now(),
          };
          setMessages((prev) => [...prev, assistantMessage]);
        } else {
          const errorMessage: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content:
              data.error ||
              "An error occurred while generating a response. Please try again.",
            timestamp: Date.now(),
          };
          setMessages((prev) => [...prev, errorMessage]);
        }
      } catch {
        const errorMessage: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content:
            "Connection error. Please check your network and try again.",
          timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setIsLoading(false);
      }
    },
    [messages, isLoading]
  );

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      sendMessage(input);
    },
    [input, sendMessage]
  );

  const handleSuggestedQuestion = useCallback(
    (question: string) => {
      sendMessage(question);
    },
    [sendMessage]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setInput("");
  }, []);

  return (
    <>
      {/* FAB Trigger Button */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.2 }}
            onClick={() => setIsOpen(true)}
            className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-500/25 flex items-center justify-center transition-colors duration-200 hover:shadow-emerald-500/40"
            aria-label="Open AI chat"
          >
            <Brain className="w-6 h-6" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Chat Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="fixed bottom-0 right-0 sm:bottom-6 sm:right-6 z-50 flex flex-col w-full sm:w-[420px] h-full sm:h-[600px] sm:max-h-[80vh] bg-slate-950 border border-border/30 sm:rounded-2xl shadow-2xl shadow-black/40 overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border/30 bg-slate-950/80 backdrop-blur-sm flex-shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-600/20 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-emerald-400" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-foreground">
                    ACOS Assistant
                  </h3>
                  <p className="text-[10px] text-muted-foreground">
                    Ask about ACOS / AFM
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                {messages.length > 0 && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={clearChat}
                    className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    aria-label="Clear chat"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsOpen(false)}
                  className="h-8 w-8 text-muted-foreground hover:text-foreground"
                  aria-label="Close chat"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {/* Messages Area */}
            <ScrollArea className="flex-1 min-h-0">
              <div className="p-4 space-y-4">
                {messages.length === 0 && (
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <div className="w-12 h-12 rounded-xl bg-emerald-600/10 flex items-center justify-center mb-3">
                      <MessageSquare className="w-6 h-6 text-emerald-400" />
                    </div>
                    <p className="text-sm font-medium text-foreground mb-1">
                      Ask about ACOS
                    </p>
                    <p className="text-xs text-muted-foreground mb-6 max-w-[260px]">
                      Get answers about the Avadhan Cognitive Operating System
                      architecture, theorems, and design.
                    </p>
                    <div className="flex flex-wrap justify-center gap-2">
                      {SUGGESTED_QUESTIONS.map((q) => (
                        <button
                          key={q}
                          onClick={() => handleSuggestedQuestion(q)}
                          className="text-xs px-3 py-1.5 rounded-full border border-emerald-600/30 text-emerald-400 hover:bg-emerald-600/10 transition-colors duration-150 max-w-[200px] truncate"
                          title={q}
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex gap-2.5 ${
                      message.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    {message.role === "assistant" && (
                      <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-emerald-600/20 flex items-center justify-center mt-0.5">
                        <Bot className="w-3.5 h-3.5 text-emerald-400" />
                      </div>
                    )}
                    <div
                      className={`max-w-[80%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
                        message.role === "user"
                          ? "bg-emerald-600 text-white rounded-br-sm"
                          : "bg-slate-800/80 text-slate-200 border border-border/20 rounded-bl-sm max-h-[400px] overflow-y-auto"
                      }`}
                    >
                      {message.role === "user" ? (
                        message.content
                      ) : (
                        <ChatMarkdown content={message.content} />
                      )}
                    </div>
                    {message.role === "user" && (
                      <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-slate-700 flex items-center justify-center mt-0.5">
                        <User className="w-3.5 h-3.5 text-slate-300" />
                      </div>
                    )}
                  </div>
                ))}

                {isLoading && (
                  <div className="flex gap-2.5 justify-start">
                    <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-emerald-600/20 flex items-center justify-center mt-0.5">
                      <Bot className="w-3.5 h-3.5 text-emerald-400" />
                    </div>
                    <div className="bg-slate-800/80 border border-border/20 rounded-xl rounded-bl-sm px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <Loader2 className="w-3.5 h-3.5 text-emerald-400 animate-spin" />
                        <span className="text-xs text-muted-foreground">
                          Thinking...
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            {/* Suggested Questions (shown when there are messages but few) */}
            {messages.length > 0 && messages.length < 3 && !isLoading && (
              <div className="px-4 pb-2 flex-shrink-0">
                <div className="flex flex-wrap gap-1.5">
                  {SUGGESTED_QUESTIONS.filter(
                    (q) =>
                      !messages.some(
                        (m) => m.role === "user" && m.content === q
                      )
                  )
                    .slice(0, 3)
                    .map((q) => (
                      <button
                        key={q}
                        onClick={() => handleSuggestedQuestion(q)}
                        className="text-[10px] px-2.5 py-1 rounded-full border border-emerald-600/25 text-emerald-400 hover:bg-emerald-600/10 transition-colors duration-150 truncate max-w-[180px]"
                        title={q}
                      >
                        {q}
                      </button>
                    ))}
                </div>
              </div>
            )}

            {/* Input Area */}
            <form
              onSubmit={handleSubmit}
              className="flex items-center gap-2 px-4 py-3 border-t border-border/30 bg-slate-950/80 backdrop-blur-sm flex-shrink-0"
            >
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about ACOS..."
                disabled={isLoading}
                className="flex-1 h-9 rounded-lg bg-slate-800/60 border border-border/30 px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 disabled:opacity-50 transition-all"
              />
              <Button
                type="submit"
                size="icon"
                disabled={!input.trim() || isLoading}
                className="h-9 w-9 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-40 flex-shrink-0"
                aria-label="Send message"
              >
                <Send className="w-4 h-4" />
              </Button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
