import React from "react";

/**
 * Renders markdown bold syntax (**text**) as <strong> tags
 * This is a private utility only used within the ai-insights feature
 */
export function renderMarkdownBold(text: string): React.ReactNode {
  if (!text) return null;

  // Split on **...** but keep the matched parts
  const parts = text.split(/(\*\*[^*]+\*\*)/g);

  return parts.map((part, idx) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      const inner = part.slice(2, -2); // remove the ** at both ends
      return <strong key={idx}>{inner}</strong>;
    }

    return <span key={idx}>{part}</span>;
  });
}
