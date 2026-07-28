export interface PresentationTemplate {
  id: string;
  name: string;
  description: string;
  colors: [string, string, string];
  gradient?: [string, string];
  transition?: "fade" | "push" | "wipe" | "split" | "cover";
  motif?: "clean" | "chart" | "table" | "image";
}

// Native, editable themes inspired by Presenton's reusable-template model. They are
// design tokens rather than raster backgrounds, so every PowerPoint element stays editable.
export const PRESENTATION_TEMPLATES: PresentationTemplate[] = [
  { id: "atlas", name: "Atlas", description: "Clear blue executive storytelling", colors: ["#1A1F2C", "#2F6BFF", "#F7F8FA"] },
  { id: "aurora", name: "Aurora", description: "Vivid technology and innovation", colors: ["#101827", "#8B5CF6", "#22D3EE"] },
  { id: "boardroom", name: "Boardroom", description: "Conservative strategy and finance", colors: ["#14213D", "#C89B3C", "#F7F4ED"] },
  { id: "editorial", name: "Editorial", description: "Warm magazine-style narratives", colors: ["#292524", "#C2410C", "#FAF7F2"] },
  { id: "forest", name: "Forest", description: "Sustainability and natural systems", colors: ["#17352B", "#2F855A", "#F2F7F3"] },
  { id: "midnight", name: "Midnight", description: "Cinematic dark presentations", colors: ["#090D18", "#5B8CFF", "#171D2D"] },
  { id: "monochrome", name: "Monochrome", description: "Minimal black-and-white clarity", colors: ["#171717", "#737373", "#FAFAFA"] },
  { id: "ocean", name: "Ocean", description: "Calm research and scientific briefs", colors: ["#123047", "#0891B2", "#F0F9FF"] },
  { id: "paper", name: "Paper", description: "Academic reports and evidence reviews", colors: ["#2B2A27", "#8B6F47", "#FCFBF7"] },
  { id: "plum", name: "Plum", description: "Premium culture and creative work", colors: ["#321B3A", "#A855A0", "#FBF5FA"] },
  { id: "signal", name: "Signal", description: "Bold launches and recommendations", colors: ["#18181B", "#EF4444", "#FFF7ED"] },
  { id: "studio", name: "Studio", description: "Modern product and design reviews", colors: ["#20242C", "#14B8A6", "#F5F7FA"] },
  { id: "neon-flow", name: "Neon Flow", description: "Animated neon gradient for technology stories", colors: ["#07111F", "#22D3EE", "#0F172A"], gradient: ["#07111F", "#312E81"], transition: "push", motif: "chart" },
  { id: "sunrise", name: "Sunrise", description: "Warm gradient for optimistic proposals", colors: ["#3B1D2A", "#F97316", "#FFF7ED"], gradient: ["#FFF7ED", "#FED7AA"], transition: "fade", motif: "image" },
  { id: "cyber-grid", name: "Cyber Grid", description: "Dark data dashboards and technical charts", colors: ["#020617", "#38BDF8", "#0F172A"], gradient: ["#020617", "#172554"], transition: "wipe", motif: "chart" },
  { id: "prism", name: "Prism", description: "Color-rich gradient for creative narratives", colors: ["#24123A", "#D946EF", "#FAF5FF"], gradient: ["#FDF4FF", "#DBEAFE"], transition: "split", motif: "image" },
  { id: "velocity", name: "Velocity", description: "High-energy motion for product launches", colors: ["#111827", "#F43F5E", "#FFF1F2"], gradient: ["#FFF1F2", "#FFE4E6"], transition: "push", motif: "chart" },
  { id: "ember", name: "Ember", description: "Dramatic orange gradient for bold decisions", colors: ["#2A1208", "#F97316", "#FFF7ED"], gradient: ["#431407", "#7C2D12"], transition: "cover", motif: "image" },
  { id: "glacier", name: "Glacier", description: "Cool scientific gradient with clean tables", colors: ["#0C4A6E", "#06B6D4", "#ECFEFF"], gradient: ["#ECFEFF", "#CFFAFE"], transition: "fade", motif: "table" },
  { id: "bloom", name: "Bloom", description: "Soft editorial gradient for people stories", colors: ["#4A1830", "#EC4899", "#FFF1F2"], gradient: ["#FFF1F2", "#FCE7F3"], transition: "split", motif: "image" },
  { id: "orbit", name: "Orbit", description: "Space-inspired motion for future strategy", colors: ["#090B20", "#818CF8", "#151936"], gradient: ["#090B20", "#312E81"], transition: "cover", motif: "chart" },
  { id: "horizon", name: "Horizon", description: "Wide photographic backgrounds and vision", colors: ["#172554", "#0EA5E9", "#F0F9FF"], gradient: ["#DBEAFE", "#F0F9FF"], transition: "wipe", motif: "image" },
  { id: "aurora-glass", name: "Aurora Glass", description: "Glass-like gradient for innovation decks", colors: ["#10233C", "#14B8A6", "#ECFDF5"], gradient: ["#ECFDF5", "#E0E7FF"], transition: "fade", motif: "chart" },
  { id: "executive-gradient", name: "Executive Gradient", description: "Premium navy gradient with financial tables", colors: ["#111827", "#D4A72C", "#F8FAFC"], gradient: ["#F8FAFC", "#E2E8F0"], transition: "fade", motif: "table" },
  { id: "data-wave", name: "Data Wave", description: "Analytical blue gradient for charts and KPIs", colors: ["#082F49", "#0284C7", "#F0F9FF"], gradient: ["#E0F2FE", "#F0FDFA"], transition: "push", motif: "chart" },
  { id: "financial-pulse", name: "Financial Pulse", description: "Market-focused green gradient and tables", colors: ["#052E16", "#22C55E", "#F0FDF4"], gradient: ["#DCFCE7", "#F0FDF4"], transition: "wipe", motif: "table" },
  { id: "editorial-motion", name: "Editorial Motion", description: "Animated magazine treatment with photography", colors: ["#292524", "#E11D48", "#FFFBEB"], gradient: ["#FFFBEB", "#FFE4E6"], transition: "split", motif: "image" },
  { id: "photo-story", name: "Photo Story", description: "Full-bleed imagery with cinematic fades", colors: ["#111827", "#F59E0B", "#F9FAFB"], gradient: ["#111827", "#374151"], transition: "fade", motif: "image" },
  { id: "cinematic-frame", name: "Cinematic Frame", description: "Dark image backgrounds and dramatic reveals", colors: ["#09090B", "#EAB308", "#18181B"], gradient: ["#09090B", "#27272A"], transition: "cover", motif: "image" },
  { id: "dashboard-pro", name: "Dashboard Pro", description: "Structured KPI charts and comparison tables", colors: ["#172033", "#2563EB", "#F8FAFC"], gradient: ["#EFF6FF", "#F8FAFC"], transition: "push", motif: "chart" },
  { id: "science-spectrum", name: "Science Spectrum", description: "Research gradients, tables, and evidence charts", colors: ["#134E4A", "#8B5CF6", "#F0FDFA"], gradient: ["#F0FDFA", "#F5F3FF"], transition: "wipe", motif: "table" },
  { id: "impact-report", name: "Impact Report", description: "Human-centered imagery with metric storytelling", colors: ["#1C1917", "#16A34A", "#FAFAF9"], gradient: ["#F0FDF4", "#FAFAF9"], transition: "fade", motif: "image" },
];

export function templateById(id: string): PresentationTemplate {
  return PRESENTATION_TEMPLATES.find((template) => template.id === id) ?? PRESENTATION_TEMPLATES[0];
}
