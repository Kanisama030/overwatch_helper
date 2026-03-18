const tierStyles: Record<string, { bg: string; text: string }> = {
  S: { bg: '#f27f0d', text: '#221910' },
  A: { bg: '#3b82f6', text: '#fff' },
  B: { bg: '#22c55e', text: '#fff' },
  C: { bg: '#6b7280', text: '#fff' },
  D: { bg: '#ef4444', text: '#fff' },
};

export function TierBadge({ tier }: { tier: string | null }) {
  if (!tier) return null;
  const style = tierStyles[tier] ?? { bg: '#6b7280', text: '#fff' };
  return (
    <span
      className="text-[10px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded"
      style={{ backgroundColor: style.bg, color: style.text }}
    >
      {tier}-TIER
    </span>
  );
}
