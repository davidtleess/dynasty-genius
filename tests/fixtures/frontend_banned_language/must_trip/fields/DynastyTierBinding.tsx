type Card = {
  dynasty_tier: string;
};

export function DynastyTierBinding({ card }: { card: Card }) {
  return <span>{card.dynasty_tier}</span>;
}
