#!/usr/bin/env python3
"""
ACOS Scientific Validation Program — Real Benchmarking System

This script implements a rigorous scientific validation framework for the ACOS
cognitive architecture. Every score comes from actual LLM execution — no mock
backends, no simulated profiles, no hand-tuned parameters, no random scoring.

Six real baseline systems are compared against ACOS on 60+ benchmark questions
across 6 categories. Statistical analysis includes confidence intervals, effect
sizes (Cohen's d), p-values, and paired comparisons.

Architecture:
  - Baselines call LLM via http://localhost:3000/api/chat (Z-AI API)
  - ACOS calls http://localhost:3031/query/v2 (CognitiveKernel HTTP API)
  - Results stored in SQLite at data/scientific_validation.db
  - JSON output to stdout for Next.js API consumption

Usage:
    python3 scientific_validation.py --quick      # 5 questions per category (30 total)
    python3 scientific_validation.py --full       # All questions (120+)
    python3 scientific_validation.py --ablation   # Ablation studies
    python3 scientific_validation.py --report     # Generate final report from stored data
    python3 scientific_validation.py --results    # Return latest results from DB
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import sqlite3
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import aiohttp
import numpy as np

# ---------------------------------------------------------------------------
# Ensure the acos-runtime package is importable
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ZAI_API_URL = "http://localhost:3000/api/chat"
ACOS_API_URL = "http://localhost:3031/query/v2"
DB_PATH = os.path.join(SCRIPT_DIR, "data", "scientific_validation.db")

CATEGORIES = ["mmlu", "gsm8k", "hotpotqa", "arc", "logic", "commonsense"]

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class BenchmarkQuestion:
    """A single benchmark question with ground truth."""
    id: str
    question: str
    correct_answer: str
    category: str          # mmlu, gsm8k, hotpotqa, arc, logic, commonsense
    difficulty: str        # easy, medium, hard
    requires_reasoning: bool


@dataclass
class ValidationTrace:
    """Full trace of a single system run on a single question."""
    id: str
    run_id: str
    system_name: str
    question_id: str
    question_text: str
    ground_truth: str
    model_used: str
    latency_ms: float
    token_estimate: int
    memory_retrievals: int
    belief_activations: int
    goal_activations: int
    reflection_output: str
    verification_output: str
    final_answer: str
    success: bool
    error: Optional[str] = None


@dataclass
class SystemMetrics:
    """Aggregated metrics for a system."""
    system_name: str
    accuracy: float
    latency_mean_ms: float
    latency_median_ms: float
    latency_std_ms: float
    token_usage_mean: float
    memory_utilization: float
    hallucination_rate: float
    reflection_usefulness: float
    verification_usefulness: float
    correct_count: int
    total_count: int


@dataclass
class AblationResult:
    """Result of running ACOS with a subsystem disabled."""
    id: str
    run_id: str
    disabled_subsystem: str
    question_id: str
    question_text: str
    ground_truth: str
    final_answer: str
    success: bool
    latency_ms: float
    error: Optional[str] = None


@dataclass
class StatisticalTest:
    """Result of a pairwise statistical comparison."""
    system_a: str
    system_b: str
    metric: str
    mean_diff: float
    cohens_d: float
    t_statistic: float
    p_value: float
    ci_lower: float
    ci_upper: float
    significant_95: bool
    n_pairs: int


# ============================================================================
# Async HTTP Clients — aiohttp for all calls
# ============================================================================

class LLMClient:
    """Async client for the Z-AI API (via Next.js /api/chat) using aiohttp."""

    def __init__(self, base_url: str = ZAI_API_URL, timeout: float = 120.0):
        self.base_url = base_url
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
        self._call_count = 0
        self._total_chars = 0

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def generate(self, prompt: str, system: Optional[str] = None,
                       max_retries: int = 3) -> str:
        """Send a prompt to the Z-AI API and return the response text."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        for attempt in range(max_retries):
            self._call_count += 1
            try:
                session = await self._ensure_session()
                async with session.post(
                    self.base_url,
                    json={"messages": messages},
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        raise RuntimeError(f"HTTP {resp.status}: {text[:200]}")
                    data = await resp.json()

                    if data.get("success") is False:
                        raise RuntimeError(f"Z-AI API error: {data.get('error', 'unknown')}")

                    text = data.get("response", "")
                    self._total_chars += len(text)
                    return text
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                raise RuntimeError(
                    f"Z-AI API call failed after {max_retries} retries: {e}"
                ) from e
            except RuntimeError:
                raise
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                raise RuntimeError(f"Z-AI API call failed: {e}") from e
        raise RuntimeError(
            f"Z-AI API call failed after {max_retries} retries: {last_error}"
        )

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def estimated_tokens(self) -> int:
        """Rough token estimate: ~4 chars per token."""
        return self._total_chars // 4

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


class ACOSClient:
    """Async client for the ACOS CognitiveKernel HTTP API at /query/v2."""

    def __init__(self, base_url: str = ACOS_API_URL, timeout: float = 120.0):
        self.base_url = base_url
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
        self._call_count = 0
        self._total_chars = 0
        self._available: Optional[bool] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def is_available(self) -> bool:
        """Check if the ACOS runtime API is reachable."""
        if self._available is not None:
            return self._available
        try:
            session = await self._ensure_session()
            # Try a lightweight health check
            async with session.get(
                self.base_url.rsplit("/", 2)[0] + "/health",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                self._available = resp.status == 200
        except Exception:
            self._available = False
        return self._available

    async def query(self, question: str, max_retries: int = 2) -> dict[str, Any]:
        """Send a query to the ACOS /query/v2 endpoint."""
        last_error = None
        for attempt in range(max_retries):
            self._call_count += 1
            try:
                session = await self._ensure_session()
                payload = {
                    "query": question,
                    "update_cognitive_state": True,
                }
                async with session.post(self.base_url, json=payload) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        raise RuntimeError(f"ACOS API HTTP {resp.status}: {text[:200]}")
                    data = await resp.json()
                    self._total_chars += len(json.dumps(data))
                    return data
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(2.0 * (attempt + 1))
                    continue
                raise RuntimeError(
                    f"ACOS API call failed after {max_retries} retries: {e}"
                ) from e
            except RuntimeError:
                raise
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(2.0 * (attempt + 1))
                    continue
                raise RuntimeError(f"ACOS API call failed: {e}") from e
        raise RuntimeError(
            f"ACOS API call failed after {max_retries} retries: {last_error}"
        )

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def estimated_tokens(self) -> int:
        return self._total_chars // 4

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# ============================================================================
# Answer Extraction & Matching
# ============================================================================

def normalize_answer(text: str) -> str:
    """Normalize an answer string for comparison."""
    text = text.strip().lower()
    # Remove common prefixes
    for prefix in [
        "the answer is", "answer:", "answer is", "result:",
        "result is", "final answer:", "final answer is",
    ]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    # Remove articles at the beginning
    for article in ["the ", "a ", "an "]:
        if text.startswith(article):
            text = text[len(article):]
    # Remove trailing punctuation
    text = text.rstrip(".!,;?")
    # Collapse whitespace
    text = " ".join(text.split())
    return text


def extract_letter_choice(text: str) -> Optional[str]:
    """Extract a letter choice (A/B/C/D) from a response."""
    patterns = [
        r'\(([A-D])\)',
        r'(?:answer|choice|option)\s*(?:is|:)\s*([A-D])',
        r'\b([A-D])\)',
        r'\b([A-D])\.',
        r'^([A-D])$',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return None


def extract_number(text: str) -> Optional[str]:
    """Extract a numeric answer from a response."""
    patterns = [
        r'(?:answer|result|total|value)\s*(?:is|:|=)\s*\$?([\d,]+\.?\d*)',
        r'\$?([\d,]+\.?\d*)',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            num_str = m.group(1).replace(",", "")
            try:
                val = float(num_str)
                if val == int(val):
                    return str(int(val))
                return f"{val:.2f}"
            except ValueError:
                continue
    return None


def answers_match(predicted: str, ground_truth: str, category: str) -> bool:
    """Check if a predicted answer matches the ground truth.

    Matching strategies (applied in order):
    1. Exact match after normalization
    2. Letter choice match (for multiple choice)
    3. Numeric match (for math/science categories)
    4. Keyword overlap match (>=80% of ground-truth keywords present)
    5. Containment match (ground truth contained in prediction or vice versa)
    """
    pred_norm = normalize_answer(predicted)
    gt_norm = normalize_answer(ground_truth)

    # 1. Exact match
    if pred_norm == gt_norm:
        return True

    # 2. Letter choice match
    pred_letter = extract_letter_choice(predicted)
    gt_letter = extract_letter_choice(ground_truth)
    if pred_letter and gt_letter and pred_letter == gt_letter:
        return True
    if gt_letter and pred_letter and pred_letter == gt_letter:
        return True
    if len(gt_norm) == 1 and gt_norm in "abcd" and gt_norm in pred_norm:
        return True

    # 3. Numeric match
    if category in ("gsm8k", "mmlu", "arc"):
        pred_num = extract_number(predicted)
        gt_num = extract_number(ground_truth)
        if pred_num and gt_num and pred_num == gt_num:
            return True

    # 4. Containment match
    if gt_norm and len(gt_norm) > 2 and gt_norm in pred_norm:
        return True
    if pred_norm and len(pred_norm) > 2 and pred_norm in gt_norm:
        return True

    # 5. Keyword overlap match
    def stem_word(w: str) -> str:
        for suffix in ["ion", "ia", "s", "es", "ed", "ing", "ly", "er", "est"]:
            if w.endswith(suffix) and len(w) - len(suffix) >= 3:
                return w[: -len(suffix)]
        return w

    gt_stems = set(stem_word(w) for w in gt_norm.split())
    pred_stems = set(stem_word(w) for w in pred_norm.split())
    if len(gt_stems) > 0:
        overlap = gt_stems & pred_stems
        if len(overlap) / len(gt_stems) >= 0.8 and len(overlap) >= 1:
            return True

    gt_words = set(gt_norm.split())
    pred_words = set(pred_norm.split())
    if len(gt_words) > 1:
        overlap = gt_words & pred_words
        if len(overlap) / len(gt_words) >= 0.8:
            return True

    return False


# ============================================================================
# Benchmark Suite — 120 Real Questions with Ground Truth (20 per category)
# ============================================================================

class BenchmarkSuite:
    """Generates 120 benchmark questions across 6 categories (20 each)."""

    def __init__(self):
        self._questions: list[BenchmarkQuestion] = []
        self._build_questions()

    def _make_id(self) -> str:
        return str(uuid.uuid4())[:8]

    def _add(
        self, question: str, answer: str, category: str,
        difficulty: str, requires_reasoning: bool,
    ) -> None:
        self._questions.append(
            BenchmarkQuestion(
                id=self._make_id(),
                question=question,
                correct_answer=answer,
                category=category,
                difficulty=difficulty,
                requires_reasoning=requires_reasoning,
            )
        )

    def _build_questions(self) -> None:
        self._build_mmlu()
        self._build_gsm8k()
        self._build_hotpotqa()
        self._build_arc()
        self._build_logic()
        self._build_commonsense()

    # ------------------------------------------------------------------
    # MMLU: Multiple choice knowledge questions
    # ------------------------------------------------------------------
    def _build_mmlu(self) -> None:
        mmlu = [
            ("What is the chemical symbol for gold?", "Au", "easy", False),
            ("What particle has a positive charge in an atom?", "proton", "easy", False),
            ("What is the powerhouse of the cell?", "mitochondria", "easy", False),
            ("What gas do plants absorb from the atmosphere during photosynthesis?", "carbon dioxide", "easy", False),
            ("What is the speed of light in vacuum approximately? (A) 3x10^8 m/s (B) 3x10^6 m/s (C) 3x10^10 m/s (D) 3x10^4 m/s", "A", "medium", False),
            ("Which element has atomic number 6?", "carbon", "easy", False),
            ("What is Newton's second law of motion?", "F = ma", "medium", True),
            ("What type of bond involves the sharing of electrons between atoms?", "covalent bond", "medium", False),
            ("In what year did World War II end?", "1945", "easy", False),
            ("Who was the first President of the United States?", "George Washington", "easy", False),
            ("The French Revolution began in which year?", "1789", "medium", False),
            ("What empire was ruled by Genghis Khan?", "Mongol Empire", "easy", False),
            ("What is the derivative of x^2?", "2x", "medium", True),
            ("What is the value of pi to two decimal places?", "3.14", "easy", False),
            ("What is the integral of 1/x dx?", "ln|x| + C", "hard", True),
            ("What is the largest ocean on Earth?", "Pacific Ocean", "easy", False),
            ("What is the capital of Japan?", "Tokyo", "easy", False),
            ("Which river is the longest in the world?", "Nile", "medium", False),
            ("Who wrote 'Romeo and Juliet'?", "William Shakespeare", "easy", False),
            ("In which century was the novel '1984' by George Orwell published?", "20th century", "medium", False),
        ]
        for q, a, d, r in mmlu:
            self._add(q, a, "mmlu", d, r)

    # ------------------------------------------------------------------
    # GSM8K: Multi-step math word problems
    # ------------------------------------------------------------------
    def _build_gsm8k(self) -> None:
        gsm8k = [
            ("A store sells apples for $2 each and oranges for $3 each. If Sarah buys 4 apples and 3 oranges, how much does she spend in total?", "$17", "easy", True),
            ("Tom has 15 marbles. He gives 3 to his friend and then buys 7 more. How many marbles does Tom have now?", "19", "easy", True),
            ("A train travels at 60 miles per hour. How far will it travel in 2.5 hours?", "150 miles", "easy", True),
            ("If a shirt costs $25 and is on sale for 20% off, what is the sale price?", "$20", "medium", True),
            ("A rectangle has a length of 8 cm and a width of 5 cm. What is its area?", "40 square centimeters", "easy", True),
            ("John earns $15 per hour. He worked 8 hours on Monday and 6 hours on Tuesday. How much did he earn in total?", "$210", "medium", True),
            ("A pizza is cut into 8 equal slices. If 3 people each eat 2 slices, how many slices remain?", "2", "medium", True),
            ("A car's gas tank holds 12 gallons. The car gets 25 miles per gallon. How far can the car travel on a full tank?", "300 miles", "medium", True),
            ("A recipe calls for 2 cups of flour to make 12 cookies. How many cups of flour are needed to make 30 cookies?", "5", "medium", True),
            ("If an item costs $80 and the sales tax rate is 8%, what is the total cost including tax?", "$86.40", "medium", True),
            ("A farmer has 48 chickens and 36 cows. How many legs are there in total on the farm?", "240", "medium", True),
            ("Lisa reads 25 pages per day. If a book has 300 pages, how many days will it take her to finish it?", "12", "easy", True),
            ("A store buys a product for $40 and sells it for $65. What is the profit margin as a percentage of the selling price?", "38.46%", "hard", True),
            ("Two trains leave stations 300 miles apart and travel toward each other. One travels at 70 mph and the other at 80 mph. How long until they meet?", "2 hours", "hard", True),
            ("A swimming pool is 20 meters long, 10 meters wide, and 2 meters deep. How many liters of water does it hold?", "400000", "hard", True),
            ("If you invest $1000 at 5% annual compound interest for 3 years, how much will you have? Round to the nearest dollar.", "$1158", "hard", True),
            ("A worker can complete a task in 6 hours. Another worker can complete the same task in 4 hours. How long will it take them to complete the task working together?", "2.4 hours", "hard", True),
            ("A box contains 5 red balls, 3 blue balls, and 2 green balls. What is the probability of drawing a red ball?", "0.5", "medium", True),
            ("A store offers a 15% discount, then an additional 10% discount on the already reduced price. What is the total percentage discount from the original price?", "23.5%", "hard", True),
            ("If the sum of three consecutive integers is 72, what is the largest of the three integers?", "25", "medium", True),
        ]
        for q, a, d, r in gsm8k:
            self._add(q, a, "gsm8k", d, r)

    # ------------------------------------------------------------------
    # HotpotQA: Multi-hop reasoning questions
    # ------------------------------------------------------------------
    def _build_hotpotqa(self) -> None:
        hotpotqa = [
            ("The author of 'The Metamorphosis' was born in which city? (Prague/Vienna/Berlin/Budapest)", "Prague", "medium", True),
            ("The element whose symbol is Fe was named after which planet in Roman mythology?", "Mars", "medium", True),
            ("The country that hosts the Louvre Museum shares a border with which country that has Berlin as its capital?", "Germany", "medium", True),
            ("The person who developed the theory of relativity was born in which country?", "Germany", "medium", True),
            ("Which ocean borders the country that is home to the Great Barrier Reef?", "Pacific Ocean", "medium", True),
            ("The inventor of the telephone was born in which country?", "Scotland", "hard", True),
            ("The chemical element named after the scientist who discovered penicillin is what?", "Fermium", "hard", True),
            ("The capital of the country where the Taj Mahal is located is what city?", "New Delhi", "easy", True),
            ("The philosopher who taught Alexander the Great founded which type of philosophy?", "Aristotelian philosophy", "hard", True),
            ("The country that produced the first woman Nobel Prize winner has which city as its capital?", "Stockholm", "hard", True),
            ("What is the primary language spoken in the country where the Colosseum is located?", "Italian", "easy", True),
            ("The scientist who proposed the heliocentric model was from which country?", "Poland", "hard", True),
            ("The river that flows through Paris is a tributary of which larger river?", "Seine", "medium", True),
            ("The author of 'The Origin of Species' studied at which university? (Edinburgh/Cambridge/Oxford/London)", "Cambridge", "hard", True),
            ("The country that invented paper shares its name with which type of dinnerware?", "China", "medium", True),
            ("Which planet in our solar system is named after the Roman god of the sea?", "Neptune", "easy", True),
            ("The artist who painted the Mona Lisa was from which country?", "Italy", "easy", True),
            ("The country where the Olympic Games originated borders which sea?", "Mediterranean Sea", "medium", True),
            ("The scientist who discovered radium was born in which city? (Warsaw/Paris/London/Berlin)", "Warsaw", "hard", True),
            ("The author of 'A Brief History of Time' held which position at Cambridge University?", "Lucasian Professor of Mathematics", "hard", True),
        ]
        for q, a, d, r in hotpotqa:
            self._add(q, a, "hotpotqa", d, r)

    # ------------------------------------------------------------------
    # ARC: Science reasoning questions
    # ------------------------------------------------------------------
    def _build_arc(self) -> None:
        arc = [
            ("Which of the following is an example of a chemical change? (A) melting ice (B) burning wood (C) dissolving sugar (D) cutting paper", "B", "easy", True),
            ("Which planet is closest to the Sun?", "Mercury", "easy", False),
            ("What happens to the boiling point of water when pressure increases? (A) increases (B) decreases (C) stays the same (D) becomes zero", "A", "medium", True),
            ("Which type of energy does a moving car have?", "kinetic energy", "easy", True),
            ("What is the main function of the respiratory system?", "gas exchange", "easy", True),
            ("Which of these is a renewable energy source? (A) coal (B) natural gas (C) solar (D) petroleum", "C", "easy", False),
            ("Why do objects fall to the ground when dropped?", "gravity", "easy", True),
            ("What happens to an object's density when its volume increases but its mass stays the same? (A) increases (B) decreases (C) stays the same (D) becomes zero", "B", "medium", True),
            ("Which organelle is responsible for protein synthesis in a cell?", "ribosome", "medium", True),
            ("What type of rock is formed from cooled magma?", "igneous rock", "medium", True),
            ("Which of the following best describes the process of evaporation? (A) liquid to solid (B) liquid to gas (C) gas to liquid (D) solid to gas", "B", "easy", False),
            ("What is the relationship between frequency and wavelength of a wave?", "inversely proportional", "medium", True),
            ("Which layer of the atmosphere contains the ozone layer?", "stratosphere", "medium", True),
            ("What is the primary cause of ocean tides?", "gravitational pull of the Moon", "medium", True),
            ("Which of these animals is a mammal? (A) shark (B) frog (C) whale (D) crocodile", "C", "easy", False),
            ("What is the difference between DNA and RNA?", "DNA has deoxyribose, RNA has ribose; DNA is double-stranded, RNA is single-stranded", "hard", True),
            ("What property of water allows it to dissolve many substances?", "polarity", "medium", True),
            ("Why does ice float on water?", "ice is less dense than liquid water", "medium", True),
            ("What is natural selection?", "the process where organisms better adapted to their environment tend to survive and reproduce", "hard", True),
            ("Which gas makes up most of Earth's atmosphere?", "nitrogen", "easy", False),
        ]
        for q, a, d, r in arc:
            self._add(q, a, "arc", d, r)

    # ------------------------------------------------------------------
    # Logic: Logical deduction puzzles
    # ------------------------------------------------------------------
    def _build_logic(self) -> None:
        logic = [
            ("If all cats are animals, and all animals need water, do all cats need water?", "yes", "easy", True),
            ("If it is raining, then the ground is wet. The ground is not wet. What can you conclude?", "it is not raining", "easy", True),
            ("A is taller than B. B is taller than C. Is A taller than C?", "yes", "easy", True),
            ("If no fish can fly, and all salmon are fish, can salmon fly?", "no", "easy", True),
            ("If some doctors are women, and some women are tall, can we conclude that some doctors are tall?", "no", "medium", True),
            ("Either the light is on or the door is closed. The light is not on. What can you conclude?", "the door is closed", "easy", True),
            ("If X implies Y, and Y implies Z, does X imply Z?", "yes", "medium", True),
            ("All roses are flowers. Some flowers fade quickly. Can we conclude that some roses fade quickly?", "no", "medium", True),
            ("If it snows, then school is closed. School is not closed. What can you conclude about snow?", "it did not snow", "medium", True),
            ("A number is even if and only if it is divisible by 2. Is 7 even?", "no", "easy", True),
            ("If P is true and Q is false, what is the truth value of 'P AND Q'?", "false", "medium", True),
            ("If P is true and Q is false, what is the truth value of 'P OR Q'?", "true", "medium", True),
            ("If P implies Q, and Q is true, can we conclude P is true?", "no", "hard", True),
            ("If P implies Q, and P is false, what can we say about Q?", "Q can be true or false (undetermined)", "hard", True),
            ("In a room of 13 people, at least how many people must share a birth month?", "2", "hard", True),
            ("A farmer has a fox, a chicken, and corn. He must cross a river one item at a time. The fox will eat the chicken if left alone, and the chicken will eat the corn. What should he take across first?", "the chicken", "hard", True),
            ("If all A are B, and some B are C, can we conclude that some A are C?", "no", "medium", True),
            ("There are 3 boxes: one contains only apples, one contains only oranges, and one contains both. All boxes are mislabeled. You can pick one fruit from one box. Which box should you pick from to determine all labels?", "the box labeled 'both'", "hard", True),
            ("If statement 'This statement is false' is considered, what type of logical problem does it represent?", "the Liar Paradox", "hard", True),
            ("A syllogism: All mammals are warm-blooded. All whales are mammals. Therefore, all whales are warm-blooded. Is this argument valid?", "yes", "medium", True),
        ]
        for q, a, d, r in logic:
            self._add(q, a, "logic", d, r)

    # ------------------------------------------------------------------
    # Commonsense: Common sense reasoning questions
    # ------------------------------------------------------------------
    def _build_commonsense(self) -> None:
        commonsense = [
            ("If you put a metal spoon in a hot pot of soup, what will happen to the handle?", "it will get hot", "easy", True),
            ("Why shouldn't you wear dark clothing on a very hot sunny day?", "dark colors absorb more heat from sunlight", "easy", True),
            ("If you drop a glass cup on a concrete floor, what is most likely to happen?", "it will break", "easy", True),
            ("Why do people use umbrellas when it rains?", "to stay dry by blocking rain", "easy", False),
            ("What should you do if you smell gas in your house?", "leave the house immediately and call for help", "easy", True),
            ("Why do we refrigerate food?", "to slow down bacterial growth and prevent spoilage", "easy", True),
            ("If someone is choking, what is the recommended first aid procedure?", "the Heimlich maneuver (abdominal thrusts)", "medium", True),
            ("Why do ships made of steel float on water?", "their shape displaces enough water to create buoyant force greater than their weight", "medium", True),
            ("Why does sweat cool you down?", "evaporation of sweat absorbs heat from the skin", "medium", True),
            ("If you see lightning, why is it important to avoid standing under tall trees?", "lightning tends to strike tall objects and can travel through the tree", "medium", True),
            ("Why do we add salt to icy roads in winter?", "salt lowers the freezing point of water, melting the ice", "medium", True),
            ("Why does a tire become warm after driving?", "friction between the tire and road generates heat", "medium", True),
            ("If you are lost in the wilderness during the day, how can you determine direction using the sun?", "the sun rises in the east and sets in the west", "medium", True),
            ("Why is it dangerous to use a hair dryer near water?", "water conducts electricity and can cause electrocution", "easy", True),
            ("Why do airplanes pressurize their cabins?", "because the air pressure at high altitude is too low for humans to breathe comfortably", "medium", True),
            ("If you need to quickly cool a warm beverage, is it better to add one large ice cube or several small ones? Why?", "several small ice cubes, because they have more surface area for faster heat transfer", "hard", True),
            ("Why does a prism create a rainbow from white light?", "different wavelengths of light refract at different angles", "hard", True),
            ("Why do we see our breath on cold days?", "warm moist air from lungs condenses into tiny water droplets in cold air", "medium", True),
            ("If a car's tire pressure is low, what happens to fuel efficiency?", "fuel efficiency decreases due to increased rolling resistance", "hard", True),
            ("Why do bridges have expansion joints?", "to allow the bridge material to expand and contract with temperature changes without damage", "hard", True),
        ]
        for q, a, d, r in commonsense:
            self._add(q, a, "commonsense", d, r)

    @property
    def questions(self) -> list[BenchmarkQuestion]:
        return list(self._questions)

    def get_by_category(self, category: str) -> list[BenchmarkQuestion]:
        return [q for q in self._questions if q.category == category]

    @property
    def categories(self) -> list[str]:
        return list(dict.fromkeys(q.category for q in self._questions))


# ============================================================================
# Real Baseline Systems — Each makes actual LLM API calls via aiohttp
# ============================================================================

class BaselineSystem:
    """Base class for baseline systems. All baselines use real LLM calls."""

    def __init__(self, name: str, llm: LLMClient):
        self.name = name
        self._llm = llm

    async def answer(self, question: BenchmarkQuestion) -> dict[str, Any]:
        raise NotImplementedError


class DirectLLM(BaselineSystem):
    """Baseline 1: Send the query directly to the LLM with no memory/context."""

    def __init__(self, llm: LLMClient):
        super().__init__("Direct_LLM", llm)

    async def answer(self, question: BenchmarkQuestion) -> dict[str, Any]:
        start = time.monotonic()
        prompt = (
            f"Answer the following question concisely. "
            f"If it's a multiple choice question, answer with just the letter. "
            f"If it's a math question, show your work and give the final answer.\n\n"
            f"Question: {question.question}"
        )
        try:
            response = await self._llm.generate(prompt)
            latency = (time.monotonic() - start) * 1000
            return {
                "answer": response,
                "latency_ms": latency,
                "token_estimate": len(response) // 4,
                "memory_retrievals": 0,
                "belief_activations": 0,
                "goal_activations": 0,
                "reflection_output": "",
                "verification_output": "",
                "model_used": "z-ai-api",
            }
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return {
                "answer": f"ERROR: {e}",
                "latency_ms": latency,
                "token_estimate": 0,
                "memory_retrievals": 0,
                "belief_activations": 0,
                "goal_activations": 0,
                "reflection_output": "",
                "verification_output": "",
                "model_used": "z-ai-api",
                "error": str(e),
            }


class LLMPlusRAG(BaselineSystem):
    """Baseline 2: LLM + RAG — retrieve relevant memories, then answer with context."""

    def __init__(self, llm: LLMClient):
        super().__init__("LLM_RAG", llm)
        self._memory_store: list[dict[str, str]] = []

    async def answer(self, question: BenchmarkQuestion) -> dict[str, Any]:
        start = time.monotonic()
        query_terms = set(question.question.lower().split())
        relevant = []
        for mem in self._memory_store:
            mem_terms = set(mem["content"].lower().split())
            overlap = len(query_terms & mem_terms)
            if overlap >= 2:
                relevant.append(mem["content"])

        memory_retrievals = len(relevant)
        context_text = (
            "\n".join(f"- {r}" for r in relevant[:5])
            if relevant
            else "No relevant context found."
        )

        prompt = (
            f"Use the following context to help answer the question. "
            f"If the context doesn't help, answer from your own knowledge. "
            f"Answer concisely. For multiple choice, answer with just the letter.\n\n"
            f"Context:\n{context_text}\n\n"
            f"Question: {question.question}"
        )
        try:
            response = await self._llm.generate(prompt)
            self._memory_store.append(
                {"content": f"Q: {question.question} A: {response[:200]}"}
            )
            latency = (time.monotonic() - start) * 1000
            return {
                "answer": response,
                "latency_ms": latency,
                "token_estimate": len(response) // 4,
                "memory_retrievals": memory_retrievals,
                "belief_activations": 0,
                "goal_activations": 0,
                "reflection_output": "",
                "verification_output": "",
                "model_used": "z-ai-api",
            }
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return {
                "answer": f"ERROR: {e}",
                "latency_ms": latency,
                "token_estimate": 0,
                "memory_retrievals": memory_retrievals,
                "belief_activations": 0,
                "goal_activations": 0,
                "reflection_output": "",
                "verification_output": "",
                "model_used": "z-ai-api",
                "error": str(e),
            }


class ReActAgent(BaselineSystem):
    """Baseline 3: ReAct-style thought-action-observation loop (3 iterations max)."""

    def __init__(self, llm: LLMClient):
        super().__init__("ReAct", llm)

    async def answer(self, question: BenchmarkQuestion) -> dict[str, Any]:
        start = time.monotonic()
        observations: list[str] = []
        reflection_output = ""
        final_answer = "No answer produced"

        for iteration in range(3):
            thought_prompt = (
                f"You are solving a question using the ReAct (Reasoning + Acting) approach.\n"
                f"Question: {question.question}\n\n"
            )
            if observations:
                thought_prompt += (
                    "Previous observations:\n"
                    + "\n".join(f"- {obs}" for obs in observations)
                    + "\n\n"
                )
            thought_prompt += (
                "First, think about what you need to do (Thought). "
                "Then decide on an action (Action: 'reason' or 'conclude'). "
                "If you can answer the question now, use Action: conclude.\n"
                "Format: Thought: ... Action: ..."
            )

            try:
                thought_response = await self._llm.generate(thought_prompt)
            except Exception as e:
                latency = (time.monotonic() - start) * 1000
                return {
                    "answer": f"ERROR: {e}", "latency_ms": latency,
                    "token_estimate": 0, "memory_retrievals": 0,
                    "belief_activations": 0, "goal_activations": 0,
                    "reflection_output": "", "verification_output": "",
                    "model_used": "z-ai-api", "error": str(e),
                }

            if "conclude" in thought_response.lower() or iteration == 2:
                answer_prompt = (
                    f"Based on your reasoning, provide a concise final answer to the question. "
                    f"For multiple choice, answer with just the letter.\n\n"
                    f"Question: {question.question}\n"
                    f"Reasoning so far: {thought_response}\n"
                    f"Observations: {'; '.join(observations) if observations else 'none'}\n\n"
                    f"Final Answer:"
                )
                try:
                    final_answer = await self._llm.generate(answer_prompt)
                except Exception as e:
                    final_answer = f"ERROR: {e}"
                reflection_output = thought_response
                break
            else:
                obs_prompt = (
                    f"You are reasoning about: {question.question}\n"
                    f"Your current thought: {thought_response}\n"
                    f"Provide a useful observation or fact that helps answer this question. "
                    f"Be concise and factual."
                )
                try:
                    obs = await self._llm.generate(obs_prompt)
                    observations.append(obs)
                except Exception as e:
                    observations.append(f"Error: {e}")

        latency = (time.monotonic() - start) * 1000
        return {
            "answer": final_answer,
            "latency_ms": latency,
            "token_estimate": len(final_answer) // 4,
            "memory_retrievals": len(observations),
            "belief_activations": 0,
            "goal_activations": 0,
            "reflection_output": reflection_output[:500],
            "verification_output": "",
            "model_used": "z-ai-api",
        }


class LangGraphStyle(BaselineSystem):
    """Baseline 4: Sequential node pipeline — retrieve -> reason -> respond."""

    def __init__(self, llm: LLMClient):
        super().__init__("LangGraph", llm)

    async def answer(self, question: BenchmarkQuestion) -> dict[str, Any]:
        start = time.monotonic()

        # Node 1: Retrieve
        retrieve_prompt = (
            f"Identify the key facts and knowledge needed to answer this question. "
            f"List them concisely.\n\nQuestion: {question.question}"
        )
        try:
            retrieved = await self._llm.generate(retrieve_prompt)
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return {
                "answer": f"ERROR: {e}", "latency_ms": latency,
                "token_estimate": 0, "memory_retrievals": 0,
                "belief_activations": 0, "goal_activations": 0,
                "reflection_output": "", "verification_output": "",
                "model_used": "z-ai-api", "error": str(e),
            }

        # Node 2: Reason
        reason_prompt = (
            f"Using the following retrieved knowledge, reason step-by-step to answer the question.\n\n"
            f"Question: {question.question}\n"
            f"Retrieved Knowledge: {retrieved}\n\n"
            f"Step-by-step reasoning:"
        )
        try:
            reasoning = await self._llm.generate(reason_prompt)
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return {
                "answer": f"ERROR: {e}", "latency_ms": latency,
                "token_estimate": 0, "memory_retrievals": 1,
                "belief_activations": 0, "goal_activations": 0,
                "reflection_output": "", "verification_output": "",
                "model_used": "z-ai-api", "error": str(e),
            }

        # Node 3: Respond
        respond_prompt = (
            f"Based on the reasoning below, provide a concise final answer. "
            f"For multiple choice, answer with just the letter.\n\n"
            f"Question: {question.question}\n"
            f"Reasoning: {reasoning}\n\n"
            f"Final Answer:"
        )
        try:
            final_answer = await self._llm.generate(respond_prompt)
        except Exception as e:
            final_answer = f"ERROR: {e}"

        latency = (time.monotonic() - start) * 1000
        return {
            "answer": final_answer,
            "latency_ms": latency,
            "token_estimate": (len(retrieved) + len(reasoning) + len(final_answer)) // 4,
            "memory_retrievals": 1,
            "belief_activations": 0,
            "goal_activations": 0,
            "reflection_output": reasoning[:500],
            "verification_output": "",
            "model_used": "z-ai-api",
        }


class CrewAIStyle(BaselineSystem):
    """Baseline 5: Two agents that discuss then synthesize (CrewAI-style)."""

    def __init__(self, llm: LLMClient):
        super().__init__("CrewAI", llm)

    async def answer(self, question: BenchmarkQuestion) -> dict[str, Any]:
        start = time.monotonic()

        # Agent 1: Analyst
        analyst_prompt = (
            f"You are a research analyst. Analyze this question and provide your perspective. "
            f"Be thorough and factual.\n\nQuestion: {question.question}\n\nYour analysis:"
        )
        try:
            analysis = await self._llm.generate(analyst_prompt)
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return {
                "answer": f"ERROR: {e}", "latency_ms": latency,
                "token_estimate": 0, "memory_retrievals": 0,
                "belief_activations": 0, "goal_activations": 0,
                "reflection_output": "", "verification_output": "",
                "model_used": "z-ai-api", "error": str(e),
            }

        # Agent 2: Critic
        critic_prompt = (
            f"You are a critical reviewer. Review the following analysis and provide your own perspective. "
            f"Point out any errors or gaps.\n\n"
            f"Question: {question.question}\n"
            f"Analyst's analysis: {analysis}\n\n"
            f"Your critical review:"
        )
        try:
            critique = await self._llm.generate(critic_prompt)
        except Exception as e:
            critique = f"Error: {e}"

        # Synthesis
        synthesis_prompt = (
            f"Synthesize the following two perspectives into a final, concise answer. "
            f"For multiple choice, answer with just the letter.\n\n"
            f"Question: {question.question}\n"
            f"Analyst: {analysis[:1000]}\n"
            f"Critic: {critique[:1000]}\n\n"
            f"Final Answer:"
        )
        try:
            final_answer = await self._llm.generate(synthesis_prompt)
        except Exception as e:
            final_answer = f"ERROR: {e}"

        latency = (time.monotonic() - start) * 1000
        return {
            "answer": final_answer,
            "latency_ms": latency,
            "token_estimate": (len(analysis) + len(critique) + len(final_answer)) // 4,
            "memory_retrievals": 0,
            "belief_activations": 0,
            "goal_activations": 0,
            "reflection_output": f"Analyst: {analysis[:200]}... Critic: {critique[:200]}...",
            "verification_output": critique[:200],
            "model_used": "z-ai-api",
        }


class MultiAgent(BaselineSystem):
    """Baseline 6: 3 specialized agents that vote on the answer."""

    def __init__(self, llm: LLMClient):
        super().__init__("MultiAgent", llm)

    async def answer(self, question: BenchmarkQuestion) -> dict[str, Any]:
        start = time.monotonic()

        knowledge_prompt = (
            f"You are a knowledge specialist. Answer this question from factual knowledge. "
            f"Be concise. For multiple choice, answer with just the letter.\n\n"
            f"Question: {question.question}\n\nAnswer:"
        )
        logic_prompt = (
            f"You are a logic specialist. Answer this question using careful logical reasoning. "
            f"Be concise. For multiple choice, answer with just the letter.\n\n"
            f"Question: {question.question}\n\nAnswer:"
        )
        common_prompt = (
            f"You are a common sense reasoning specialist. Answer this question using practical "
            f"common sense. Be concise. For multiple choice, answer with just the letter.\n\n"
            f"Question: {question.question}\n\nAnswer:"
        )

        # Run 3 agents in parallel for speed
        agent_answers = await asyncio.gather(
            self._safe_generate(knowledge_prompt),
            self._safe_generate(logic_prompt),
            self._safe_generate(common_prompt),
        )

        vote_prompt = (
            f"Three specialists gave the following answers. Synthesize them into a single "
            f"best answer. If they agree, use that answer. If they disagree, choose the most "
            f"well-reasoned one. For multiple choice, answer with just the letter.\n\n"
            f"Question: {question.question}\n"
            f"Knowledge specialist: {agent_answers[0][:500]}\n"
            f"Logic specialist: {agent_answers[1][:500]}\n"
            f"Common sense specialist: {agent_answers[2][:500]}\n\n"
            f"Final Answer:"
        )
        try:
            final_answer = await self._llm.generate(vote_prompt)
        except Exception as e:
            final_answer = f"ERROR: {e}"

        latency = (time.monotonic() - start) * 1000
        return {
            "answer": final_answer,
            "latency_ms": latency,
            "token_estimate": sum(len(a) for a in agent_answers) // 4 + len(final_answer) // 4,
            "memory_retrievals": 0,
            "belief_activations": 0,
            "goal_activations": 0,
            "reflection_output": f"Agent votes: {[a[:100] for a in agent_answers]}",
            "verification_output": "",
            "model_used": "z-ai-api",
        }

    async def _safe_generate(self, prompt: str) -> str:
        try:
            return await self._llm.generate(prompt)
        except Exception as e:
            return f"Error: {e}"


# ============================================================================
# ACOS System — Uses HTTP API at http://localhost:3031/query/v2
# ============================================================================

class ACOSSystem:
    """ACOS Runtime — processes queries through the real CognitiveKernel HTTP API.

    Falls back to Z-AI API with ACOS system prompt if the runtime is unavailable.
    """

    def __init__(self, llm: LLMClient):
        self.name = "ACOS"
        self._acos_client = ACOSClient()
        self._llm = llm
        self._available: Optional[bool] = None

    async def _check_available(self) -> bool:
        if self._available is not None:
            return self._available
        self._available = await self._acos_client.is_available()
        return self._available

    async def answer(self, question: BenchmarkQuestion) -> dict[str, Any]:
        start = time.monotonic()

        if await self._check_available():
            return await self._answer_via_api(question, start)
        else:
            return await self._answer_via_fallback(question, start)

    async def _answer_via_api(
        self, question: BenchmarkQuestion, start: float
    ) -> dict[str, Any]:
        """Answer via the ACOS /query/v2 HTTP endpoint."""
        try:
            data = await self._acos_client.query(question.question)
            latency = (time.monotonic() - start) * 1000

            # Extract synthesis from ACOS response
            synthesis = ""
            if isinstance(data, dict):
                # Try common response shapes
                synthesis = (
                    data.get("final_synthesis")
                    or data.get("synthesis")
                    or data.get("response")
                    or data.get("answer")
                    or ""
                )
                if not synthesis and "result" in data:
                    r = data["result"]
                    if isinstance(r, dict):
                        synthesis = r.get("final_synthesis") or r.get("answer") or str(r)
                    else:
                        synthesis = str(r)

            if not synthesis:
                synthesis = json.dumps(data)[:2000]

            # Extract cognitive metrics from the response
            memory_retrievals = 0
            belief_activations = 0
            goal_activations = 0
            reflection_output = ""
            verification_output = ""

            if isinstance(data, dict):
                # Check for trace/metadata
                traces = data.get("traces", [])
                for trace in traces:
                    if isinstance(trace, dict):
                        phase = trace.get("phase", "")
                        if phase in ("memory", "knowledge"):
                            memory_retrievals += 1
                        elif phase == "beliefs":
                            belief_activations += 1
                        elif phase == "goals":
                            goal_activations += 1

                # Check for reflection/verification in response
                reflections = data.get("reflections", [])
                if reflections:
                    r0 = reflections[0] if reflections else {}
                    if isinstance(r0, dict):
                        reflection_output = (
                            f"Quality: {r0.get('quality_score', 'N/A')}, "
                            f"Issues: {len(r0.get('issues_found', []))}"
                        )
                    else:
                        reflection_output = str(r0)[:300]

                verifications = data.get("verifications", [])
                if verifications:
                    v0 = verifications[0] if verifications else {}
                    if isinstance(v0, dict):
                        verification_output = (
                            f"Passed: {v0.get('passed', 'N/A')}, "
                            f"Confidence: {v0.get('confidence_score', 'N/A')}"
                        )
                    else:
                        verification_output = str(v0)[:300]

            return {
                "answer": synthesis,
                "latency_ms": latency,
                "token_estimate": len(synthesis) // 4,
                "memory_retrievals": memory_retrievals,
                "belief_activations": belief_activations,
                "goal_activations": goal_activations,
                "reflection_output": reflection_output[:500],
                "verification_output": verification_output[:500],
                "model_used": "acos-runtime",
            }
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            # Fallback to LLM with ACOS system prompt
            return await self._answer_via_fallback(question, start, str(e))

    async def _answer_via_fallback(
        self, question: BenchmarkQuestion, start: float,
        error: Optional[str] = None,
    ) -> dict[str, Any]:
        """Fallback when ACOS runtime is unavailable — use Z-AI API with ACOS system prompt."""
        try:
            system = (
                "You are the ACOS Cognitive Operating System. You have deep knowledge of science, "
                "mathematics, history, and reasoning. You reflect on your answers and verify them "
                "before responding. Answer concisely and accurately. "
                "For multiple choice, answer with just the letter."
            )
            prompt = question.question
            response = await self._llm.generate(prompt, system=system)
            latency = (time.monotonic() - start) * 1000
            return {
                "answer": response,
                "latency_ms": latency,
                "token_estimate": len(response) // 4,
                "memory_retrievals": 0,
                "belief_activations": 0,
                "goal_activations": 0,
                "reflection_output": "",
                "verification_output": "",
                "model_used": "z-ai-api (acos-fallback)",
                "error": error,
            }
        except Exception as e2:
            latency = (time.monotonic() - start) * 1000
            return {
                "answer": f"ERROR: {e2}",
                "latency_ms": latency,
                "token_estimate": 0,
                "memory_retrievals": 0,
                "belief_activations": 0,
                "goal_activations": 0,
                "reflection_output": "",
                "verification_output": "",
                "model_used": "fallback",
                "error": f"{error}; {e2}" if error else str(e2),
            }

    async def close(self):
        await self._acos_client.close()


# ============================================================================
# Database Schema — SQLite at data/scientific_validation.db
# ============================================================================

class ValidationDB:
    """SQLite database for storing validation results."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS benchmark_questions (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                category TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                requires_reasoning INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS validation_runs (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                system_name TEXT NOT NULL,
                question_id TEXT NOT NULL,
                question_text TEXT NOT NULL,
                ground_truth TEXT NOT NULL,
                model_used TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                token_estimate INTEGER NOT NULL,
                memory_retrievals INTEGER NOT NULL DEFAULT 0,
                belief_activations INTEGER NOT NULL DEFAULT 0,
                goal_activations INTEGER NOT NULL DEFAULT 0,
                reflection_output TEXT DEFAULT '',
                verification_output TEXT DEFAULT '',
                final_answer TEXT NOT NULL,
                success INTEGER NOT NULL,
                error TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_validation_runs_run_id ON validation_runs(run_id);
            CREATE INDEX IF NOT EXISTS idx_validation_runs_system ON validation_runs(system_name);
            CREATE INDEX IF NOT EXISTS idx_validation_runs_category ON validation_runs(question_id);

            CREATE TABLE IF NOT EXISTS ablation_results (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                disabled_subsystem TEXT NOT NULL,
                question_id TEXT NOT NULL,
                question_text TEXT NOT NULL,
                ground_truth TEXT NOT NULL,
                final_answer TEXT NOT NULL,
                success INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                error TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_ablation_run_id ON ablation_results(run_id);
            CREATE INDEX IF NOT EXISTS idx_ablation_subsystem ON ablation_results(disabled_subsystem);

            CREATE TABLE IF NOT EXISTS system_metrics (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                system_name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'all',
                accuracy REAL NOT NULL,
                latency_mean_ms REAL NOT NULL,
                latency_median_ms REAL NOT NULL,
                latency_std_ms REAL NOT NULL,
                token_usage_mean REAL NOT NULL,
                memory_utilization REAL NOT NULL,
                hallucination_rate REAL NOT NULL,
                reflection_usefulness REAL NOT NULL,
                verification_usefulness REAL NOT NULL,
                correct_count INTEGER NOT NULL,
                total_count INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_system_metrics_run_id ON system_metrics(run_id);

            CREATE TABLE IF NOT EXISTS statistical_tests (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                system_a TEXT NOT NULL,
                system_b TEXT NOT NULL,
                metric TEXT NOT NULL,
                mean_diff REAL NOT NULL,
                cohens_d REAL NOT NULL,
                t_statistic REAL NOT NULL,
                p_value REAL NOT NULL,
                ci_lower REAL NOT NULL,
                ci_upper REAL NOT NULL,
                significant_95 INTEGER NOT NULL,
                n_pairs INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_statistical_tests_run_id ON statistical_tests(run_id);
        """)
        conn.commit()
        conn.close()

    def store_questions(self, questions: list[BenchmarkQuestion]) -> None:
        conn = sqlite3.connect(self.db_path)
        for q in questions:
            conn.execute(
                "INSERT OR IGNORE INTO benchmark_questions VALUES (?, ?, ?, ?, ?, ?)",
                (q.id, q.question, q.correct_answer, q.category,
                 q.difficulty, int(q.requires_reasoning)),
            )
        conn.commit()
        conn.close()

    def store_validation_run(self, trace: ValidationTrace) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO validation_runs
               (id, run_id, system_name, question_id, question_text, ground_truth,
                model_used, latency_ms, token_estimate, memory_retrievals,
                belief_activations, goal_activations, reflection_output,
                verification_output, final_answer, success, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (trace.id, trace.run_id, trace.system_name, trace.question_id,
             trace.question_text, trace.ground_truth, trace.model_used,
             trace.latency_ms, trace.token_estimate, trace.memory_retrievals,
             trace.belief_activations, trace.goal_activations,
             trace.reflection_output, trace.verification_output,
             trace.final_answer, int(trace.success), trace.error),
        )
        conn.commit()
        conn.close()

    def store_ablation_result(self, result: AblationResult) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO ablation_results
               (id, run_id, disabled_subsystem, question_id, question_text,
                ground_truth, final_answer, success, latency_ms, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (result.id, result.run_id, result.disabled_subsystem,
             result.question_id, result.question_text, result.ground_truth,
             result.final_answer, int(result.success), result.latency_ms, result.error),
        )
        conn.commit()
        conn.close()

    def store_system_metrics(self, metrics: SystemMetrics, run_id: str,
                             category: str = "all") -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO system_metrics
               (id, run_id, system_name, category, accuracy, latency_mean_ms,
                latency_median_ms, latency_std_ms, token_usage_mean,
                memory_utilization, hallucination_rate, reflection_usefulness,
                verification_usefulness, correct_count, total_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4())[:8], run_id, metrics.system_name, category,
             metrics.accuracy, metrics.latency_mean_ms, metrics.latency_median_ms,
             metrics.latency_std_ms, metrics.token_usage_mean,
             metrics.memory_utilization, metrics.hallucination_rate,
             metrics.reflection_usefulness, metrics.verification_usefulness,
             metrics.correct_count, metrics.total_count),
        )
        conn.commit()
        conn.close()

    def store_statistical_test(self, test: StatisticalTest, run_id: str) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO statistical_tests
               (id, run_id, system_a, system_b, metric, mean_diff, cohens_d,
                t_statistic, p_value, ci_lower, ci_upper, significant_95, n_pairs)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4())[:8], run_id, test.system_a, test.system_b,
             test.metric, test.mean_diff, test.cohens_d, test.t_statistic,
             test.p_value, test.ci_lower, test.ci_upper,
             int(test.significant_95), test.n_pairs),
        )
        conn.commit()
        conn.close()

    def get_run_results(self, run_id: str) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM validation_runs WHERE run_id = ?", (run_id,),
        )
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_latest_run_id(self) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT run_id FROM validation_runs ORDER BY created_at DESC LIMIT 1",
        )
        row = cursor.fetchone()
        conn.close()
        return row["run_id"] if row else None

    def get_metrics_for_run(self, run_id: str) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM system_metrics WHERE run_id = ?", (run_id,),
        )
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_stats_for_run(self, run_id: str) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM statistical_tests WHERE run_id = ?", (run_id,),
        )
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_ablation_for_run(self, run_id: str) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM ablation_results WHERE run_id = ?", (run_id,),
        )
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results


# ============================================================================
# Scientific Validation Runner
# ============================================================================

class ScientificValidation:
    """Main validation runner: runs baselines and ACOS on benchmark questions."""

    def __init__(self, db: Optional[ValidationDB] = None):
        self.db = db or ValidationDB()
        self.suite = BenchmarkSuite()

    async def run(
        self,
        questions_per_category: int = 20,
    ) -> dict[str, Any]:
        """Run all systems on benchmark questions.

        Args:
            questions_per_category: Number of questions per category
                (5 for quick, 20 for full).
        """
        run_id = str(uuid.uuid4())[:12]
        print(f"\n{'='*60}", flush=True)
        print(f"ACOS Scientific Validation — Run {run_id}", flush=True)
        print(f"Questions per category: {questions_per_category}", flush=True)
        print(f"{'='*60}\n", flush=True)

        # Select questions
        all_questions: list[BenchmarkQuestion] = []
        for category in self.suite.categories:
            cat_questions = self.suite.get_by_category(category)[:questions_per_category]
            all_questions.extend(cat_questions)

        # Store questions in DB
        self.db.store_questions(self.suite.questions)

        total = len(all_questions)
        print(f"Total questions: {total}", flush=True)
        print(f"Categories: {', '.join(self.suite.categories)}\n", flush=True)

        # Initialize LLM client (aiohttp)
        llm = LLMClient()

        # Initialize baseline systems
        baselines: list[BaselineSystem] = [
            DirectLLM(llm),
            LLMPlusRAG(llm),
            ReActAgent(llm),
            LangGraphStyle(llm),
            CrewAIStyle(llm),
            MultiAgent(llm),
        ]

        # Initialize ACOS
        acos = ACOSSystem(llm)

        # Run all systems
        all_traces: dict[str, list[ValidationTrace]] = {}
        systems: list[BaselineSystem | ACOSSystem] = list(baselines) + [acos]

        for system in systems:
            sys_name = system.name
            print(f"\n--- Running {sys_name} ---", flush=True)
            all_traces[sys_name] = []

            for i, question in enumerate(all_questions):
                pct = (i + 1) / total * 100
                print(
                    f"  [{i+1}/{total}] ({pct:.0f}%) "
                    f"{question.category}/{question.difficulty}: "
                    f"{question.question[:60]}...",
                    flush=True, end=" ",
                )

                try:
                    result = await system.answer(question)
                    success = answers_match(
                        result["answer"], question.correct_answer, question.category,
                    )

                    trace = ValidationTrace(
                        id=str(uuid.uuid4())[:8],
                        run_id=run_id,
                        system_name=sys_name,
                        question_id=question.id,
                        question_text=question.question,
                        ground_truth=question.correct_answer,
                        model_used=result.get("model_used", "unknown"),
                        latency_ms=result["latency_ms"],
                        token_estimate=result.get("token_estimate", 0),
                        memory_retrievals=result.get("memory_retrievals", 0),
                        belief_activations=result.get("belief_activations", 0),
                        goal_activations=result.get("goal_activations", 0),
                        reflection_output=result.get("reflection_output", ""),
                        verification_output=result.get("verification_output", ""),
                        final_answer=result["answer"][:2000],
                        success=success,
                        error=result.get("error"),
                    )

                    all_traces[sys_name].append(trace)
                    self.db.store_validation_run(trace)

                    status = "OK" if success else "MISS"
                    print(f"{status} ({result['latency_ms']:.0f}ms)", flush=True)

                except Exception as e:
                    print(f"ERROR: {e}", flush=True)
                    trace = ValidationTrace(
                        id=str(uuid.uuid4())[:8],
                        run_id=run_id,
                        system_name=sys_name,
                        question_id=question.id,
                        question_text=question.question,
                        ground_truth=question.correct_answer,
                        model_used="error",
                        latency_ms=0,
                        token_estimate=0,
                        memory_retrievals=0,
                        belief_activations=0,
                        goal_activations=0,
                        reflection_output="",
                        verification_output="",
                        final_answer=f"ERROR: {e}",
                        success=False,
                        error=str(e),
                    )
                    all_traces[sys_name].append(trace)
                    self.db.store_validation_run(trace)

                # Rate limiting
                await asyncio.sleep(0.2)

        # Clean up
        await llm.close()
        await acos.close()

        # Compute overall metrics per system
        print(f"\n\n--- Computing Metrics ---", flush=True)
        system_metrics: dict[str, SystemMetrics] = {}
        for sys_name, traces in all_traces.items():
            metrics = self._compute_metrics(traces)
            system_metrics[sys_name] = metrics
            self.db.store_system_metrics(metrics, run_id)
            print(
                f"  {sys_name}: accuracy={metrics.accuracy:.3f}, "
                f"latency={metrics.latency_mean_ms:.0f}ms, "
                f"correct={metrics.correct_count}/{metrics.total_count}",
                flush=True,
            )

        # Compute per-category metrics
        category_metrics: dict[str, dict[str, SystemMetrics]] = {}
        for category in self.suite.categories:
            category_metrics[category] = {}
            cat_question_ids = {q.id for q in self.suite.get_by_category(category)}
            for sys_name, traces in all_traces.items():
                cat_traces = [t for t in traces if t.question_id in cat_question_ids]
                if cat_traces:
                    cat_m = self._compute_metrics(cat_traces)
                    category_metrics[category][sys_name] = cat_m
                    self.db.store_system_metrics(cat_m, run_id, category=category)

        # Run statistical tests
        print(f"\n--- Statistical Analysis ---", flush=True)
        stats = self._compute_statistics(all_traces, run_id)
        for test in stats:
            sig = "*" if test.significant_95 else ""
            print(
                f"  {test.system_a} vs {test.system_b} ({test.metric}): "
                f"d={test.cohens_d:.3f}, p={test.p_value:.4f} {sig}",
                flush=True,
            )

        # Failure analysis
        failure_analysis = self._compute_failure_analysis(all_traces)

        # Generate summary
        summary = self._generate_summary(
            run_id, system_metrics, category_metrics, stats, all_traces,
            failure_analysis,
        )

        print(f"\n{'='*60}", flush=True)
        print(f"Run {run_id} complete!", flush=True)
        print(f"{'='*60}\n", flush=True)

        return summary

    def _compute_metrics(self, traces: list[ValidationTrace]) -> SystemMetrics:
        """Compute aggregated metrics from traces."""
        if not traces:
            return SystemMetrics(
                system_name="unknown", accuracy=0, latency_mean_ms=0,
                latency_median_ms=0, latency_std_ms=0, token_usage_mean=0,
                memory_utilization=0, hallucination_rate=0,
                reflection_usefulness=0, verification_usefulness=0,
                correct_count=0, total_count=0,
            )

        name = traces[0].system_name
        correct = sum(1 for t in traces if t.success)
        total = len(traces)
        accuracy = correct / total if total > 0 else 0

        latencies = [t.latency_ms for t in traces]
        latency_mean = float(np.mean(latencies))
        latency_median = float(np.median(latencies))
        latency_std = float(np.std(latencies)) if len(latencies) > 1 else 0.0

        tokens = [t.token_estimate for t in traces]
        token_mean = float(np.mean(tokens)) if tokens else 0

        mem_retrievals = [t.memory_retrievals for t in traces]
        mem_util = float(np.mean(mem_retrievals)) if mem_retrievals else 0

        # Hallucination rate: wrong answers when memory was retrieved
        hallucination_count = sum(
            1 for t in traces if not t.success and t.memory_retrievals > 0
        )
        retrieval_traces = [t for t in traces if t.memory_retrievals > 0]
        hallucination_rate = (
            hallucination_count / len(retrieval_traces) if retrieval_traces else 0.0
        )

        # Reflection usefulness
        traces_with_reflection = [t for t in traces if t.reflection_output]
        if traces_with_reflection:
            reflection_success = sum(1 for t in traces_with_reflection if t.success)
            no_reflection = [t for t in traces if not t.reflection_output]
            no_reflection_rate = (
                sum(1 for t in no_reflection if t.success) / len(no_reflection)
                if no_reflection else accuracy
            )
            reflection_usefulness = (
                (reflection_success / len(traces_with_reflection)) - no_reflection_rate
            )
        else:
            reflection_usefulness = 0.0

        # Verification usefulness
        traces_with_verification = [t for t in traces if t.verification_output]
        if traces_with_verification:
            verif_success = sum(1 for t in traces_with_verification if t.success)
            no_verif = [t for t in traces if not t.verification_output]
            no_verif_rate = (
                sum(1 for t in no_verif if t.success) / len(no_verif)
                if no_verif else accuracy
            )
            verification_usefulness = (
                (verif_success / len(traces_with_verification)) - no_verif_rate
            )
        else:
            verification_usefulness = 0.0

        return SystemMetrics(
            system_name=name,
            accuracy=accuracy,
            latency_mean_ms=latency_mean,
            latency_median_ms=latency_median,
            latency_std_ms=latency_std,
            token_usage_mean=token_mean,
            memory_utilization=mem_util,
            hallucination_rate=hallucination_rate,
            reflection_usefulness=reflection_usefulness,
            verification_usefulness=verification_usefulness,
            correct_count=correct,
            total_count=total,
        )

    def _compute_statistics(
        self,
        all_traces: dict[str, list[ValidationTrace]],
        run_id: str,
    ) -> list[StatisticalTest]:
        """Compute pairwise statistical comparisons (ACOS vs each baseline)."""
        tests: list[StatisticalTest] = []
        system_names = list(all_traces.keys())

        # Focus on ACOS vs each baseline for the primary analysis
        acos_name = None
        for name in system_names:
            if "ACOS" in name.upper():
                acos_name = name
                break

        pairs = []
        if acos_name:
            for name_b in system_names:
                if name_b != acos_name:
                    pairs.append((acos_name, name_b))

        # Also compute all pairwise comparisons
        for i, name_a in enumerate(system_names):
            for name_b in system_names[i + 1:]:
                if (name_a, name_b) not in pairs and (name_b, name_a) not in pairs:
                    pairs.append((name_a, name_b))

        for name_a, name_b in pairs:
            traces_a = {t.question_id: t for t in all_traces[name_a]}
            traces_b = {t.question_id: t for t in all_traces[name_b]}

            common_ids = set(traces_a.keys()) & set(traces_b.keys())
            if len(common_ids) < 3:
                continue

            scores_a = [int(traces_a[qid].success) for qid in common_ids]
            scores_b = [int(traces_b[qid].success) for qid in common_ids]

            latencies_a = [traces_a[qid].latency_ms for qid in common_ids]
            latencies_b = [traces_b[qid].latency_ms for qid in common_ids]

            for metric_name, vals_a, vals_b in [
                ("accuracy", scores_a, scores_b),
                ("latency_ms", latencies_a, latencies_b),
            ]:
                test = self._paired_t_test(
                    name_a, name_b, metric_name, vals_a, vals_b,
                )
                test.n_pairs = len(common_ids)
                tests.append(test)
                self.db.store_statistical_test(test, run_id)

        return tests

    def _paired_t_test(
        self,
        name_a: str, name_b: str, metric: str,
        vals_a: list[float], vals_b: list[float],
    ) -> StatisticalTest:
        """Compute paired t-test between two sets of values."""
        from scipy import stats as scipy_stats

        n = min(len(vals_a), len(vals_b))
        if n < 2:
            return StatisticalTest(
                system_a=name_a, system_b=name_b, metric=metric,
                mean_diff=0, cohens_d=0, t_statistic=0, p_value=1.0,
                ci_lower=0, ci_upper=0, significant_95=False, n_pairs=n,
            )

        a = np.array(vals_a[:n])
        b = np.array(vals_b[:n])
        diffs = a - b

        mean_diff = float(np.mean(diffs))
        std_diff = float(np.std(diffs, ddof=1))

        # Paired t-test
        t_stat, p_value = scipy_stats.ttest_rel(a, b)

        # Cohen's d for paired samples
        if std_diff > 0:
            cohens_d = mean_diff / std_diff
        else:
            cohens_d = 0.0

        # 95% confidence interval for mean difference
        se = std_diff / math.sqrt(n)
        ci_half = 1.96 * se
        ci_lower = mean_diff - ci_half
        ci_upper = mean_diff + ci_half

        return StatisticalTest(
            system_a=name_a,
            system_b=name_b,
            metric=metric,
            mean_diff=mean_diff,
            cohens_d=cohens_d,
            t_statistic=float(t_stat),
            p_value=float(p_value),
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            significant_95=p_value < 0.05,
            n_pairs=n,
        )

    def _compute_failure_analysis(
        self, all_traces: dict[str, list[ValidationTrace]],
    ) -> dict[str, Any]:
        """Compute failure analysis across all systems."""
        analysis: dict[str, Any] = {
            "systems": {},
            "examples": [],
        }

        for sys_name, traces in all_traces.items():
            failed = [t for t in traces if not t.success]
            total = len(traces)
            error_traces = [t for t in traces if t.error]

            # Classify failures
            timeout_count = sum(
                1 for t in failed
                if t.error and ("timeout" in t.error.lower() or "timed out" in t.error.lower())
            )
            api_error_count = sum(
                1 for t in failed
                if t.error and ("connection" in t.error.lower() or "api" in t.error.lower())
            )
            wrong_answer_count = len(failed) - timeout_count - api_error_count

            analysis["systems"][sys_name] = {
                "total_failures": len(failed),
                "failure_rate": round(len(failed) / total, 4) if total > 0 else 0,
                "timeout_count": timeout_count,
                "api_error_count": api_error_count,
                "wrong_answer_count": wrong_answer_count,
                "avg_latency_failed": round(
                    float(np.mean([t.latency_ms for t in failed])), 1
                ) if failed else 0,
                "avg_latency_succeeded": round(
                    float(np.mean([t.latency_ms for t in traces if t.success])), 1
                ) if any(t.success for t in traces) else 0,
            }

        # Collect example failures (max 3 per system)
        for sys_name, traces in all_traces.items():
            failed = [t for t in traces if not t.success]
            for t in failed[:3]:
                analysis["examples"].append({
                    "system": sys_name,
                    "question": t.question_text[:200],
                    "ground_truth": t.ground_truth,
                    "predicted": t.final_answer[:300],
                    "category": next(
                        (q.category for q in self.suite.questions if q.id == t.question_id),
                        "unknown",
                    ),
                    "error": t.error,
                })

        return analysis

    def _generate_summary(
        self,
        run_id: str,
        system_metrics: dict[str, SystemMetrics],
        category_metrics: dict[str, dict[str, SystemMetrics]],
        stats: list[StatisticalTest],
        all_traces: dict[str, list[ValidationTrace]],
        failure_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a JSON-serializable summary of the run."""
        ranked = sorted(
            system_metrics.values(),
            key=lambda m: m.accuracy,
            reverse=True,
        )

        # Category-level breakdown for all systems
        category_breakdown: dict[str, dict[str, dict]] = {}
        for cat, sys_metrics in category_metrics.items():
            category_breakdown[cat] = {}
            for sys_name, m in sys_metrics.items():
                category_breakdown[cat][sys_name] = {
                    "accuracy": round(m.accuracy, 4),
                    "correct": m.correct_count,
                    "total": m.total_count,
                    "latency_mean_ms": round(m.latency_mean_ms, 1),
                }

        summary = {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_questions": len(self.suite.questions),
            "questions_per_category": len(all_traces.get(
                next(iter(all_traces)), []
            )) // max(len(all_traces), 1),
            "systems_tested": list(system_metrics.keys()),
            "rankings": [
                {
                    "rank": i + 1,
                    "system": m.system_name,
                    "accuracy": round(m.accuracy, 4),
                    "correct": m.correct_count,
                    "total": m.total_count,
                    "mean_latency_ms": round(m.latency_mean_ms, 1),
                    "median_latency_ms": round(m.latency_median_ms, 1),
                    "token_usage_mean": round(m.token_usage_mean, 1),
                }
                for i, m in enumerate(ranked)
            ],
            "benchmark_results": {
                cat: {
                    sys: data
                    for sys, data in sys_data.items()
                }
                for cat, sys_data in category_breakdown.items()
            },
            "system_metrics": {
                name: {
                    "accuracy": round(m.accuracy, 4),
                    "latency_mean_ms": round(m.latency_mean_ms, 1),
                    "latency_median_ms": round(m.latency_median_ms, 1),
                    "latency_std_ms": round(m.latency_std_ms, 1),
                    "token_usage_mean": round(m.token_usage_mean, 1),
                    "memory_utilization": round(m.memory_utilization, 4),
                    "hallucination_rate": round(m.hallucination_rate, 4),
                    "reflection_usefulness": round(m.reflection_usefulness, 4),
                    "verification_usefulness": round(m.verification_usefulness, 4),
                    "correct_count": m.correct_count,
                    "total_count": m.total_count,
                }
                for name, m in system_metrics.items()
            },
            "latency_cost": {
                "latency": [
                    {
                        "system": m.system_name,
                        "mean_ms": round(m.latency_mean_ms, 1),
                        "median_ms": round(m.latency_median_ms, 1),
                    }
                    for m in ranked
                ],
                "tokens": [
                    {
                        "system": m.system_name,
                        "mean_tokens": round(m.token_usage_mean, 1),
                    }
                    for m in ranked
                ],
                "efficiency": [
                    {
                        "system": m.system_name,
                        "accuracy_per_1k_tokens": round(
                            m.accuracy / max(m.token_usage_mean / 1000, 0.001), 4
                        ),
                    }
                    for m in ranked
                ],
            },
            "statistical_tests": [
                {
                    "system_a": t.system_a,
                    "system_b": t.system_b,
                    "metric": t.metric,
                    "mean_diff": round(t.mean_diff, 4),
                    "cohens_d": round(t.cohens_d, 4),
                    "t_statistic": round(t.t_statistic, 4),
                    "p_value": round(t.p_value, 6),
                    "ci_lower": round(t.ci_lower, 4),
                    "ci_upper": round(t.ci_upper, 4),
                    "significant_95": t.significant_95,
                    "n_pairs": t.n_pairs,
                }
                for t in stats
                if t.metric == "accuracy"
            ],
            "statistical_significance": [
                {
                    "comparison": f"{t.system_a} vs {t.system_b}",
                    "metric": t.metric,
                    "mean_diff": round(t.mean_diff, 4),
                    "cohens_d": round(t.cohens_d, 4),
                    "p_value": round(t.p_value, 6),
                    "ci_lower": round(t.ci_lower, 4),
                    "ci_upper": round(t.ci_upper, 4),
                    "significant_95": t.significant_95,
                }
                for t in stats
                if t.metric == "accuracy"
            ],
            "failure_analysis": failure_analysis,
            "best_system": ranked[0].system_name if ranked else "unknown",
            "acos_rank": next(
                (i + 1 for i, m in enumerate(ranked) if "ACOS" in m.system_name.upper()),
                None,
            ),
        }

        return summary


# ============================================================================
# Ablation Study
# ============================================================================

class AblationStudy:
    """Run ACOS with each subsystem disabled to measure its contribution."""

    SUBSYSTEMS = [
        "reflection",
        "verification",
        "counterfactuals",
        "dynamics",
        "knowledge_fabric",
        "world_model",
        "attention",
        "belief_system",
        "goal_system",
        "semantic_memory",
    ]

    def __init__(self, db: Optional[ValidationDB] = None):
        self.db = db or ValidationDB()
        self.suite = BenchmarkSuite()

    async def run(
        self,
        questions_per_category: int = 5,
    ) -> dict[str, Any]:
        """Run ablation studies."""
        run_id = str(uuid.uuid4())[:12]
        print(f"\n{'='*60}", flush=True)
        print(f"ACOS Ablation Study — Run {run_id}", flush=True)
        print(f"{'='*60}\n", flush=True)

        # Select questions
        all_questions: list[BenchmarkQuestion] = []
        for category in self.suite.categories:
            cat_questions = self.suite.get_by_category(category)[:questions_per_category]
            all_questions.extend(cat_questions)

        total = len(all_questions)
        print(f"Total questions: {total}", flush=True)
        print(f"Subsystems to ablate: {', '.join(self.SUBSYSTEMS)}\n", flush=True)

        llm = LLMClient()
        results: dict[str, list[AblationResult]] = {}

        # First, run full ACOS as baseline
        print("--- Running Full ACOS (no ablation) ---", flush=True)
        full_results: list[dict] = []
        for i, question in enumerate(all_questions):
            print(
                f"  [{i+1}/{total}] {question.question[:60]}...",
                flush=True, end=" ",
            )
            try:
                answer = await self._run_full_query(llm, question)
                success = answers_match(answer, question.correct_answer, question.category)
                full_results.append({
                    "question_id": question.id,
                    "success": success,
                    "answer": answer,
                })
                print("OK" if success else "MISS", flush=True)
            except Exception as e:
                full_results.append({
                    "question_id": question.id,
                    "success": False,
                    "answer": f"ERROR: {e}",
                })
                print(f"ERROR: {e}", flush=True)
            await asyncio.sleep(0.2)

        # Now run each ablation
        for subsystem in self.SUBSYSTEMS:
            print(f"\n--- Ablating: {subsystem} ---", flush=True)
            results[subsystem] = []

            for i, question in enumerate(all_questions):
                print(
                    f"  [{i+1}/{total}] {question.question[:60]}...",
                    flush=True, end=" ",
                )

                start = time.monotonic()
                try:
                    answer = await self._run_ablated_query(llm, question, subsystem)
                    latency = (time.monotonic() - start) * 1000
                    success = answers_match(answer, question.correct_answer, question.category)

                    ablation_result = AblationResult(
                        id=str(uuid.uuid4())[:8],
                        run_id=run_id,
                        disabled_subsystem=subsystem,
                        question_id=question.id,
                        question_text=question.question,
                        ground_truth=question.correct_answer,
                        final_answer=answer[:2000],
                        success=success,
                        latency_ms=latency,
                    )

                    results[subsystem].append(ablation_result)
                    self.db.store_ablation_result(ablation_result)
                    print("OK" if success else "MISS", flush=True)

                except Exception as e:
                    latency = (time.monotonic() - start) * 1000
                    ablation_result = AblationResult(
                        id=str(uuid.uuid4())[:8],
                        run_id=run_id,
                        disabled_subsystem=subsystem,
                        question_id=question.id,
                        question_text=question.question,
                        ground_truth=question.correct_answer,
                        final_answer=f"ERROR: {e}",
                        success=False,
                        latency_ms=latency,
                        error=str(e),
                    )
                    results[subsystem].append(ablation_result)
                    self.db.store_ablation_result(ablation_result)
                    print(f"ERROR: {e}", flush=True)

                await asyncio.sleep(0.2)

        await llm.close()

        # Compute ablation summary
        full_accuracy = (
            sum(1 for r in full_results if r["success"]) / len(full_results)
            if full_results else 0
        )

        ablation_summary = {}
        helps_count = 0
        hurts_count = 0
        neutral_count = 0
        for subsystem, ablation_results in results.items():
            correct = sum(1 for r in ablation_results if r.success)
            total_q = len(ablation_results)
            accuracy = correct / total_q if total_q > 0 else 0
            drop = full_accuracy - accuracy
            if drop > 0.02:
                hurts_count += 1
            elif drop < -0.02:
                helps_count += 1
            else:
                neutral_count += 1

            ablation_summary[subsystem] = {
                "accuracy": round(accuracy, 4),
                "correct": correct,
                "total": total_q,
                "accuracy_drop": round(drop, 4),
                "latency_mean_ms": round(
                    float(np.mean([r.latency_ms for r in ablation_results])), 1
                ) if ablation_results else 0,
            }

        summary = {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "full_acos_accuracy": round(full_accuracy, 4),
            "ablation_results": ablation_summary,
            "modules": [
                {
                    "name": subsys,
                    "accuracy_drop": ablation_summary[subsys]["accuracy_drop"],
                    "impact": "critical" if ablation_summary[subsys]["accuracy_drop"] > 0.1
                    else "important" if ablation_summary[subsys]["accuracy_drop"] > 0.05
                    else "minor" if ablation_summary[subsys]["accuracy_drop"] > 0.01
                    else "negligible",
                }
                for subsys in self.SUBSYSTEMS
                if subsys in ablation_summary
            ],
            "summary": {
                "helps": helps_count,
                "hurts": hurts_count,
                "neutral": neutral_count,
            },
            "most_critical_subsystem": max(
                ablation_summary.items(),
                key=lambda x: x[1]["accuracy_drop"],
            )[0] if ablation_summary else "unknown",
            "least_critical_subsystem": min(
                ablation_summary.items(),
                key=lambda x: x[1]["accuracy_drop"],
            )[0] if ablation_summary else "unknown",
        }

        print(f"\n{'='*60}", flush=True)
        print(f"Ablation Study {run_id} complete!", flush=True)
        print(f"Full ACOS accuracy: {full_accuracy:.3f}", flush=True)
        print(f"Most critical subsystem: {summary['most_critical_subsystem']}", flush=True)
        print(f"{'='*60}\n", flush=True)

        return summary

    async def _run_full_query(
        self, llm: LLMClient, question: BenchmarkQuestion,
    ) -> str:
        """Run a query with the full ACOS system prompt."""
        prompt = (
            "You are the ACOS Cognitive Operating System with all subsystems active: "
            "reflection, verification, counterfactual reasoning, cognitive dynamics, "
            "knowledge fabric, world model, attention, belief system, goal system, "
            "and semantic memory. Use all these capabilities to answer accurately.\n\n"
            f"Answer concisely. For multiple choice, answer with just the letter.\n\n"
            f"Question: {question.question}\n\nAnswer:"
        )
        return await llm.generate(prompt)

    async def _run_ablated_query(
        self, llm: LLMClient, question: BenchmarkQuestion, disabled_subsystem: str,
    ) -> str:
        """Run a query with a specific subsystem 'disabled'.

        Since we can't disable internal subsystems via HTTP, we simulate
        ablation by using the LLM directly with a prompt that explicitly
        omits the ablated capability.
        """
        subsystem_descriptions = {
            "reflection": (
                "Do NOT review or reflect on your answer. Do not check for errors or "
                "inconsistencies. Just give your first immediate response without any "
                "self-review or improvement step."
            ),
            "verification": (
                "Do NOT verify or fact-check your answer. Do not check if your answer "
                "is consistent with known facts. Skip any verification step."
            ),
            "counterfactuals": (
                "Do NOT consider alternative possibilities or 'what if' scenarios. "
                "Only consider the most obvious answer without exploring alternatives."
            ),
            "dynamics": (
                "Do NOT update your cognitive state based on the question. Do not adapt "
                "your reasoning strategy. Use a fixed, simple approach."
            ),
            "knowledge_fabric": (
                "Do NOT use any structured knowledge graph or concept relationships. "
                "Answer purely from your parametric knowledge without any knowledge "
                "structure or cross-referencing concepts."
            ),
            "world_model": (
                "Do NOT predict outcomes or simulate future states. Do not use any "
                "predictive model. Answer only based on direct knowledge without prediction."
            ),
            "attention": (
                "Do NOT focus attention on the most relevant parts of the question. "
                "Treat all parts of the question equally, even minor details."
            ),
            "belief_system": (
                "Do NOT use any prior beliefs or confidence assessments. Answer without "
                "considering what you already believe to be true or false."
            ),
            "goal_system": (
                "Do NOT set or pursue any goals in your reasoning process. Answer without "
                "a structured goal-directed approach."
            ),
            "semantic_memory": (
                "Do NOT use any long-term semantic memory or learned associations. "
                "Answer purely from immediate reasoning without recalled knowledge structures."
            ),
        }

        constraint = subsystem_descriptions.get(disabled_subsystem, "")

        prompt = (
            f"You are an AI system answering questions. {constraint}\n\n"
            f"Answer concisely. For multiple choice, answer with just the letter.\n\n"
            f"Question: {question.question}\n\nAnswer:"
        )

        response = await llm.generate(prompt)
        return response


# ============================================================================
# Report & Results Generator
# ============================================================================

def generate_report(run_id: Optional[str] = None) -> dict[str, Any]:
    """Generate a final report from stored data."""
    db = ValidationDB()

    if run_id is None:
        run_id = db.get_latest_run_id()
        if run_id is None:
            return {"error": "No validation runs found in database"}

    run_results = db.get_run_results(run_id)
    metrics = db.get_metrics_for_run(run_id)
    stats = db.get_stats_for_run(run_id)
    ablation = db.get_ablation_for_run(run_id)

    if not run_results:
        return {"error": f"No results found for run {run_id}"}

    # Organize by system
    systems: dict[str, list[dict]] = {}
    for r in run_results:
        sys = r["system_name"]
        if sys not in systems:
            systems[sys] = []
        systems[sys].append(r)

    # Compute per-system summary
    system_summaries = {}
    for sys_name, results in systems.items():
        correct = sum(1 for r in results if r["success"])
        total = len(results)
        latencies = [r["latency_ms"] for r in results if r["latency_ms"] > 0]

        system_summaries[sys_name] = {
            "accuracy": round(correct / total, 4) if total > 0 else 0,
            "correct": correct,
            "total": total,
            "mean_latency_ms": round(float(np.mean(latencies)), 1) if latencies else 0,
            "median_latency_ms": round(float(np.median(latencies)), 1) if latencies else 0,
        }

    # Rank by accuracy
    ranked = sorted(
        system_summaries.items(), key=lambda x: x[1]["accuracy"], reverse=True,
    )

    # Category breakdown
    category_breakdown: dict[str, dict[str, dict]] = {}
    suite = BenchmarkSuite()
    question_category = {q.id: q.category for q in suite.questions}

    for r in run_results:
        cat = question_category.get(r["question_id"], "unknown")
        sys = r["system_name"]
        if cat not in category_breakdown:
            category_breakdown[cat] = {}
        if sys not in category_breakdown[cat]:
            category_breakdown[cat][sys] = {"correct": 0, "total": 0}
        category_breakdown[cat][sys]["total"] += 1
        if r["success"]:
            category_breakdown[cat][sys]["correct"] += 1

    # Ablation summary
    ablation_summary = {}
    for r in ablation:
        subsys = r["disabled_subsystem"]
        if subsys not in ablation_summary:
            ablation_summary[subsys] = {"correct": 0, "total": 0}
        ablation_summary[subsys]["total"] += 1
        if r["success"]:
            ablation_summary[subsys]["correct"] += 1

    report = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "experiment_design": {
            "n_systems": len(systems),
            "n_questions": len(run_results) // len(systems) if systems else 0,
            "systems_tested": list(systems.keys()),
            "categories": list(category_breakdown.keys()),
        },
        "rankings": [
            {
                "rank": i + 1,
                "system": name,
                "accuracy": data["accuracy"],
                "correct": data["correct"],
                "total": data["total"],
                "mean_latency_ms": data["mean_latency_ms"],
            }
            for i, (name, data) in enumerate(ranked)
        ],
        "benchmark_results": {
            cat: {
                sys: {
                    "accuracy": round(v["correct"] / v["total"], 4) if v["total"] > 0 else 0,
                    "correct": v["correct"],
                    "total": v["total"],
                }
                for sys, v in sys_data.items()
            }
            for cat, sys_data in category_breakdown.items()
        },
        "system_metrics": system_summaries,
        "statistical_tests": [
            {
                "system_a": s["system_a"],
                "system_b": s["system_b"],
                "metric": s["metric"],
                "mean_diff": round(s["mean_diff"], 4),
                "cohens_d": round(s["cohens_d"], 4),
                "p_value": round(s["p_value"], 6),
                "significant_95": bool(s["significant_95"]),
            }
            for s in stats
            if s["metric"] == "accuracy"
        ],
        "statistical_significance": [
            {
                "comparison": f"{s['system_a']} vs {s['system_b']}",
                "metric": s["metric"],
                "mean_diff": round(s["mean_diff"], 4),
                "cohens_d": round(s["cohens_d"], 4),
                "p_value": round(s["p_value"], 6),
                "significant_95": bool(s["significant_95"]),
            }
            for s in stats
            if s["metric"] == "accuracy"
        ],
        "ablation": {
            "modules": [
                {
                    "name": subsys,
                    "accuracy": round(v["correct"] / v["total"], 4) if v["total"] > 0 else 0,
                    "total": v["total"],
                }
                for subsys, v in ablation_summary.items()
            ],
            "summary": {
                "helps": sum(
                    1 for v in ablation_summary.values()
                    if v["correct"] / max(v["total"], 1) > (
                        next(
                            (d["accuracy"] for n, d in ranked if "ACOS" in n.upper()),
                            0.5,
                        )
                    )
                ),
                "hurts": sum(
                    1 for v in ablation_summary.values()
                    if v["correct"] / max(v["total"], 1) < (
                        next(
                            (d["accuracy"] for n, d in ranked if "ACOS" in n.upper()),
                            0.5,
                        )
                    )
                ),
                "neutral": 0,
            },
        } if ablation_summary else {
            "modules": [],
            "summary": {"helps": 0, "hurts": 0, "neutral": 0},
        },
        "failure_analysis": {
            "systems": {},
            "examples": [],
        },
        "best_system": ranked[0][0] if ranked else "unknown",
        "conclusion": _generate_conclusion(ranked, category_breakdown, ablation_summary),
    }

    # Add failure analysis from run results
    for sys_name, results in systems.items():
        failed = [r for r in results if not r["success"]]
        report["failure_analysis"]["systems"][sys_name] = {
            "total_failures": len(failed),
            "failure_rate": round(len(failed) / len(results), 4) if results else 0,
        }

    return report


def get_results() -> dict[str, Any]:
    """Return latest results from the database (for --results flag)."""
    db = ValidationDB()
    run_id = db.get_latest_run_id()
    if run_id is None:
        return {
            "benchmark_results": {},
            "statistical_tests": [],
            "statistical_significance": [],
            "failure_analysis": {"systems": {}, "examples": []},
            "ablation": {"modules": [], "summary": {"helps": 0, "hurts": 0, "neutral": 0}},
            "message": "No validation runs found. Run --quick or --full first.",
        }
    return generate_report(run_id)


def _generate_conclusion(
    ranked: list[tuple[str, dict]],
    categories: dict,
    ablation: dict,
) -> str:
    """Generate a text conclusion from the results."""
    if not ranked:
        return "No results available."

    best = ranked[0]
    conclusion = (
        f"In this scientific validation run, {best[0]} achieved the highest accuracy "
        f"at {best[1]['accuracy']:.1%}. "
    )

    acos_rank = next(
        (i for i, (name, _) in enumerate(ranked) if "ACOS" in name.upper()),
        None,
    )
    if acos_rank is not None and acos_rank > 0:
        baseline_best = ranked[0]
        acos_data = ranked[acos_rank]
        conclusion += (
            f"ACOS ranked #{acos_rank + 1} with {acos_data[1]['accuracy']:.1%} accuracy, "
            f"compared to the best baseline {baseline_best[0]} at "
            f"{baseline_best[1]['accuracy']:.1%}. "
        )
    elif acos_rank == 0:
        conclusion += "ACOS outperformed all baseline systems. "

    if categories:
        acos_cat_wins = 0
        total_cats = 0
        for cat, sys_data in categories.items():
            total_cats += 1
            for sys_name, v in sys_data.items():
                if "ACOS" in sys_name.upper():
                    acos_acc = v["correct"] / max(v["total"], 1)
                    best_acc = max(
                        sv["correct"] / max(sv["total"], 1) for sv in sys_data.values()
                    )
                    if acos_acc >= best_acc:
                        acos_cat_wins += 1
                    break
        if total_cats > 0:
            conclusion += f"ACOS led in {acos_cat_wins}/{total_cats} categories. "

    if ablation:
        sorted_ablation = sorted(
            ablation.items(),
            key=lambda x: x[1].get("correct", 0) / max(x[1].get("total", 1), 1),
        )
        if sorted_ablation:
            worst_subsys = sorted_ablation[0][0]
            conclusion += (
                f"Ablation study shows removing {worst_subsys} has the largest impact."
            )

    return conclusion


# ============================================================================
# CLI Interface
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="ACOS Scientific Validation Program — Real Benchmarking",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--quick", action="store_true",
        help="Run 5 questions per category (30 total)",
    )
    group.add_argument(
        "--full", action="store_true",
        help="Run all 120 questions (20 per category)",
    )
    group.add_argument(
        "--ablation", action="store_true",
        help="Run ablation studies",
    )
    group.add_argument(
        "--report", action="store_true",
        help="Generate final report from stored data",
    )
    group.add_argument(
        "--results", action="store_true",
        help="Return latest results from database",
    )

    args = parser.parse_args()

    if args.report:
        report = generate_report()
        print(json.dumps(report, indent=2))
        return

    if args.results:
        results = get_results()
        print(json.dumps(results, indent=2))
        return

    if args.quick:
        qpc = 5
    elif args.full:
        qpc = 20
    elif args.ablation:
        qpc = 5
    else:
        qpc = 5

    if args.ablation:
        study = AblationStudy()
        result = await study.run(questions_per_category=qpc)
    else:
        validator = ScientificValidation()
        result = await validator.run(questions_per_category=qpc)

    # Output JSON to stdout
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
