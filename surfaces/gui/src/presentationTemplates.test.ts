import { describe, expect, it } from "vitest";
import { PRESENTATION_TEMPLATES, PRESENTATION_TEMPLATE_GROUPS } from "./presentationTemplates";

describe("presentation template catalog", () => {
  it("places every template in one coherent selector group", () => {
    const catalogIds = PRESENTATION_TEMPLATES.map((template) => template.id).sort();
    const groupedIds = PRESENTATION_TEMPLATE_GROUPS.flatMap((group) => [...group.ids]).sort();
    expect(groupedIds).toEqual(catalogIds);
    expect(new Set(groupedIds).size).toBe(groupedIds.length);
  });
});
