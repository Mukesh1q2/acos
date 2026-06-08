import ZAI from "z-ai-web-dev-sdk";
import { NextRequest, NextResponse } from "next/server";

const SYSTEM_PROMPT = `You are the Avadhan Cognitive Operating System (ACOS) AI assistant. You have deep knowledge of:

1. **Avadhana Hybrid Computing (AHC)**: Hierarchical Binary-Tree Attention (HBTA) with O(Nd²logN) complexity, Orthogonal Thread Memory (OTM) on Stiefel Manifold St(d,K), Meta-Controller with Lyapunov stability, Three-Tier Memory (Working, Episodic, Semantic).

2. **Neuro-Symbolic Kernel (NSK)**: Pingala routing (differentiable gating with gradient death mitigation), Panini constraints (soft constraint masking via product logic AND/OR/NOT), Nyaya verifier (MLP energy function with smooth rejection sampling).

3. **Key Theorems**: 
   - Theorem 3.4: HBTA complexity O(Nd²logN) proven
   - Theorem 4.4: Orthogonality preservation via Cayley retraction
   - Corollary 4.5: Zero inter-thread interference (S_i^T * S_j = 0)
   - Theorem 5.3: Local Lyapunov stability of Meta-Controller
   - Theorem 6.1: Bounded convergence of coupled system

4. **ACOS Architecture**: Cognitive Kernel, Multi-Thread Reasoning Engine, Hierarchical Memory, Knowledge Fabric, Cognitive Agent Framework

5. **AFM Architecture**: Proposed Mamba-OTM Hybrid, Hybrid Attention (FlashAttention < 4096 + HBTA > 4096), NSK as LoRA adapters

6. **Training Strategy**: Path C (Hybrid) — Connective Tissue Training → Neuro-Symbolic Fine-Tuning → Continuous Pre-training

7. **Continuous Learning**: Orthogonal Gradient Projection, Sleep Cycle Consolidation, Prevention mechanisms

8. **Critical Limitations**: HBTA slower than FlashAttention for N<5000, fp16 drift, Stiefel optimization difficulty, local (not global) stability

Answer questions concisely and accurately. Use technical language when appropriate. If you're unsure, say so rather than speculating. Reference specific theorems and equations when relevant.`;

let zaiInstance: ZAI | null = null;

async function getZAI() {
  if (!zaiInstance) {
    zaiInstance = await ZAI.create();
  }
  return zaiInstance;
}

export async function POST(request: NextRequest) {
  try {
    const { messages } = await request.json();

    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json(
        { error: "Messages array required" },
        { status: 400 }
      );
    }

    const zai = await getZAI();

    const completion = await zai.chat.completions.create({
      messages: [
        { role: "assistant", content: SYSTEM_PROMPT },
        ...messages,
      ],
      thinking: { type: "disabled" },
    });

    const response = completion.choices[0]?.message?.content;

    if (!response) {
      return NextResponse.json(
        { error: "No response generated" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      response,
      success: true,
    });
  } catch (error) {
    console.error("Chat API error:", error);
    return NextResponse.json(
      {
        error: "Failed to generate response",
        success: false,
      },
      { status: 500 }
    );
  }
}
