import { useMemo } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Mic,
  Brain,
  Target,
  BarChart3,
  GraduationCap,
  Clock,
  ChevronDown,
  ArrowRight,
  CheckCircle2,
  Sparkles,
} from "lucide-react";
import Button from "@/components/ui/Button";

// ---------------------------------------------------------------------------
// Animation variants
// ---------------------------------------------------------------------------

const ease = [0.22, 1, 0.36, 1] as const;

const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: (i: number = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, delay: i * 0.15, ease },
  }),
};

const scaleIn = {
  hidden: { opacity: 0, scale: 0.8 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.8, ease },
  },
};

const staggerContainer = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.12, delayChildren: 0.2 },
  },
};

// ---------------------------------------------------------------------------
// Floating particles (lightweight version of TheraTales' ParticleBackground)
// ---------------------------------------------------------------------------

const PARTICLE_COLORS = [
  "rgba(59,130,246,0.15)",  // blue
  "rgba(6,182,212,0.12)",   // cyan
  "rgba(0,179,126,0.12)",   // green
  "rgba(255,122,172,0.15)", // pink
  "rgba(139,92,246,0.12)",  // purple
];

interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
  color: string;
  duration: number;
  delay: number;
}

function generateParticles(count: number): Particle[] {
  return Array.from({ length: count }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    size: 4 + Math.random() * 10,
    color: PARTICLE_COLORS[i % PARTICLE_COLORS.length]!,
    duration: 10 + Math.random() * 8,
    delay: -(Math.random() * 15),
  }));
}

function FloatingParticles() {
  const particles = useMemo(() => generateParticles(30), []);

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {particles.map((p) => (
        <motion.div
          key={p.id}
          className="absolute rounded-full"
          style={{
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: p.size,
            height: p.size,
            backgroundColor: p.color,
          }}
          animate={{
            y: [0, -20, 0, 15, 0],
            x: [0, 8, 0, -8, 0],
            scale: [1, 1.2, 1, 0.9, 1],
          }}
          transition={{
            duration: p.duration,
            repeat: Infinity,
            ease: "easeInOut",
            delay: p.delay,
          }}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------

const LOOP_STEPS = [
  {
    icon: Mic,
    title: "Teach",
    desc: "Any lesson, any platform. Preply, Zoom, in-person - upload the recording.",
    color: "#3b82f6",
  },
  {
    icon: Brain,
    title: "Analyze",
    desc: "AI categorizes errors by type and severity, extracts themes and vocabulary.",
    color: "#8b5cf6",
  },
  {
    icon: Target,
    title: "Practice",
    desc: "Students get targeted exercises built from their actual mistakes, auto-graded.",
    color: "#00b37e",
  },
  {
    icon: BarChart3,
    title: "Prepare",
    desc: "Teachers get morning briefings with scores, patterns, and what to focus on.",
    color: "#ff7aac",
  },
];

const TEACHER_BENEFITS = [
  "Morning briefing of all upcoming students",
  "Error patterns tracked across sessions",
  "Progress data replaces guesswork",
  "Works with offline lessons too",
];

const STUDENT_BENEFITS = [
  "Practice built from your actual lesson errors",
  "Auto-graded with immediate feedback",
  "Study materials in your format - flashcards, audio, slides",
  "Any language pair, not just English",
];

// ---------------------------------------------------------------------------
// Landing Page
// ---------------------------------------------------------------------------

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--color-surface)]">
      {/* ----------------------------------------------------------------- */}
      {/* Sticky nav                                                        */}
      {/* ----------------------------------------------------------------- */}
      <nav className="fixed top-0 z-50 w-full border-b border-[var(--color-border)] bg-[var(--color-surface)]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <Link to="/" className="flex items-center gap-2.5">
            <img src="/loop/logo.png" alt="Loop" className="h-14" />
            <span className="text-lg font-semibold tracking-tight text-[color:var(--color-text-primary)]">
              Loop Your Lesson
            </span>
          </Link>
          <Link to="/students">
            <Button variant="primary" size="sm">
              Try Loop
            </Button>
          </Link>
        </div>
      </nav>

      {/* ----------------------------------------------------------------- */}
      {/* 1. Hero                                                           */}
      {/* ----------------------------------------------------------------- */}
      <section className="relative flex flex-col items-center overflow-hidden px-6 pb-20 pt-32">
        {/* Animated background */}
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse 80% 60% at 50% 40%, rgba(204,226,255,0.25) 0%, rgba(255,219,233,0.15) 40%, transparent 70%)",
          }}
        />
        <FloatingParticles />

        <motion.div
          className="relative z-10 mx-auto flex max-w-3xl flex-col items-center text-center"
          initial="hidden"
          animate="visible"
          variants={staggerContainer}
        >
          {/* Logo */}
          <motion.img
            src="/loop/logo.png"
            alt="Loop - infinity loop"
            className="mb-4 h-28"
            variants={scaleIn}
          />

          {/* Headline */}
          <motion.h1
            className="mb-5 text-5xl font-bold leading-[1.1] tracking-tight text-[color:var(--color-text-primary)] sm:text-6xl"
            variants={fadeUp}
            custom={1}
          >
            Every lesson keeps{" "}
            <span
              className="bg-clip-text text-transparent"
              style={{
                backgroundImage:
                  "linear-gradient(135deg, #3b82f6 0%, #06b6d4 50%, #00b37e 100%)",
              }}
            >
              teaching
            </span>
            <br />
            after it ends
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            className="mb-8 max-w-xl text-lg leading-relaxed text-[color:var(--color-text-secondary)]"
            variants={fadeUp}
            custom={2}
          >
            Closing <strong>the loop</strong> between teaching and learning.
            <br />
            AI-powered lesson intelligence for Preply tutors and students.
          </motion.p>

          {/* CTAs */}
          <motion.div
            className="flex flex-wrap items-center justify-center gap-4"
            variants={fadeUp}
            custom={3}
          >
            <Link to="/students">
              <Button variant="primary" size="lg">
                Try Loop
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <a href="#how-it-works">
              <Button variant="secondary" size="lg">
                See how it works
              </Button>
            </a>
          </motion.div>
        </motion.div>

        {/* Scroll hint */}
        <motion.div
          className="mt-12 flex flex-col items-center gap-1"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5, duration: 0.6 }}
        >
          <span className="text-xs tracking-widest uppercase text-[color:var(--color-text-muted)]">
            Scroll
          </span>
          <motion.div
            animate={{ y: [0, 6, 0] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
          >
            <ChevronDown className="h-4 w-4 text-[color:var(--color-text-muted)]" />
          </motion.div>
        </motion.div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* 2. Problem                                                        */}
      {/* ----------------------------------------------------------------- */}
      <section className="bg-[var(--color-surface-secondary)] px-6 py-16">
        <div className="mx-auto max-w-6xl">
          <motion.div
            className="mb-10 text-center"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={fadeUp}
          >
            <h2 className="mb-3 text-3xl font-bold tracking-tight text-[color:var(--color-text-primary)] sm:text-4xl">
              What happens between lessons?
            </h2>
            <p className="mx-auto max-w-lg text-base text-[color:var(--color-text-secondary)]">
              A lot - and almost none of it connects back to Preply.
            </p>
          </motion.div>

          <motion.div
            className="grid gap-6 md:grid-cols-2"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-60px" }}
            variants={staggerContainer}
          >
            {/* Students */}
            <motion.div
              className="rounded-xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-8 shadow-sm"
              variants={fadeUp}
              whileHover={{ y: -4, boxShadow: "0 8px 30px rgba(0,0,0,0.06)" }}
              transition={{ type: "spring", stiffness: 300, damping: 20 }}
            >
              <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50">
                <GraduationCap className="h-6 w-6 text-blue-500" />
              </div>
              <h3 className="mb-3 text-xl font-semibold text-[color:var(--color-text-primary)]">
                Students go dark
              </h3>
              <p className="leading-relaxed text-[color:var(--color-text-secondary)]">
                Practice between sessions - Duolingo, YouTube, flashcard apps -
                has zero connection to what their tutor taught. The personal
                thread that makes private tutoring worth paying for goes quiet.
              </p>
            </motion.div>

            {/* Teachers */}
            <motion.div
              className="rounded-xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-8 shadow-sm"
              variants={fadeUp}
              whileHover={{ y: -4, boxShadow: "0 8px 30px rgba(0,0,0,0.06)" }}
              transition={{ type: "spring", stiffness: 300, damping: 20 }}
            >
              <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--color-primary-light)]">
                <Clock className="h-6 w-6 text-[color:var(--color-primary)]" />
              </div>
              <h3 className="mb-3 text-xl font-semibold text-[color:var(--color-text-primary)]">
                Teachers lose track
              </h3>
              <p className="leading-relaxed text-[color:var(--color-text-secondary)]">
                8+ unpaid hours monthly tracking progress across WhatsApp, Google
                Docs, and memory. Prep quality degrades, lessons become generic,
                and personalization erodes.
              </p>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* 3. The Loop (how it works)                                        */}
      {/* ----------------------------------------------------------------- */}
      <section
        id="how-it-works"
        className="scroll-mt-20 bg-[var(--color-surface)] px-6 py-16"
      >
        <div className="mx-auto max-w-6xl">
          <motion.div
            className="mb-10 text-center"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={fadeUp}
          >
            <div className="mb-4 flex items-center justify-center gap-2">
              <Sparkles className="h-5 w-5 text-[color:var(--color-primary)]" />
              <span className="text-sm font-medium uppercase tracking-widest text-[color:var(--color-primary)]">
                How it works
              </span>
            </div>
            <h2 className="mb-3 text-3xl font-bold tracking-tight text-[color:var(--color-text-primary)] sm:text-4xl">
              The Loop
            </h2>
            <p className="mx-auto max-w-md text-base text-[color:var(--color-text-secondary)]">
              Teach, analyze, practice, prepare - repeat.
            </p>
          </motion.div>

          {/* Steps */}
          <motion.div
            className="relative grid gap-6 sm:grid-cols-2 lg:grid-cols-4"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-40px" }}
            variants={staggerContainer}
          >
            {/* Connecting line (desktop only) */}
            <div className="pointer-events-none absolute left-0 right-0 top-[3.5rem] z-0 hidden lg:block">
              <div className="mx-16 h-[2px] bg-gradient-to-r from-blue-200 via-purple-200 via-50% to-pink-200" />
            </div>

            {LOOP_STEPS.map((step, i) => (
              <motion.div
                key={step.title}
                className="relative z-10 flex flex-col items-center text-center"
                variants={fadeUp}
                custom={i}
              >
                <motion.div
                  className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] shadow-sm"
                  whileHover={{ scale: 1.08, rotate: 2 }}
                  transition={{ type: "spring", stiffness: 400, damping: 15 }}
                >
                  <step.icon
                    className="h-7 w-7"
                    style={{ color: step.color }}
                  />
                </motion.div>
                <div className="mb-1.5 text-xs font-semibold uppercase tracking-widest text-[color:var(--color-text-muted)]">
                  Step {i + 1}
                </div>
                <h3 className="mb-2 text-lg font-semibold text-[color:var(--color-text-primary)]">
                  {step.title}
                </h3>
                <p className="max-w-[220px] text-sm leading-relaxed text-[color:var(--color-text-secondary)]">
                  {step.desc}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* 4. Two sides                                                      */}
      {/* ----------------------------------------------------------------- */}
      <section className="bg-[var(--color-surface-secondary)] px-6 py-16">
        <div className="mx-auto max-w-6xl">
          <motion.div
            className="mb-10 text-center"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={fadeUp}
          >
            <h2 className="mb-3 text-3xl font-bold tracking-tight text-[color:var(--color-text-primary)] sm:text-4xl">
              A superpower for both sides
            </h2>
            <p className="mx-auto max-w-lg text-base text-[color:var(--color-text-secondary)]">
              The loop handles the rest. Teachers stay informed, students stay
              practiced.
            </p>
          </motion.div>

          <motion.div
            className="grid gap-6 md:grid-cols-2"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-60px" }}
            variants={staggerContainer}
          >
            {/* For teachers */}
            <motion.div
              className="rounded-xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-8 shadow-sm"
              variants={fadeUp}
              whileHover={{ y: -4, boxShadow: "0 8px 30px rgba(0,0,0,0.06)" }}
              transition={{ type: "spring", stiffness: 300, damping: 20 }}
            >
              <div
                className="mb-5 inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-sm font-medium text-[color:var(--color-text-primary)]"
                style={{ background: "var(--color-highlight-gradient)" }}
              >
                <Clock className="h-3.5 w-3.5" />
                For teachers
              </div>
              <ul className="space-y-3.5">
                {TEACHER_BENEFITS.map((b) => (
                  <li key={b} className="flex items-start gap-3">
                    <CheckCircle2 className="mt-0.5 h-4.5 w-4.5 shrink-0 text-[color:var(--color-success)]" />
                    <span className="text-[15px] leading-relaxed text-[color:var(--color-text-secondary)]">
                      {b}
                    </span>
                  </li>
                ))}
              </ul>
            </motion.div>

            {/* For students */}
            <motion.div
              className="rounded-xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-8 shadow-sm"
              variants={fadeUp}
              whileHover={{ y: -4, boxShadow: "0 8px 30px rgba(0,0,0,0.06)" }}
              transition={{ type: "spring", stiffness: 300, damping: 20 }}
            >
              <div
                className="mb-5 inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-sm font-medium text-[color:var(--color-text-primary)]"
                style={{ background: "var(--color-highlight-gradient)" }}
              >
                <GraduationCap className="h-3.5 w-3.5" />
                For students
              </div>
              <ul className="space-y-3.5">
                {STUDENT_BENEFITS.map((b) => (
                  <li key={b} className="flex items-start gap-3">
                    <CheckCircle2 className="mt-0.5 h-4.5 w-4.5 shrink-0 text-[color:var(--color-success)]" />
                    <span className="text-[15px] leading-relaxed text-[color:var(--color-text-secondary)]">
                      {b}
                    </span>
                  </li>
                ))}
              </ul>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* 5. Footer CTA                                                     */}
      {/* ----------------------------------------------------------------- */}
      <section className="relative overflow-hidden px-6 py-16">
        {/* Soft gradient background */}
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse 90% 70% at 50% 50%, rgba(204,226,255,0.2) 0%, rgba(255,219,233,0.12) 50%, transparent 80%)",
          }}
        />

        <motion.div
          className="relative z-10 mx-auto flex max-w-2xl flex-col items-center text-center"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={staggerContainer}
        >
          <motion.img
            src="/loop/logo.png"
            alt=""
            className="mb-6 h-16 opacity-60"
            variants={scaleIn}
          />
          <motion.h2
            className="mb-4 text-3xl font-bold tracking-tight text-[color:var(--color-text-primary)] sm:text-4xl"
            variants={fadeUp}
            custom={1}
          >
            Ready to close the loop?
          </motion.h2>
          <motion.p
            className="mb-8 max-w-md text-base text-[color:var(--color-text-secondary)]"
            variants={fadeUp}
            custom={2}
          >
            Every lesson your students take becomes a cycle of improvement.
            Start now - it takes 30 seconds.
          </motion.p>
          <motion.div variants={fadeUp} custom={3}>
            <Link to="/students">
              <Button variant="primary" size="lg">
                Get started
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </motion.div>
        </motion.div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* Footer                                                            */}
      {/* ----------------------------------------------------------------- */}
      <footer className="border-t border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-5">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 sm:flex-row">
          <div className="flex items-center gap-2">
            <img src="/loop/logo.png" alt="" className="h-7 opacity-50" />
            <span className="text-sm text-[color:var(--color-text-muted)]">
              Loop by The Loop team
            </span>
          </div>
          <span className="text-xs text-[color:var(--color-text-muted)]">
            Built for the Preply × Agora hackathon, March 2026
          </span>
        </div>
      </footer>
    </div>
  );
}
