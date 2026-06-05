type Rookie = {
  confidence: string;
};

export function ConfidenceBinding({ rookie }: { rookie: Rookie }) {
  return <span>{rookie.confidence}</span>;
}
