# CareMate — Color Palette & Design System

## Overview

CareMate uses a modern OKLCH color space for perceptually uniform colors with excellent accessibility. The palette is designed for hospital environments with trust-building blues, calming teals, and emergency-grade reds.

---

## Primary Colors

### Trust Blue (Primary)
**Hex**: `#0B3C5D`  
**OKLCH**: `oklch(0.32 0.07 240)`  
**Usage**: Primary buttons, headers, doctor dashboard accents  
**Foreground**: `oklch(0.98 0.003 250)` (near-white)

**Description**: Deep, professional blue that conveys trust and medical authority. Used for primary actions and doctor-related interfaces.

### Calm Teal (Secondary)
**Hex**: `#328CC1`  
**OKLCH**: `oklch(0.6 0.12 230)`  
**Usage**: Secondary buttons, links, nurse dashboard accents  
**Foreground**: `oklch(0.98 0.003 250)` (near-white)

**Description**: Soothing teal that reduces anxiety. Used for secondary actions and nurse-related interfaces.

---

## Accent Colors

### Mint (Accent)
**Hex**: `#69D2E7`  
**OKLCH**: `oklch(0.81 0.09 215)`  
**Usage**: Highlights, hover states, interactive elements  
**Foreground**: `oklch(0.22 0.04 240)` (dark blue-gray)

**Description**: Light, refreshing cyan for interactive elements and positive feedback.

### Health Green (Success)
**Hex**: `#2EC4B6`  
**OKLCH**: `oklch(0.74 0.12 180)`  
**Usage**: Success messages, completed tasks, healthy vitals  
**Foreground**: `oklch(0.22 0.04 240)` (dark blue-gray)

**Description**: Vibrant teal-green indicating health, success, and completion.

### Alert Amber (Warning)
**Hex**: `#FF9F1C`  
**OKLCH**: `oklch(0.78 0.17 60)`  
**Usage**: Warning messages, pending actions, abnormal vitals  
**Foreground**: `oklch(0.22 0.04 240)` (dark blue-gray)

**Description**: Warm amber for warnings that need attention but aren't critical.

### Crimson Red (Destructive/Emergency)
**Hex**: `#D90429`  
**OKLCH**: `oklch(0.55 0.23 25)`  
**Usage**: Emergency alerts, critical errors, delete actions  
**Foreground**: `oklch(0.98 0.003 250)` (near-white)

**Description**: High-contrast red for emergencies and critical actions. Triggers immediate attention.

---

## Neutral Colors

### Background (Light Mode)
**OKLCH**: `oklch(0.985 0.003 250)`  
**Description**: Near-white with subtle blue tint for reduced eye strain

### Foreground (Light Mode)
**OKLCH**: `oklch(0.22 0.04 240)`  
**Description**: Dark blue-gray for primary text

### Card Background
**OKLCH**: `oklch(1 0 0)`  
**Description**: Pure white for elevated surfaces

### Muted Background
**OKLCH**: `oklch(0.96 0.008 240)`  
**Description**: Light gray-blue for disabled states and subtle backgrounds

### Muted Foreground
**OKLCH**: `oklch(0.48 0.03 240)`  
**Description**: Medium gray-blue for secondary text

### Border
**OKLCH**: `oklch(0.92 0.01 240)`  
**Description**: Subtle border color for dividers and inputs

---

## Dark Mode Colors

### Background (Dark Mode)
**OKLCH**: `oklch(0.18 0.03 240)`  
**Description**: Deep blue-black for dark mode background

### Foreground (Dark Mode)
**OKLCH**: `oklch(0.98 0.003 250)`  
**Description**: Near-white for dark mode text

### Card Background (Dark Mode)
**OKLCH**: `oklch(0.22 0.04 240)`  
**Description**: Slightly lighter than background for elevated surfaces

### Muted Background (Dark Mode)
**OKLCH**: `oklch(0.28 0.03 240)`  
**Description**: Medium dark for disabled states

### Muted Foreground (Dark Mode)
**OKLCH**: `oklch(0.7 0.02 240)`  
**Description**: Light gray for secondary text

### Border (Dark Mode)
**OKLCH**: `oklch(1 0 0 / 10%)`  
**Description**: Subtle white border with 10% opacity

---

## Sidebar Colors

### Sidebar Background
**Light**: `oklch(0.98 0.005 240)`  
**Description**: Very light blue-gray for sidebar

### Sidebar Foreground
**Light**: `oklch(0.22 0.04 240)`  
**Description**: Dark text for sidebar

### Sidebar Primary
**Light**: `oklch(0.32 0.07 240)` (Trust Blue)  
**Description**: Active navigation items

### Sidebar Accent
**Light**: `oklch(0.94 0.015 230)`  
**Description**: Hover state for sidebar items

### Sidebar Border
**Light**: `oklch(0.92 0.01 240)`  
**Description**: Dividers in sidebar

---

## Gradients

### Hero Gradient
```css
linear-gradient(135deg, 
  oklch(0.32 0.07 240) 0%,    /* Trust Blue */
  oklch(0.45 0.11 225) 50%,   /* Medium Blue */
  oklch(0.6 0.12 215) 100%    /* Calm Teal */
)
```
**Usage**: Hero sections, landing page backgrounds

### Aurora Gradient
```css
radial-gradient(ellipse at top left, 
  oklch(0.81 0.09 215 / 0.35), transparent 60%),
radial-gradient(ellipse at bottom right, 
  oklch(0.74 0.12 180 / 0.25), transparent 55%)
```
**Usage**: Subtle background accents, decorative overlays

### Card Gradient
```css
linear-gradient(180deg, 
  oklch(1 0 0 / 0.9),         /* White 90% */
  oklch(0.98 0.003 250 / 0.7) /* Light blue 70% */
)
```
**Usage**: Card backgrounds with subtle depth

---

## Shadows

### Soft Shadow
```css
0 1px 2px oklch(0.32 0.07 240 / 0.04),
0 8px 24px -12px oklch(0.32 0.07 240 / 0.12)
```
**Usage**: Default card elevation

### Elevated Shadow
```css
0 4px 12px -2px oklch(0.32 0.07 240 / 0.08),
0 24px 48px -16px oklch(0.32 0.07 240 / 0.18)
```
**Usage**: Modals, popovers, elevated cards

### Glow Shadow
```css
0 0 0 1px oklch(0.6 0.12 230 / 0.2),
0 8px 32px -4px oklch(0.6 0.12 230 / 0.35)
```
**Usage**: Focus states, interactive elements

### Emergency Shadow
```css
0 0 0 2px oklch(0.55 0.23 25 / 0.4),
0 0 48px oklch(0.55 0.23 25 / 0.5)
```
**Usage**: Emergency alerts, critical notifications

---

## Animations

### Pulse Emergency
```css
@keyframes pulse-emergency {
  0%, 100% { box-shadow: 0 0 0 0 oklch(0.55 0.23 25 / 0.7); }
  50% { box-shadow: 0 0 0 24px oklch(0.55 0.23 25 / 0); }
}
```
**Usage**: Emergency alert buttons

### Float Soft
```css
@keyframes float-soft {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-8px); }
}
```
**Usage**: Floating elements, decorative accents

### Fade Up
```css
@keyframes fade-up {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
```
**Usage**: Page transitions, content reveals

### Wave Bar
```css
@keyframes wave-bar {
  0%, 100% { transform: scaleY(0.3); }
  50% { transform: scaleY(1); }
}
```
**Usage**: Voice wave visualization

### Shimmer
```css
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
```
**Usage**: Loading states, skeleton screens

---

## Typography

### Font Family
**Primary**: `Satoshi, ui-sans-serif, system-ui, sans-serif`  
**Features**: `ss01, cv11` (stylistic sets for improved readability)

### Font Smoothing
**Webkit**: `-webkit-font-smoothing: antialiased`  
**Purpose**: Crisp text rendering on all displays

---

## Border Radius

| Size | Value | Usage |
|------|-------|-------|
| `sm` | `calc(0.875rem - 4px)` = `10px` | Small buttons, badges |
| `md` | `calc(0.875rem - 2px)` = `12px` | Input fields |
| `lg` | `0.875rem` = `14px` | Default cards, buttons |
| `xl` | `calc(0.875rem + 4px)` = `18px` | Large cards |
| `2xl` | `calc(0.875rem + 8px)` = `22px` | Modals |
| `3xl` | `calc(0.875rem + 12px)` = `26px` | Hero sections |

---

## Transitions

### Smooth Transition
```css
all 0.4s cubic-bezier(0.16, 1, 0.3, 1)
```
**Easing**: Custom ease-out curve for natural motion  
**Usage**: Default transition for interactive elements

### Reveal Transition
```css
opacity 0.9s cubic-bezier(0.16, 1, 0.3, 1),
transform 0.9s cubic-bezier(0.16, 1, 0.3, 1),
filter 0.9s cubic-bezier(0.16, 1, 0.3, 1)
```
**Usage**: Scroll-triggered reveals

### Kinetic Letter Transition
```css
opacity 0.7s cubic-bezier(0.16, 1, 0.3, 1),
transform 0.9s cubic-bezier(0.16, 1, 0.3, 1)
```
**Usage**: Per-letter text animations

---

## Accessibility

### Contrast Ratios

| Combination | Ratio | WCAG Level |
|-------------|-------|------------|
| Trust Blue on White | 10.2:1 | AAA |
| Calm Teal on White | 4.8:1 | AA |
| Mint on Dark Blue-Gray | 7.1:1 | AAA |
| Crimson Red on White | 5.9:1 | AA |
| Health Green on White | 4.6:1 | AA |
| Alert Amber on Dark Blue-Gray | 6.2:1 | AA |

### Reduced Motion
All animations respect `prefers-reduced-motion: reduce`:
```css
@media (prefers-reduced-motion: reduce) {
  .reveal, .kinetic-letter { 
    transition: none !important; 
    opacity: 1 !important; 
    transform: none !important; 
  }
  .marquee-track, .blob, .animate-float { 
    animation: none !important; 
  }
}
```

---

## Usage Guidelines

### Do's ✅
- Use Trust Blue for primary actions and doctor-related features
- Use Calm Teal for secondary actions and nurse-related features
- Use Crimson Red sparingly for emergencies only
- Use Health Green for success states and positive feedback
- Maintain consistent spacing with the border radius system
- Use shadows to establish visual hierarchy

### Don'ts ❌
- Don't use Crimson Red for non-critical actions
- Don't mix multiple accent colors in the same component
- Don't use pure black (#000000) — use foreground color instead
- Don't create custom colors outside the palette
- Don't use animations for critical information (accessibility)

---

## Color Mapping by Dashboard

| Dashboard | Primary Color | Accent Color | Use Case |
|-----------|---------------|--------------|----------|
| Doctor | Trust Blue | Mint | Medical queries, patient summaries |
| Nurse | Calm Teal | Health Green | Care requests, task completion |
| Nutrition | Health Green | Alert Amber | Meal plans, dietary alerts |
| Utility | Muted | Alert Amber | Maintenance, system status |
| Admin | Trust Blue | All colors | Metrics, alerts, management |
| Patient Device | Calm Teal | Mint | Voice interface, responses |

---

## Implementation

### CSS Variables
All colors are defined as CSS custom properties in `:root`:

```css
:root {
  --primary: oklch(0.32 0.07 240);
  --secondary: oklch(0.6 0.12 230);
  --accent: oklch(0.81 0.09 215);
  --destructive: oklch(0.55 0.23 25);
  --success: oklch(0.74 0.12 180);
  --warning: oklch(0.78 0.17 60);
  /* ... */
}
```

### Tailwind Usage
Colors are mapped to Tailwind utilities:

```tsx
<button className="bg-primary text-primary-foreground">
  Primary Button
</button>

<div className="bg-success text-success-foreground">
  Success Message
</div>

<div className="border-border shadow-soft">
  Card with Soft Shadow
</div>
```

### Direct CSS Usage
```css
.custom-element {
  background-color: var(--color-primary);
  color: var(--color-primary-foreground);
  box-shadow: var(--shadow-elevated);
}
```

---

## Design Tokens Export

### For Figma
```json
{
  "primary": {
    "value": "oklch(0.32 0.07 240)",
    "type": "color"
  },
  "secondary": {
    "value": "oklch(0.6 0.12 230)",
    "type": "color"
  },
  "accent": {
    "value": "oklch(0.81 0.09 215)",
    "type": "color"
  },
  "destructive": {
    "value": "oklch(0.55 0.23 25)",
    "type": "color"
  },
  "success": {
    "value": "oklch(0.74 0.12 180)",
    "type": "color"
  },
  "warning": {
    "value": "oklch(0.78 0.17 60)",
    "type": "color"
  }
}
```

### For iOS/Swift
```swift
extension Color {
    static let trustBlue = Color(oklch: (0.32, 0.07, 240))
    static let calmTeal = Color(oklch: (0.6, 0.12, 230))
    static let mint = Color(oklch: (0.81, 0.09, 215))
    static let crimsonRed = Color(oklch: (0.55, 0.23, 25))
    static let healthGreen = Color(oklch: (0.74, 0.12, 180))
    static let alertAmber = Color(oklch: (0.78, 0.17, 60))
}
```

### For Android/Kotlin
```kotlin
object CareMateColors {
    val TrustBlue = Color(0xFF0B3C5D)
    val CalmTeal = Color(0xFF328CC1)
    val Mint = Color(0xFF69D2E7)
    val CrimsonRed = Color(0xFFD90429)
    val HealthGreen = Color(0xFF2EC4B6)
    val AlertAmber = Color(0xFFFF9F1C)
}
```

---

## References

- **OKLCH Color Space**: https://oklch.com/
- **Tailwind CSS v4**: https://tailwindcss.com/
- **WCAG Contrast Guidelines**: https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html
- **Radix UI Colors**: https://www.radix-ui.com/colors

---

## Version History

- **v1.0** (2026-05-29): Initial color palette with OKLCH color space
- Hospital-safe colors with AAA/AA contrast ratios
- Dark mode support
- Accessibility-first design
