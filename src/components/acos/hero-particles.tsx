"use client";

import { useEffect, useRef } from "react";

/* ------------------------------------------------------------------ */
/*  Configuration                                                      */
/* ------------------------------------------------------------------ */

const PARTICLE_COUNT = 70;
const NEURAL_NODE_COUNT = 4;
const CONNECTION_DISTANCE = 100;
const CONNECTION_OPACITY = 0.07;

/* Emerald (#10b981) to teal (#14b8a6) color range */
const PARTICLE_COLORS = [
  { r: 16, g: 185, b: 129 }, // emerald-500
  { r: 20, g: 184, b: 166 }, // teal-500
  { r: 52, g: 211, b: 153 }, // emerald-400
  { r: 45, g: 212, b: 191 }, // teal-400
];

/* ------------------------------------------------------------------ */
/*  Particle Types                                                     */
/* ------------------------------------------------------------------ */

interface Particle {
  x: number;
  y: number;
  radius: number;
  speed: number;
  opacity: number;
  color: { r: number; g: number; b: number };
  driftPhase: number;
  driftSpeed: number;
  driftAmplitude: number;
}

interface NeuralNode extends Particle {
  glowRadius: number;
  pulsePhase: number;
}

/* ------------------------------------------------------------------ */
/*  Helper: create a particle                                          */
/* ------------------------------------------------------------------ */

function createParticle(canvasWidth: number, canvasHeight: number, isStatic: boolean): Particle {
  const color = PARTICLE_COLORS[Math.floor(Math.random() * PARTICLE_COLORS.length)];
  return {
    x: Math.random() * canvasWidth,
    y: isStatic ? Math.random() * canvasHeight : canvasHeight + Math.random() * 50,
    radius: 1 + Math.random() * 2,
    speed: 0.2 + Math.random() * 0.6,
    opacity: 0.2 + Math.random() * 0.4,
    color,
    driftPhase: Math.random() * Math.PI * 2,
    driftSpeed: 0.005 + Math.random() * 0.015,
    driftAmplitude: 0.3 + Math.random() * 0.7,
  };
}

function createNeuralNode(canvasWidth: number, canvasHeight: number, isStatic: boolean): NeuralNode {
  const color = PARTICLE_COLORS[Math.floor(Math.random() * 2)]; // emerald or teal
  return {
    x: Math.random() * canvasWidth,
    y: isStatic ? Math.random() * canvasHeight : canvasHeight + Math.random() * 50,
    radius: 4 + Math.random() * 2,
    speed: 0.15 + Math.random() * 0.25,
    opacity: 0.4 + Math.random() * 0.2,
    color,
    driftPhase: Math.random() * Math.PI * 2,
    driftSpeed: 0.003 + Math.random() * 0.007,
    driftAmplitude: 0.5 + Math.random() * 0.5,
    glowRadius: 12 + Math.random() * 8,
    pulsePhase: Math.random() * Math.PI * 2,
  };
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function HeroParticles() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    /* Respect prefers-reduced-motion */
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    /* Sizing */
    const resize = () => {
      const parent = canvas.parentElement;
      if (!parent) return;
      canvas.width = parent.clientWidth;
      canvas.height = parent.clientHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    /* Initialize particles */
    const w = canvas.width;
    const h = canvas.height;
    const particles: Particle[] = [];
    const neuralNodes: NeuralNode[] = [];

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push(createParticle(w, h, prefersReducedMotion));
    }
    for (let i = 0; i < NEURAL_NODE_COUNT; i++) {
      neuralNodes.push(createNeuralNode(w, h, prefersReducedMotion));
    }

    /* All entities for connection drawing */
    const allEntities = () => [...particles, ...neuralNodes] as Particle[];

    /* ---- Animation loop ---- */
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const cw = canvas.width;
      const ch = canvas.height;

      const entities = allEntities();

      /* Draw connections first (behind particles) */
      for (let i = 0; i < entities.length; i++) {
        for (let j = i + 1; j < entities.length; j++) {
          const dx = entities[i].x - entities[j].x;
          const dy = entities[i].y - entities[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < CONNECTION_DISTANCE) {
            const opacity = CONNECTION_OPACITY * (1 - dist / CONNECTION_DISTANCE);
            ctx.beginPath();
            ctx.moveTo(entities[i].x, entities[i].y);
            ctx.lineTo(entities[j].x, entities[j].y);
            ctx.strokeStyle = `rgba(16, 185, 129, ${opacity})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }

      /* Draw small particles */
      for (const p of particles) {
        if (!prefersReducedMotion) {
          p.y -= p.speed;
          p.driftPhase += p.driftSpeed;
          p.x += Math.sin(p.driftPhase) * p.driftAmplitude;

          /* Fade based on vertical position */
          const fadeZone = ch * 0.15;
          let fadeOpacity = p.opacity;
          if (p.y < fadeZone) {
            fadeOpacity *= p.y / fadeZone;
          } else if (p.y > ch - fadeZone) {
            fadeOpacity *= (ch - p.y) / fadeZone;
          }

          /* Reset particle at bottom when it goes off top */
          if (p.y < -10) {
            p.y = ch + 10;
            p.x = Math.random() * cw;
            p.driftPhase = Math.random() * Math.PI * 2;
          }

          p.opacity = Math.max(0.05, fadeOpacity);
        }

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${p.color.r}, ${p.color.g}, ${p.color.b}, ${p.opacity})`;
        ctx.fill();
      }

      /* Draw neural nodes with glow */
      for (const node of neuralNodes) {
        if (!prefersReducedMotion) {
          node.y -= node.speed;
          node.driftPhase += node.driftSpeed;
          node.x += Math.sin(node.driftPhase) * node.driftAmplitude;
          node.pulsePhase += 0.02;

          /* Fade based on vertical position */
          const fadeZone = ch * 0.15;
          let fadeOpacity = node.opacity;
          if (node.y < fadeZone) {
            fadeOpacity *= node.y / fadeZone;
          } else if (node.y > ch - fadeZone) {
            fadeOpacity *= (ch - node.y) / fadeZone;
          }

          /* Reset at bottom */
          if (node.y < -10) {
            node.y = ch + 10;
            node.x = Math.random() * cw;
            node.driftPhase = Math.random() * Math.PI * 2;
          }

          node.opacity = Math.max(0.1, fadeOpacity);
        }

        const pulseScale = 1 + 0.15 * Math.sin(node.pulsePhase);
        const glowRadius = node.glowRadius * pulseScale;

        /* Soft glow */
        const gradient = ctx.createRadialGradient(
          node.x, node.y, 0,
          node.x, node.y, glowRadius
        );
        gradient.addColorStop(0, `rgba(${node.color.r}, ${node.color.g}, ${node.color.b}, ${node.opacity * 0.3})`);
        gradient.addColorStop(0.5, `rgba(${node.color.r}, ${node.color.g}, ${node.color.b}, ${node.opacity * 0.08})`);
        gradient.addColorStop(1, `rgba(${node.color.r}, ${node.color.g}, ${node.color.b}, 0)`);
        ctx.beginPath();
        ctx.arc(node.x, node.y, glowRadius, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();

        /* Core dot */
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius * pulseScale, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${node.color.r}, ${node.color.g}, ${node.color.b}, ${node.opacity})`;
        ctx.fill();
      }

      if (!prefersReducedMotion) {
        animationFrameRef.current = requestAnimationFrame(draw);
      }
    };

    draw();

    return () => {
      cancelAnimationFrame(animationFrameRef.current);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ zIndex: 0 }}
      aria-hidden="true"
    />
  );
}
