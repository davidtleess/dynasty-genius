type Card = {
  roster_action: string;
};

export function RosterActionBinding({ card }: { card: Card }) {
  return <span>{card.roster_action}</span>;
}
