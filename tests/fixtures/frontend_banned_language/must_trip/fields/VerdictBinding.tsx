type Evaluation = {
  verdict: string;
};

export function VerdictBinding({ evaluation }: { evaluation: Evaluation }) {
  return <span>{evaluation.verdict}</span>;
}
