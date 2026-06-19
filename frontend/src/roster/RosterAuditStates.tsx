// Honest non-success states for the Roster Audit surface. Every failure path
// renders descriptive, neutral copy — never a blank/empty surface.

function Notice({ title, body }: { title: string; body: string }) {
  return (
    <div className="dg-roster__state" role="status">
      <p className="dg-roster__state-title">{title}</p>
      <p className="dg-roster__state-body">{body}</p>
    </div>
  );
}

export const LoadingState = () => (
  <Notice title="Loading roster audit" body="Fetching your roster from the model." />
);

export const ConfigErrorState = () => (
  <Notice
    title="Roster not configured"
    body="The league/roster configuration is missing or invalid."
  />
);

export const UnavailableState = () => (
  <Notice
    title="Roster data unavailable"
    body="The roster audit dependency is temporarily unavailable."
  />
);

export const ParseErrorState = () => (
  <Notice
    title="Could not read roster audit"
    body="The response did not match the expected contract."
  />
);

export const EmptyState = () => (
  <Notice
    title="No rostered skill players"
    body="No QB/RB/WR/TE players were returned for your roster."
  />
);
