import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Activity,
  ArrowRight,
  Bell,
  ClipboardList,
  Mic,
  Radio,
  ShieldAlert,
  Smartphone,
  Sparkles,
  Stethoscope,
  Utensils,
  Wrench,
  Waves,
  Languages,
  HeartPulse,
  Zap,
} from "lucide-react";
import { ROLES } from "@/lib/roles";
import { VoiceWave } from "@/components/dashboard/VoiceWave";
import { Reveal, KineticText } from "@/components/Reveal";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "CareMate — Real-time hospital coordination" },
      { name: "description", content: "Voice-first, mobile, low-latency hospital coordination across doctor, nurse, nutrition, utility & admin workflows." },
    ],
  }),
  component: Landing,
});

function Landing() {
  return (
    <div className="min-h-screen overflow-x-hidden bg-background text-foreground">
      <FloatingNav />
      <Hero />
      <Marquee />
      <WorkflowViz />
      <FeaturesGrid />
      <VoiceShowcase />
      <DashboardShowcase />
      <EmergencySection />
      <MobileSection />
      <RealtimeSection />
      <LoginCTA />
      <Footer />
    </div>
  );
}

function Marquee() {
  const items = ["Voice-first", "Multilingual AI", "Realtime sync", "Emergency-grade", "PWA · Offline", "OCR + ChromaDB", "Low-latency", "Built for hospitals"];
  const loop = [...items, ...items];
  return (
    <section className="marquee border-y border-border bg-card/40 py-5">
      <div className="marquee-track text-2xl font-black tracking-tight md:text-4xl">
        {loop.map((t, i) => (
          <span key={i} className="inline-flex items-center gap-12">
            <span className={i % 3 === 0 ? "bg-gradient-to-r from-secondary to-accent bg-clip-text text-transparent" : "text-foreground/80"}>{t}</span>
            <span className="text-secondary">✦</span>
          </span>
        ))}
      </div>
    </section>
  );
}

function FloatingNav() {
  return (
    <div className="fixed inset-x-0 top-3 z-50 flex justify-center px-3">
      <nav className="flex w-full max-w-3xl items-center gap-2 rounded-2xl border border-border/60 bg-background/70 px-3 py-2 shadow-soft backdrop-blur-xl">
        <Link to="/" className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-hero text-primary-foreground shadow-glow">
            <Activity className="h-4 w-4" />
          </div>
          <span className="font-bold tracking-tight">CareMate</span>
        </Link>
        <div className="ml-2 hidden items-center gap-1 text-sm text-muted-foreground md:flex">
          <a href="#workflow" className="rounded-md px-2.5 py-1 transition hover:bg-muted hover:text-foreground">Workflow</a>
          <a href="#features" className="rounded-md px-2.5 py-1 transition hover:bg-muted hover:text-foreground">Features</a>
          <a href="#dashboards" className="rounded-md px-2.5 py-1 transition hover:bg-muted hover:text-foreground">Dashboards</a>
          <a href="#emergency" className="rounded-md px-2.5 py-1 transition hover:bg-muted hover:text-foreground">Emergency</a>
        </div>
        <Link
          to="/login"
          className="ml-auto inline-flex items-center gap-1.5 rounded-xl bg-primary px-3 py-1.5 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
        >
          Sign in <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </nav>
    </div>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden pt-28 pb-20 md:pt-36 md:pb-28">
      <div className="absolute inset-0 -z-10 bg-gradient-aurora" />
      <div className="blob absolute -left-32 top-20 -z-10 h-80 w-80 rounded-full bg-secondary/40" />
      <div className="blob absolute -right-24 top-60 -z-10 h-72 w-72 rounded-full bg-accent/40" style={{ animationDelay: "-6s" }} />

      <div className="mx-auto max-w-6xl px-4 text-center">
        <span className="animate-fade-up inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground shadow-soft">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-success" />
          Live real-time hospital coordination · v1
        </span>
        <h1 className="mt-6 mb-0 w-full text-center text-4xl font-black tracking-tight leading-tight md:text-6xl lg:text-7xl">
          <KineticText text="The voice-first nervous system" />{" "}
          <span className="bg-gradient-to-r from-secondary to-accent bg-clip-text text-transparent">
            <KineticText text="for your hospital." startDelay={700} />
          </span>
        </h1>
        <Reveal as="p" delay={200} className="mx-auto -mt-20 max-w-2xl text-pretty text-base text-muted-foreground md:text-lg">
          CareMate connects patients, doctors, nurses, nutritionists, utility staff and administrators with real-time voice, multilingual AI and emergency-grade alerts — built for mobile, fast on low networks.
        </Reveal>
        <Reveal delay={320} className="mt-8 flex flex-wrap justify-center gap-3">
          <Link
            to="/login"
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-glow transition hover:scale-[1.02] hover:bg-primary/90"
          >
            Open hospital portal <ArrowRight className="h-4 w-4" />
          </Link>
          <a
            href="#dashboards"
            className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-5 py-3 text-sm font-semibold transition hover:bg-muted"
          >
            See dashboards
          </a>
        </Reveal>

        <Reveal variant="scale" delay={420} className="mx-auto mt-14 max-w-4xl">
          <div className="rounded-3xl border border-border bg-gradient-card p-2 shadow-elevated">
            <div className="grid gap-2 rounded-2xl bg-card p-5 sm:grid-cols-3">
              <HeroStat icon={<HeartPulse className="h-4 w-4" />} label="Avg response" value="< 5s" tint="success" />
              <HeroStat icon={<Zap className="h-4 w-4" />} label="Emergency alert" value="< 2s" tint="destructive" />
              <HeroStat icon={<Radio className="h-4 w-4" />} label="Concurrent rooms" value="1,200+" tint="secondary" />
              <div className="sm:col-span-3 mt-2 rounded-xl bg-muted/50 p-4">
                <div className="mb-2 flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <Mic className="h-3.5 w-3.5 text-secondary" /> Patient · Room 207 · Tamil → English
                </div>
                <VoiceWave />
                <p className="mt-2 text-sm text-foreground/80">"Doctor, I am feeling dizzy after the morning dose."</p>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

function HeroStat({ icon, label, value, tint }: { icon: React.ReactNode; label: string; value: string; tint: "success" | "destructive" | "secondary" }) {
  const tintMap = {
    success: "bg-success/10 text-success",
    destructive: "bg-destructive/10 text-destructive",
    secondary: "bg-secondary/10 text-secondary",
  };
  return (
    <div className="rounded-xl border border-border/60 bg-background/50 p-4 text-left">
      <div className={`mb-2 inline-flex h-7 w-7 items-center justify-center rounded-md ${tintMap[tint]}`}>{icon}</div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-xl font-bold">{value}</p>
    </div>
  );
}

function WorkflowViz() {
  const steps = [
    { icon: <Mic className="h-4 w-4" />, label: "Patient speaks", sub: "Any language" },
    { icon: <Sparkles className="h-4 w-4" />, label: "AI routes & summarizes", sub: "Nemotron + Meditron" },
    { icon: <ClipboardList className="h-4 w-4" />, label: "Right role gets it", sub: "Nurse · Doctor · Diet" },
    { icon: <HeartPulse className="h-4 w-4" />, label: "Reply delivered", sub: "Voice · < 5s" },
  ];
  return (
    <section id="workflow" className="mx-auto max-w-6xl px-4 py-20">
      <Reveal className="mb-10 text-center">
        <p className="text-xs font-semibold uppercase tracking-widest text-secondary">AI workflow</p>
        <h2 className="mt-2 text-3xl font-bold tracking-tight md:text-4xl">From a whisper to the right care, in seconds.</h2>
        <Reveal as="p" delay={100} className="mx-auto max-w-2xl text-pretty text-base text-muted-foreground md:text-lg">
          Watch how CareMate captures patient intent, routes intelligently, and delivers responses — all without leaving the bedside.
        </Reveal>
      </Reveal>
      <div className="relative grid gap-3 md:grid-cols-4">
        {steps.map((s, i) => (
          <Reveal key={i} delay={i * 90} className="relative rounded-2xl border border-border bg-card p-5 shadow-soft transition hover:-translate-y-1 hover:shadow-elevated">
            <div className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg bg-secondary/10 text-secondary">{s.icon}</div>
            <p className="text-sm font-semibold">{s.label}</p>
            <p className="text-xs text-muted-foreground">{s.sub}</p>
            <span className="absolute right-3 top-3 text-[10px] font-mono text-muted-foreground">0{i + 1}</span>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

function FeaturesGrid() {
  const features = [
    { icon: <Mic />, title: "Voice-first interaction", body: "Auto-play patient voice, doctor replies hands-free. Built for tablets and gloves." },
    { icon: <Languages />, title: "Multilingual AI", body: "Real-time translation between patient and staff — Tamil, Hindi, English & more." },
    { icon: <ShieldAlert />, title: "Emergency override", body: "Code-red alerts pierce every queue with sound, color and room context." },
    { icon: <Radio />, title: "Realtime sync", body: "WebSocket-driven updates. No refresh, no polling, no waiting." },
    { icon: <Smartphone />, title: "PWA & offline", body: "Installable, cached, low-bandwidth — works on the worst hospital Wi-Fi." },
    { icon: <Sparkles />, title: "OCR & summaries", body: "Reports scanned, indexed in ChromaDB, surfaced as instant patient context." },
  ];
  return (
    <section id="features" className="mx-auto max-w-6xl px-4 py-20">
      <Reveal className="mb-10 text-center">
        <p className="text-xs font-semibold uppercase tracking-widest text-secondary">Built for hospitals</p>
        <h2 className="mt-2 text-3xl font-bold tracking-tight md:text-4xl">Less friction. Faster care.</h2>
        <Reveal as="p" delay={100} className="mx-auto mt-3 max-w-2xl text-pretty text-base text-muted-foreground md:text-lg">
          Every feature designed to reduce clicks, eliminate waiting, and keep focus on patients.
        </Reveal>
      </Reveal>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {features.map((f, i) => (
          <Reveal key={i} delay={(i % 3) * 100} className="group rounded-2xl border border-border bg-card p-5 shadow-soft transition hover:-translate-y-1 hover:shadow-elevated">
            <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-secondary/15 to-accent/20 text-secondary transition group-hover:scale-110">
              {f.icon}
            </div>
            <h3 className="text-base font-semibold">{f.title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{f.body}</p>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

function VoiceShowcase() {
  return (
    <section className="relative overflow-hidden py-20">
      <div className="absolute inset-0 -z-10 bg-gradient-aurora opacity-60" />
      <div className="mx-auto grid max-w-6xl gap-10 px-4 md:grid-cols-2 md:items-center">
        <Reveal variant="left">
          <p className="text-xs font-semibold uppercase tracking-widest text-secondary">Voice interaction</p>
          <h2 className="mt-2 text-3xl font-bold tracking-tight md:text-4xl">Auto Voice Assistant Mode.</h2>
          <p className="mt-4 text-muted-foreground">
            Doctors open the dashboard, the latest patient query plays automatically, and a single press records the reply — delivered as a voice note to the patient. Manual mode works just like a WhatsApp voice message.
          </p>
          <ul className="mt-6 space-y-3 text-sm">
            {["Hands-free for rounds & gloves", "Auto-queue prioritizes urgency", "Replies routed in &lt; 5 seconds"].map((t, i) => (
              <li key={i} className="flex items-start gap-3">
                <span className="mt-1 grid h-5 w-5 place-items-center rounded-full bg-success/15 text-success">
                  <Waves className="h-3 w-3" />
                </span>
                <span dangerouslySetInnerHTML={{ __html: t }} />
              </li>
            ))}
          </ul>
        </Reveal>
        <Reveal variant="right" delay={150} className="rounded-3xl border border-border bg-gradient-card p-6 shadow-elevated">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-full bg-secondary/15 text-secondary">
              <Mic className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold">Now playing · Room 312</p>
              <p className="text-xs text-muted-foreground">Patient: R. Iyer · Hindi → English</p>
            </div>
            <span className="ml-auto rounded-full bg-destructive/10 px-2 py-0.5 text-[10px] font-bold uppercase text-destructive">High</span>
          </div>
          <div className="my-5 rounded-2xl bg-muted/50 p-5">
            <VoiceWave bars={32} />
          </div>
          <p className="text-sm">"The pain in my chest is back, sharper than yesterday."</p>
          <div className="mt-5 grid grid-cols-3 gap-2">
            <button className="rounded-xl bg-primary px-3 py-2.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90">Reply by voice</button>
            <button className="rounded-xl border border-border bg-card px-3 py-2.5 text-xs font-semibold hover:bg-muted">Escalate</button>
            <button className="rounded-xl border border-border bg-card px-3 py-2.5 text-xs font-semibold hover:bg-muted">Summary</button>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

function DashboardShowcase() {
  return (
    <section id="dashboards" className="mx-auto max-w-6xl px-4 py-20">
      <Reveal className="mb-10 text-center">
        <p className="text-xs font-semibold uppercase tracking-widest text-secondary">Five focused dashboards</p>
        <h2 className="mt-2 text-3xl font-bold tracking-tight md:text-4xl">One platform, every role.</h2>
        <Reveal as="p" delay={100} className="mx-auto mt-3 max-w-2xl text-pretty text-base text-muted-foreground md:text-lg">
          Doctors, nurses, nutritionists, utility staff and admins each see exactly what they need — nothing more, nothing less.
        </Reveal>
      </Reveal>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {ROLES.map((r, i) => {
          const Icon = roleIcon(r.id);
          return (
            <Reveal key={r.id} delay={i * 80} variant="scale">
              <Link
                to={r.path}
                className="group block rounded-2xl border border-border bg-card p-5 shadow-soft transition hover:-translate-y-1 hover:border-secondary/50 hover:shadow-elevated"
              >
                <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-primary/5 text-primary transition group-hover:bg-primary group-hover:text-primary-foreground">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="text-base font-semibold">{r.label}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{r.tagline}</p>
                <span className="mt-4 inline-flex items-center gap-1 text-xs font-medium text-secondary">
                  Open dashboard <ArrowRight className="h-3 w-3 transition group-hover:translate-x-0.5" />
                </span>
              </Link>
            </Reveal>
          );
        })}
      </div>
    </section>
  );
}

function roleIcon(id: string) {
  switch (id) {
    case "doctor": return Stethoscope;
    case "nurse": return HeartPulse;
    case "nutrition": return Utensils;
    case "utility": return Wrench;
    default: return ShieldAlert;
  }
}

function EmergencySection() {
  return (
    <section id="emergency" className="mx-auto max-w-6xl px-4 py-20">
      <div className="overflow-hidden rounded-3xl border-2 border-destructive/20 bg-gradient-to-br from-destructive/5 via-card to-card p-8 shadow-soft md:p-12">
        <div className="grid gap-8 md:grid-cols-2 md:items-center">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full bg-destructive/10 px-3 py-1 text-xs font-bold uppercase tracking-widest text-destructive">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-destructive" /> Code Red
            </span>
            <h2 className="mt-4 text-3xl font-bold tracking-tight md:text-4xl">Emergency intelligence, built in.</h2>
            <p className="mt-3 text-muted-foreground">
              Critical alerts override every screen with flashing context, room number, patient summary and acknowledgement gates — until the right person responds.
            </p>
          </div>
          <div className="rounded-2xl border-2 border-destructive bg-destructive/5 p-5 shadow-emergency">
            <div className="flex items-center gap-3 text-destructive">
              <div className="grid h-10 w-10 animate-emergency place-items-center rounded-full bg-destructive text-destructive-foreground">
                <ShieldAlert className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-widest">Active emergency</p>
                <p className="text-lg font-bold leading-tight">Room 412 · Cardiac event</p>
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <button className="flex-1 rounded-xl bg-destructive py-2.5 text-sm font-semibold text-destructive-foreground">Respond</button>
              <button className="rounded-xl border border-destructive/30 px-3 py-2.5 text-sm font-semibold text-destructive">Ack</button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function MobileSection() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-20">
      <div className="grid gap-10 md:grid-cols-2 md:items-center">
        <div className="order-2 md:order-1">
          <div className="relative mx-auto w-64">
            <div className="animate-float rounded-[2.5rem] border-[10px] border-foreground/90 bg-card p-3 shadow-elevated">
              <div className="rounded-[1.8rem] bg-gradient-aurora p-4">
                <div className="mb-3 flex items-center justify-between text-xs text-foreground/70">
                  <span>9:41</span>
                  <span>● ● ●</span>
                </div>
                <div className="rounded-2xl bg-card p-4 shadow-soft">
                  <p className="text-[10px] uppercase tracking-widest text-muted-foreground">Incoming request</p>
                  <p className="mt-1 text-sm font-bold">Room 207 · Water</p>
                  <div className="my-3"><VoiceWave bars={14} /></div>
                  <button className="w-full rounded-xl bg-primary py-2 text-xs font-semibold text-primary-foreground">Accept</button>
                </div>
                <div className="mt-3 rounded-2xl bg-destructive p-3 text-destructive-foreground">
                  <p className="text-[10px] font-bold uppercase tracking-widest">Code red</p>
                  <p className="text-sm font-bold">Room 412</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="order-1 md:order-2">
          <p className="text-xs font-semibold uppercase tracking-widest text-secondary">Mobile-first</p>
          <h2 className="mt-2 text-3xl font-bold tracking-tight md:text-4xl">Made for the hallway, not the desk.</h2>
          <p className="mt-3 text-muted-foreground">
            Installs as a PWA. Touch-first targets. Voice over typing. Cached for low networks. Built so nurses on the move and doctors on tablets never wait.
          </p>
        </div>
      </div>
    </section>
  );
}

function RealtimeSection() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-20">
      <div className="grid gap-3 sm:grid-cols-3">
        {[
          { k: "≤ 2s", v: "Initial app load" },
          { k: "≤ 5s", v: "Voice reply delivery" },
          { k: "≤ 2s", v: "Emergency alert" },
        ].map((s, i) => (
          <div key={i} className="rounded-2xl border border-border bg-card p-6 text-center shadow-soft">
            <p className="bg-gradient-to-b from-secondary to-primary bg-clip-text text-4xl font-black text-transparent">{s.k}</p>
            <p className="mt-1 text-sm text-muted-foreground">{s.v}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function LoginCTA() {
  return (
    <section className="mx-auto max-w-5xl px-4 py-20">
      <div className="overflow-hidden rounded-3xl border border-border bg-gradient-hero p-10 text-center text-primary-foreground shadow-elevated md:p-16">
        <Bell className="mx-auto h-8 w-8 opacity-80" />
        <h2 className="mt-4 text-3xl font-bold tracking-tight md:text-5xl">Enter the hospital portal.</h2>
        <p className="mx-auto mt-3 max-w-xl text-primary-foreground/80">
          Role-based access for doctors, nurses, nutritionists, utility staff and admins. One sign-in, one dashboard, one workflow.
        </p>
        <Link
          to="/login"
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-background px-5 py-3 text-sm font-semibold text-foreground transition hover:scale-[1.02]"
        >
          Sign in <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 text-sm text-muted-foreground md:flex-row">
        <div className="flex items-center gap-2">
          <div className="grid h-6 w-6 place-items-center rounded-md bg-primary text-primary-foreground">
            <Activity className="h-3 w-3" />
          </div>
          <span>© {new Date().getFullYear()} CareMate. Built for hospitals.</span>
        </div>
        <div className="flex gap-4">
          <a href="#workflow" className="hover:text-foreground">Workflow</a>
          <a href="#features" className="hover:text-foreground">Features</a>
          <a href="#dashboards" className="hover:text-foreground">Dashboards</a>
        </div>
      </div>
    </footer>
  );
}
