import { useEffect, useState } from "react";

interface Props {
  active?: boolean;
  bars?: number;
  className?: string;
}

export function VoiceWave({ active = true, bars = 24, className = "" }: Props) {
  const [seed, setSeed] = useState(0);
  useEffect(() => {
    if (!active) return;
    const t = setInterval(() => setSeed((s) => s + 1), 600);
    return () => clearInterval(t);
  }, [active]);

  return (
    <div className={`flex h-10 items-center justify-center gap-[3px] ${className}`}>
      {Array.from({ length: bars }).map((_, i) => {
        const h = 20 + ((Math.sin(i * 0.6 + seed) + 1) / 2) * 28;
        return (
          <span
            key={i}
            className={`w-[3px] rounded-full ${active ? "bg-secondary animate-wave-bar" : "bg-border"}`}
            style={{ height: `${h}px`, animationDelay: `${i * 0.05}s` }}
          />
        );
      })}
    </div>
  );
}
