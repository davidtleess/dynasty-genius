// League Pulse non-ready states. Neutral, non-blank, banned-language-clean copy.

export function LoadingState() {
  return <p className="dg-league-pulse__state">Loading League Pulse…</p>;
}

export function UnavailableState() {
  return (
    <p className="dg-league-pulse__state">
      League Pulse unavailable. The league snapshot could not be loaded right now.
    </p>
  );
}

export function ParseErrorState() {
  return (
    <p className="dg-league-pulse__state">
      Could not read League Pulse. The response was not in the expected shape.
    </p>
  );
}
