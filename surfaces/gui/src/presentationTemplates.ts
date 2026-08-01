export interface PresentationTemplate {
  id: string;
  name: string;
  description: string;
  colors: [string, string, string];
  gradient?: [string, string];
  transition?: "fade" | "push" | "wipe" | "split" | "cover";
  motif?: "clean" | "chart" | "table" | "image";
  composition?: "photo-left" | "photo-right" | "botanical" | "collage" | "torn-photo" | "editorial" | "full-bleed" | "infographic" | "minimal-frame" | "heritage";
  /** Original, editable visual language shared by preview and exported decks. */
  theme?: "atlas" | "chalkboard" | "notebook" | "newsroom" | "forest" | "dashboard" | "infographic" | "itau" | "tron" | "blockworld" | "consulting";
  /** Five deterministic, CSS-authored background compositions—not third-party imagery. */
  backdropVariants?: readonly string[];
  accentOptions?: readonly { id: string; label: string; color: string }[];
}

// Native, editable themes inspired by Presenton's reusable-template model. They are
// design tokens rather than raster backgrounds, so every PowerPoint element stays editable.
export const PRESENTATION_TEMPLATES: PresentationTemplate[] = [
  { id: "atlas", name: "Atlas", description: "Clear blue executive storytelling", colors: ["#1A1F2C", "#2F6BFF", "#F7F8FA"] },
  { id: "aurora", name: "Aurora", description: "Vivid technology and innovation", colors: ["#101827", "#8B5CF6", "#22D3EE"] },
  { id: "boardroom", name: "Boardroom", description: "Chalkboard strategy workshop with hand-drawn evidence", colors: ["#F4F1DF", "#F6C453", "#101713"], gradient: ["#101713", "#1C2A22"], transition: "wipe", motif: "clean", theme: "chalkboard", backdropVariants: ["slate", "grid", "formula", "cards", "ledger"] },
  { id: "editorial", name: "Editorial", description: "Newspaper and magazine storytelling with disciplined columns", colors: ["#211D19", "#B63C2E", "#F5F0E6"], gradient: ["#F5F0E6", "#E7DFD1"], transition: "fade", motif: "table", composition: "editorial", theme: "newsroom", backdropVariants: ["broadsheet", "magazine", "columns", "clippings", "press"] },
  { id: "forest", name: "Forest", description: "Sustainability and natural systems", colors: ["#17352B", "#2F855A", "#F2F7F3"] },
  { id: "midnight", name: "Midnight", description: "Cinematic dark presentations", colors: ["#090D18", "#5B8CFF", "#171D2D"] },
  { id: "monochrome", name: "Monochrome", description: "Minimal black-and-white clarity", colors: ["#171717", "#737373", "#FAFAFA"] },
  { id: "ocean", name: "Ocean", description: "Calm research and scientific briefs", colors: ["#123047", "#0891B2", "#F0F9FF"] },
  { id: "paper", name: "Paper", description: "Notebook research with pencil marks, ruled pages, and margin notes", colors: ["#25231F", "#637D52", "#F7F1DF"], gradient: ["#F7F1DF", "#E9DFC7"], transition: "fade", motif: "clean", theme: "notebook", backdropVariants: ["ruled", "graph", "spiral", "kraft", "field-notes"] },
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
  { id: "dashboard-pro", name: "Dashboard Pro", description: "Dark analytical control room with green and orange signal colors", colors: ["#EDF7F1", "#4ADE80", "#0D1617"], gradient: ["#0D1617", "#142527"], transition: "push", motif: "chart", theme: "dashboard", backdropVariants: ["matrix", "kpi", "terminal", "market", "signal"] },
  { id: "science-spectrum", name: "Science Spectrum", description: "Research gradients, tables, and evidence charts", colors: ["#134E4A", "#8B5CF6", "#F0FDFA"], gradient: ["#F0FDFA", "#F5F3FF"], transition: "wipe", motif: "table" },
  { id: "impact-report", name: "Impact Report", description: "Human-centered imagery with metric storytelling", colors: ["#1C1917", "#16A34A", "#FAFAF9"], gradient: ["#F0FDF4", "#FAFAF9"], transition: "fade", motif: "image" },
  { id: "science-studio", name: "Science Studio", description: "Cinematic laboratory photography with elegant type", colors: ["#E8F7FA", "#56CFE1", "#070B12"], gradient: ["#070B12", "#122B3A"], transition: "fade", motif: "image", composition: "photo-right" },
  { id: "digital-pulse", name: "Digital Pulse", description: "Energetic maker photography with electric highlights", colors: ["#F8FAFC", "#C7F43B", "#17191C"], gradient: ["#17191C", "#334155"], transition: "push", motif: "image", composition: "photo-left" },
  { id: "eco-sketchbook", name: "Eco Sketchbook", description: "Playful hand-drawn sustainability storytelling", colors: ["#1F2937", "#4FA8A5", "#FFFDFC"], gradient: ["#FFFDFC", "#FDE3D4"], transition: "wipe", motif: "clean", composition: "botanical" },
  { id: "social-workshop", name: "Social Workshop", description: "Documentary collage for learning and collaboration", colors: ["#FFFDF8", "#F5C542", "#292524"], gradient: ["#292524", "#57534E"], transition: "split", motif: "image", composition: "collage" },
  { id: "environmental-fieldwork", name: "Environmental Fieldwork", description: "Optimistic field photography with a torn-paper edge", colors: ["#12372A", "#91B29A", "#FFFEFB"], gradient: ["#FFFEFB", "#EAF4EC"], transition: "wipe", motif: "image", composition: "torn-photo" },
  { id: "personal-brand", name: "Personal Brand", description: "Fashion editorial with strong asymmetric typography", colors: ["#09090B", "#0B5CAD", "#F7F3F2"], gradient: ["#F7F3F2", "#EEE9E7"], transition: "cover", motif: "image", composition: "editorial" },
  { id: "botanical-noir", name: "Botanical Noir", description: "Forest canopy, botanical forms, and calm natural contrast", colors: ["#F0F8E8", "#A8D67B", "#102016"], gradient: ["#102016", "#1B3A25"], transition: "fade", motif: "image", composition: "botanical", theme: "forest", backdropVariants: ["canopy", "fern", "trunks", "moss", "night-grove"] },
  { id: "nature-balance", name: "Nature Balance", description: "Immersive full-bleed nature photography and serif details", colors: ["#F7FFF9", "#A8D5BA", "#0D2C22"], gradient: ["#0D2C22", "#0B3B50"], transition: "cover", motif: "image", composition: "full-bleed" },
  { id: "storytelling-lab", name: "Storytelling Lab", description: "Minimal cream editorial with a framed documentary image", colors: ["#111111", "#2C8C8C", "#F7F3EB"], gradient: ["#F7F3EB", "#EEE8DC"], transition: "push", motif: "image", composition: "minimal-frame" },
  { id: "agricultural-motion", name: "Agricultural Motion", description: "Dynamic aerial agriculture imagery and lime accents", colors: ["#FFFFFF", "#A8C96A", "#263A18"], gradient: ["#263A18", "#566B25"], transition: "push", motif: "image", composition: "full-bleed" },
  { id: "cultural-heritage", name: "Cultural Heritage", description: "Museum-like cinematic storytelling with antique gold", colors: ["#F6ECD8", "#B88A3B", "#17120F"], gradient: ["#17120F", "#3B2419"], transition: "fade", motif: "image", composition: "heritage" },
  { id: "cyan-infographic", name: "Cyan Infographic", description: "Clear modular information design with contained diagrams", colors: ["#083344", "#0EA5C9", "#F4FCFD"], gradient: ["#F4FCFD", "#D7F3F7"], transition: "wipe", motif: "chart", composition: "infographic", theme: "infographic", backdropVariants: ["modules", "index", "map", "cards", "signals"] },
  { id: "growth-momentum", name: "Growth Momentum", description: "Dark growth narrative with luminous chart direction", colors: ["#F8FAFC", "#38BDF8", "#07131C"], gradient: ["#07131C", "#0C4A6E"], transition: "push", motif: "chart", composition: "infographic" },
  { id: "home-investment", name: "Home Investment", description: "Warm property finance with approachable infographics", colors: ["#312E2B", "#F0645A", "#FCFAF7"], gradient: ["#FCFAF7", "#F4E8DA"], transition: "split", motif: "table", composition: "minimal-frame" },
  { id: "museum-editorial", name: "Museum Editorial", description: "Refined cultural layouts with archival framing", colors: ["#F2E7D2", "#9D6B2F", "#15110E"], gradient: ["#15110E", "#30221B"], transition: "fade", motif: "image", composition: "heritage" },
  { id: "itau", name: "Itaú", description: "Accessible orange-and-navy financial product clarity", colors: ["#FFFFFF", "#EC7000", "#001E60"], gradient: ["#001E60", "#173B80"], transition: "fade", motif: "clean", theme: "itau", backdropVariants: ["arc", "cards", "path", "sun", "signal"] },
  { id: "tron", name: "Tron", description: "Original neon-grid future interface; choose cyan, green, or orange light", colors: ["#EAF9FF", "#38DDF5", "#051016"], gradient: ["#051016", "#0A2432"], transition: "push", motif: "chart", theme: "tron", backdropVariants: ["grid", "circuit", "portal", "hud", "speed"], accentOptions: [{ id: "cyan", label: "Cyan light", color: "#38DDF5" }, { id: "green", label: "Green light", color: "#66FF99" }, { id: "orange", label: "Orange light", color: "#FF9A3D" }] },
  { id: "minecraft", name: "Minecraft", description: "Original block-world system for playful learning and planning", colors: ["#F7F3D9", "#78B849", "#24351F"], gradient: ["#24351F", "#426F38"], transition: "wipe", motif: "clean", theme: "blockworld", backdropVariants: ["grass", "cave", "craft", "sunset", "map"] },
  { id: "mckinsey", name: "McKinsey", description: "Executive evidence hierarchy with restrained blue analytical framing", colors: ["#12263F", "#1D5D9B", "#FFFFFF"], gradient: ["#FFFFFF", "#EDF3F8"], transition: "fade", motif: "chart", theme: "consulting", backdropVariants: ["thesis", "evidence", "matrix", "decision", "appendix"] },
  { id: "accenture", name: "Accenture", description: "Bold future-facing strategy with high-contrast purple signals", colors: ["#1A1A1A", "#A100FF", "#F7F4FA"], gradient: ["#F7F4FA", "#EBDDFF"], transition: "push", motif: "chart", theme: "consulting", backdropVariants: ["signal", "path", "momentum", "system", "outcome"] },
  { id: "bcp", name: "BCP", description: "Practical transformation framing with warm, structured business cues", colors: ["#172A4D", "#F5B335", "#FCFAF5"], gradient: ["#FCFAF5", "#F2E5C8"], transition: "fade", motif: "table", theme: "consulting", backdropVariants: ["brief", "process", "portfolio", "milestone", "value"] },
  { id: "bain", name: "Bain", description: "Direct recommendation storytelling with a decisive red accent", colors: ["#1D1D1D", "#CC1F2F", "#FFFDFC"], gradient: ["#FFFDFC", "#F5E3E2"], transition: "cover", motif: "chart", theme: "consulting", backdropVariants: ["answer", "tradeoff", "value", "choice", "action"] },
];

export const PRESENTATION_TEMPLATE_GROUPS = [
  {
    label: "Essential",
    ids: ["atlas", "monochrome", "boardroom", "paper", "studio", "ocean"],
  },
  {
    label: "Editorial & cultural",
    ids: ["editorial", "storytelling-lab", "personal-brand", "museum-editorial", "cultural-heritage", "social-workshop", "eco-sketchbook", "plum"],
  },
  {
    label: "Photographic",
    ids: ["science-studio", "digital-pulse", "environmental-fieldwork", "nature-balance", "agricultural-motion", "botanical-noir", "photo-story", "cinematic-frame", "horizon", "impact-report", "sunrise", "bloom"],
  },
  {
    label: "Data & evidence",
    ids: ["dashboard-pro", "data-wave", "financial-pulse", "home-investment", "growth-momentum", "cyan-infographic", "science-spectrum", "glacier", "executive-gradient", "cyber-grid"],
  },
  {
    label: "Expressive",
    ids: ["aurora", "neon-flow", "prism", "velocity", "ember", "orbit", "aurora-glass", "editorial-motion", "signal", "forest", "midnight"],
  },
  { label: "Signature", ids: ["itau", "tron", "minecraft"] },
  { label: "Consulting", ids: ["mckinsey", "accenture", "bcp", "bain"] },
] as const;

// Slide Designer intentionally starts with a small, contrast-reviewed set. The
// complete catalog remains available in the broader presentation artifacts.
export const CURATED_SLIDE_DESIGNER_TEMPLATE_GROUPS = [
  { label: "Business & evidence", ids: ["atlas", "boardroom"] },
  { label: "Editorial", ids: ["paper", "editorial"] },
  { label: "Visual storytelling", ids: ["botanical-noir"] },
  { label: "Data & systems", ids: ["dashboard-pro", "cyan-infographic"] },
  { label: "Signature", ids: ["itau", "tron", "minecraft"] },
  { label: "Consulting", ids: ["mckinsey", "accenture", "bcp", "bain"] },
] as const;

export function templatesInGroup(ids: readonly string[]): PresentationTemplate[] {
  return ids.map((id) => templateById(id));
}

export function templateById(id: string): PresentationTemplate {
  return PRESENTATION_TEMPLATES.find((template) => template.id === id) ?? PRESENTATION_TEMPLATES[0];
}
