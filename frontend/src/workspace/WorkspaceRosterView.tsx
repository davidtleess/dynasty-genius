import { useEffect, useRef, useState } from "react";
import type { MarketRanksAvailable } from "../lib/api";
import { rankText } from "../market-ranks/MarketRanks";
import { formatAvailablePoints } from "../research/availableHelpers";
import { headshotSrc, PlayerIdentity } from "../ui/PlayerIdentity";
import type { WorkspaceOrder, WorkspacePlayer } from "./types";
import { WorkspaceInspector } from "./WorkspaceInspector";
import { WorkspaceRosterGroups } from "./WorkspaceRosterGroups";
import { sortWorkspacePlayers } from "./workspaceData";
import "./WorkspaceRosterView.css";

type Props = {
  roster: WorkspacePlayer[];
  available: WorkspacePlayer[];
  data: MarketRanksAvailable;
  nowLabel: string;
  futureLabel: string;
  forecastsReady: boolean;
  forecastError: boolean;
  watchNotice?: string | null;
  onWatch: (player: WorkspacePlayer) => void;
  onCompare: (player: WorkspacePlayer) => void;
  onComparePair: (rosterId: string, availableId: string) => void;
};
const orders: { value: WorkspaceOrder; label: string }[] = [
  { value: "ours", label: "Our rank" },
  { value: "market", label: "Market rank" },
  { value: "gap", label: "Rank difference" },
  { value: "now", label: "This season" },
  { value: "future", label: "Future" },
  { value: "name", label: "Name" },
];
function useDesktopInspector() {
  const [desktop, setDesktop] = useState(
    () => window.matchMedia?.("(min-width: 85rem)").matches ?? false,
  );
  useEffect(() => {
    const query = window.matchMedia?.("(min-width: 85rem)");
    if (!query) return;
    const update = () => setDesktop(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  return desktop;
}

function Alternatives({
  props,
  position,
  initialRosterId,
  onBack,
  hasSelectedPlayer,
}: {
  props: Props;
  position: string;
  initialRosterId: string;
  onBack: () => void;
  hasSelectedPlayer: boolean;
}) {
  const [rosterId, setRosterId] = useState(initialRosterId);
  const [order, setOrder] = useState<WorkspaceOrder>("ours");
  const [query, setQuery] = useState("");
  const roster = props.roster.filter((p) => p.position === position);
  const chosen = roster.find((p) => p.id === rosterId) ?? null;
  const candidates = props.available.filter(
    (p) =>
      p.ownership === "available" &&
      p.position === position &&
      p.name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()),
  );
  const sorted = sortWorkspacePlayers(candidates, order);
  const rows = [...sorted.ranked, ...sorted.missing];
  const points = (value: number | null | undefined) =>
    value == null ? "No forecast" : `${formatAvailablePoints(value)} pts`;
  return (
    <section
      className="dg-roster-alternatives"
      aria-label={`Available ${position} alternatives`}
    >
      <button type="button" className="dg-roster-view__text-action" onClick={onBack}>
        {hasSelectedPlayer ? "Back to roster player" : "Back to roster"}
      </button>
      <h2>Available {position} alternatives</h2>
      <p>
        Unowned players from the relevant available pool in your saved league snapshot.
        Choose the player and roster spot you want to compare.
      </p>
      <label>
        Compare against
        <select
          aria-label="Compare against"
          value={chosen?.id ?? ""}
          onChange={(e) => setRosterId(e.target.value)}
        >
          <option value="">Choose your roster player</option>
          {roster.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      {chosen && (
        <section
          className="dg-roster-alternatives__incumbent"
          aria-label="Your comparison player"
        >
          <p className="dg-roster-view__note">Your comparison player</p>
          <PlayerIdentity
            name={chosen.name}
            team={chosen.team ?? ""}
            position={chosen.position}
            imageSrc={headshotSrc(chosen.id)}
            imageStatus="available"
          />
          <div className="dg-roster-alternatives__ranks">
            <span>
              Our rank <strong>{rankText(chosen.rank?.our_rank ?? null)}</strong>
            </span>
            <span>
              Market <strong>{rankText(chosen.rank?.market_rank ?? null)}</strong>
            </span>
          </div>
          <p className="dg-roster-view__note">
            {props.nowLabel}: {points(chosen.forecast?.now_points)} ·{" "}
            {props.futureLabel}: {points(chosen.forecast?.future_points)}
          </p>
        </section>
      )}
      {!props.forecastsReady ? (
        <p role={props.forecastError ? "alert" : "status"}>
          {props.forecastError
            ? "Available players could not be matched to this ranking snapshot. Reload to try again."
            : "Loading available players…"}
        </p>
      ) : (
        <>
          <label>
            Find an alternative
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Player name"
            />
          </label>
          <label>
            Order alternatives
            <select
              aria-label="Order alternatives"
              value={order}
              onChange={(e) => setOrder(e.target.value as WorkspaceOrder)}
            >
              {orders.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <p className="dg-roster-view__note">
            {rows.length} matching players in this pool. Missing readings remain
            visible. This ordering does not establish a pickup advantage.
          </p>
          <ul className="dg-roster-alternatives__list">
            {rows.map((p) => (
              <li key={p.id}>
                <PlayerIdentity
                  name={p.name}
                  team={p.team ?? ""}
                  position={p.position}
                  imageSrc={headshotSrc(p.id)}
                  imageStatus="available"
                />
                <div className="dg-roster-alternatives__ranks">
                  <span>
                    Our rank <strong>{rankText(p.rank?.our_rank ?? null)}</strong>
                  </span>
                  <span>
                    Market <strong>{rankText(p.rank?.market_rank ?? null)}</strong>
                  </span>
                </div>
                <div className="dg-roster-alternatives__points">
                  <span>
                    {props.nowLabel}: {points(p.forecast?.now_points)}
                  </span>
                  <span>
                    {props.futureLabel}: {points(p.forecast?.future_points)}
                  </span>
                </div>
                {p.forecast?.starting_estimate && (
                  <p className="dg-roster-view__note">Starting estimate</p>
                )}
                <div className="dg-roster-alternatives__actions">
                  <button
                    type="button"
                    disabled={!chosen}
                    aria-label={`Compare ${p.name}${chosen ? ` with ${chosen.name}` : " — choose a roster player"}`}
                    onClick={() => {
                      if (chosen) props.onComparePair(chosen.id, p.id);
                    }}
                  >
                    Compare
                  </button>
                  <button
                    type="button"
                    aria-label={`${p.watched ? "Unwatch" : "Watch"} ${p.name}`}
                    onClick={() => props.onWatch(p)}
                  >
                    {p.watched ? "Unwatch" : "Watch"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
          {rows.length === 0 && (
            <p>No {position} players in this available pool match your search.</p>
          )}
        </>
      )}
    </section>
  );
}

export function WorkspaceRosterView(props: Props) {
  const [order, setOrder] = useState<WorkspaceOrder>("ours");
  const [position, setPosition] = useState("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [alternatives, setAlternatives] = useState<{
    position: string;
    rosterId: string;
  } | null>(null);
  const desktop = useDesktopInspector();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const asideRef = useRef<HTMLElement>(null);
  const previousDesktopRef = useRef(desktop);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const selected = props.roster.find((p) => p.id === selectedId) ?? null;
  const open = selected !== null || alternatives !== null;
  const rows = props.roster.filter(
    (p) => position === "all" || p.position === position,
  );
  const paired = props.data.coverage.roster_common_players;
  function rememberFocus() {
    if (document.activeElement instanceof HTMLElement)
      returnFocusRef.current = document.activeElement;
  }
  function select(p: WorkspacePlayer) {
    rememberFocus();
    setSelectedId(p.id);
    setAlternatives(null);
  }
  function close() {
    dialogRef.current?.close();
    setSelectedId(null);
    setAlternatives(null);
    if (returnFocusRef.current?.isConnected) returnFocusRef.current.focus();
  }
  useEffect(() => {
    const dialog = dialogRef.current;
    if (desktop && open && !previousDesktopRef.current)
      asideRef.current?.focus({ preventScroll: true });
    previousDesktopRef.current = desktop;
    if (!desktop && open && dialog && !dialog.open) dialog.showModal();
    return () => {
      if (dialog?.open) dialog.close();
    };
  }, [desktop, open]);
  const inspector = alternatives ? (
    <Alternatives
      key={`${alternatives.position}-${alternatives.rosterId}`}
      props={props}
      position={alternatives.position}
      initialRosterId={alternatives.rosterId}
      hasSelectedPlayer={selected !== null}
      onBack={() => {
        setAlternatives(null);
        if (!selected) close();
      }}
    />
  ) : selected ? (
    <WorkspaceInspector
      player={selected}
      data={props.data}
      nowLabel={props.nowLabel}
      futureLabel={props.futureLabel}
      onWatch={props.onWatch}
      onCompare={props.onCompare}
      onAlternatives={(p) => setAlternatives({ position: p.position, rosterId: p.id })}
    />
  ) : (
    <div className="dg-roster-view__empty">
      <h2>Your player, in context</h2>
      <p>
        Choose a player to see our rank beside the market, review his forecast, and find
        available alternatives.
      </p>
      <p className="dg-roster-view__note">
        A rank difference is a reason to investigate. It is not proof the market is
        wrong.
      </p>
    </div>
  );
  return (
    <div className="dg-roster-view">
      <section className="dg-roster-view__board" aria-label="Your roster by position">
        <div className="dg-roster-view__intro">
          <h1>Your roster</h1>
          {props.watchNotice && <p role="status">{props.watchNotice}</p>}
          <p>
            {props.data.coverage.roster_players} players on your roster. {paired} have
            both our rank and a market rank, among the same{" "}
            {props.data.coverage.common_players} players.
          </p>
          <p className="dg-roster-view__note">
            Start with a position group. Select a player to explore the difference and
            compare an available alternative.
          </p>
          <div className="dg-roster-view__filters">
            <label>
              Order within each position
              <select
                aria-label="Order within each position"
                value={order}
                onChange={(e) => setOrder(e.target.value as WorkspaceOrder)}
              >
                {orders.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Position
              <select
                aria-label="Position"
                value={position}
                onChange={(e) => {
                  setPosition(e.target.value);
                  setSelectedId(null);
                  setAlternatives(null);
                }}
              >
                <option value="all">All positions</option>
                {[...new Set(props.roster.map((p) => p.position))].sort().map((p) => (
                  <option key={p} value={p}>
                    {p || "Unknown"}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
        <WorkspaceRosterGroups
          rows={rows}
          data={props.data}
          nowLabel={props.nowLabel}
          futureLabel={props.futureLabel}
          order={order}
          selectedId={selectedId}
          onSelect={select}
          onWatch={props.onWatch}
          showDepth={position === "all" || position === "QB"}
          onFindAlternatives={(pos) => {
            rememberFocus();
            setAlternatives({ position: pos, rosterId: "" });
          }}
        />
        {!props.forecastsReady && (
          <p
            className="dg-roster-view__notice"
            role={props.forecastError ? "alert" : "status"}
          >
            {props.forecastError
              ? "Forecasts could not be matched to this ranking snapshot. Your roster ranks remain available."
              : "Loading your player forecasts…"}
          </p>
        )}
        <details className="dg-roster-view__method">
          <summary>How these ranks compare</summary>
          <p>{props.data.basis.summary}</p>
          <p>{props.data.basis.scoring_note}</p>
          <p>{props.data.basis.market_proxy_note}</p>
          <p>
            Rank gaps are places, not price differences. Model points and FantasyCalc
            Market Value use different units. Equal values share a tied rank;
            alphabetical order within a tie does not express a preference.
          </p>
        </details>
      </section>
      {desktop ? (
        <aside
          ref={asideRef}
          tabIndex={-1}
          className="dg-roster-view__inspector"
          aria-label="Roster player details"
        >
          {open && (
            <button className="dg-roster-view__close" type="button" onClick={close}>
              Clear selection
            </button>
          )}
          {inspector}
        </aside>
      ) : (
        open && (
          <dialog
            ref={dialogRef}
            className="dg-roster-view__dialog"
            aria-label="Roster player details"
            onCancel={(e) => {
              e.preventDefault();
              close();
            }}
          >
            <div className="dg-roster-view__dialog-head">
              {alternatives && selected ? (
                <button type="button" onClick={() => setAlternatives(null)}>
                  Back to selected player
                </button>
              ) : (
                <span>Roster player</span>
              )}
              <button type="button" aria-label="Close player details" onClick={close}>
                Close
              </button>
            </div>
            {inspector}
          </dialog>
        )
      )}
    </div>
  );
}
