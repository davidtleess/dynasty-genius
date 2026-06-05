type Card = {
  recommended_action: string;
};

export function RecommendedActionBinding({ card }: { card: Card }) {
  return <span>{card.recommended_action}</span>;
}
