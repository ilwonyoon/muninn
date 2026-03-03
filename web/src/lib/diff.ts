/**
 * Paragraph-level diff utility for summary change highlighting.
 *
 * Uses LCS (Longest Common Subsequence) to detect added/removed/unchanged
 * paragraphs between two texts split on double-newlines.
 */

export interface DiffParagraph {
  type: "added" | "removed" | "unchanged";
  content: string;
}

/**
 * Split text into paragraphs on double-newline boundaries.
 * Trims empty leading/trailing paragraphs.
 */
function splitParagraphs(text: string): string[] {
  return text
    .split(/\n\n+/)
    .map((p) => p.trim())
    .filter(Boolean);
}

/**
 * Compute the LCS table for two string arrays.
 */
function lcsTable(a: string[], b: string[]): number[][] {
  const m = a.length;
  const n = b.length;
  const dp: number[][] = Array.from({ length: m + 1 }, () =>
    Array(n + 1).fill(0)
  );
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] =
        a[i - 1] === b[j - 1]
          ? dp[i - 1][j - 1] + 1
          : Math.max(dp[i - 1][j], dp[i][j - 1]);
    }
  }
  return dp;
}

/**
 * Compute paragraph-level diff between old and new text.
 *
 * Returns an array of DiffParagraph entries indicating which paragraphs
 * were added, removed, or unchanged.
 */
export function diffParagraphs(
  oldText: string,
  newText: string
): DiffParagraph[] {
  const oldParas = splitParagraphs(oldText);
  const newParas = splitParagraphs(newText);
  const dp = lcsTable(oldParas, newParas);

  const result: DiffParagraph[] = [];
  let i = oldParas.length;
  let j = newParas.length;

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && oldParas[i - 1] === newParas[j - 1]) {
      result.push({ type: "unchanged", content: newParas[j - 1] });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      result.push({ type: "added", content: newParas[j - 1] });
      j--;
    } else {
      result.push({ type: "removed", content: oldParas[i - 1] });
      i--;
    }
  }

  return result.reverse();
}

/**
 * Given the current summary and previous summary, return a Set of
 * paragraph contents that were added or changed (for highlighting).
 */
export function getChangedParagraphs(
  currentSummary: string,
  previousSummary: string
): Set<string> {
  const diff = diffParagraphs(previousSummary, currentSummary);
  const changed = new Set<string>();
  for (const entry of diff) {
    if (entry.type === "added") {
      changed.add(entry.content);
    }
  }
  return changed;
}
