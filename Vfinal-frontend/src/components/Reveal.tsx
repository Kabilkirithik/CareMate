import { useReveal } from "@/hooks/useReveal";
import type { ElementType, ReactNode } from "react";

interface RevealProps {
  as?: ElementType;
  children: ReactNode;
  className?: string;
  delay?: number;
  variant?: "up" | "left" | "right" | "scale";
  id?: string;
}

export function Reveal({ as: Tag = "div", children, className = "", delay = 0, variant = "up", id }: RevealProps) {
  const ref = useReveal<HTMLElement>();
  return (
    <Tag
      ref={ref as never}
      id={id}
      className={`reveal reveal-${variant} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </Tag>
  );
}

interface KineticTextProps {
  text: string;
  className?: string;
  stagger?: number;
  startDelay?: number;
}

export function KineticText({ text, className = "", stagger = 35, startDelay = 0 }: KineticTextProps) {
  const ref = useReveal<HTMLSpanElement>(0.2);
  const words = text.split(" ");
  let i = 0;
  return (
    <span ref={ref} className={`kinetic ${className}`}>
      {words.map((w, wi) => (
        <span key={wi} className="kinetic-word">
          {Array.from(w).map((ch) => {
            const delay = startDelay + i * stagger;
            i++;
            return (
              <span
                key={`${wi}-${i}`}
                className="kinetic-letter"
                style={{ transitionDelay: `${delay}ms` }}
              >
                {ch}
              </span>
            );
          })}
          {wi < words.length - 1 && <span className="kinetic-space"> </span>}
        </span>
      ))}
    </span>
  );
}
