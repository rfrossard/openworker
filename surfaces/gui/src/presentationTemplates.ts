export interface PresentationTemplate {
  id: string;
  name: string;
  description: string;
  colors: [string, string, string];
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
];

export function templateById(id: string): PresentationTemplate {
  return PRESENTATION_TEMPLATES.find((template) => template.id === id) ?? PRESENTATION_TEMPLATES[0];
}
