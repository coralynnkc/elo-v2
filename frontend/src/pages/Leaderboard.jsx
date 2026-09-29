import React, { useState, useEffect } from "react";
import { Link, Navigate, NavLink, useParams } from "react-router-dom";
import { SEASONS, loadData, getTeamMatches, getTournaments } from "../utils/data";

const COLUMNS = [
  { key: "rank", label: "#", value: (r) => r.order, defaultDir: "asc", className: "rank" },
  { key: "team", label: "Team", value: (r) => r.team.Team, defaultDir: "asc" },
  { key: "mu", label: "Rating", value: (r) => r.team.Mu, defaultDir: "desc", numeric: true,
    title: "μ: the model's best estimate of team strength" },
  { key: "sigma", label: "σ", value: (r) => r.team.Sigma, defaultDir: "asc", numeric: true,
    className: "col-sigma", title: "σ: uncertainty in the rating; shrinks as a team debates more" },
  { key: "rounds", label: "Rounds", value: (r) => r.team.Aff_Rounds + r.team.Neg_Rounds,
    defaultDir: "desc", numeric: true, className: "col-rounds" },
  { key: "conservative", label: "Conservative", value: (r) => r.team.Conservative,
    defaultDir: "desc", numeric: true, title: "μ − 3σ: a rating the team very likely exceeds" },
];

export default function Leaderboard() {
  const { season } = useParams();
  const [data, setData] = useState(null);
  const [expanded, setExpanded] = useState(new Set());
  const [sort, setSort] = useState({ key: "rank", dir: "asc" });
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    if (!SEASONS[season]) return;
    setExpanded(new Set());
    loadData(season).then((d) => setData({ season, ...d }));
  }, [season]);

  function toggle(teamName) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(teamName) ? next.delete(teamName) : next.add(teamName);
      return next;
    });
  }

  if (!SEASONS[season]) return <Navigate to="/" replace />;
  if (!data || data.season !== season) return <div className="loading">Loading…</div>;

  const { teams, rawHistory } = data;
  const tournaments = getTournaments(rawHistory);

  // Rank stays the μ rank among ranked teams whatever column the table is sorted by.
  // Unranked teams (too few tournaments) get no rank and sort after ranked ones.
  const ranked = teams.filter((t) => t.Ranked);
  const unranked = teams.filter((t) => !t.Ranked);
  const rows = ranked.map((team, i) => ({ team, rank: i + 1, order: i }));
  if (showAll) {
    unranked.forEach((team, i) => rows.push({ team, rank: null, order: ranked.length + i }));
  }
  const col = COLUMNS.find((c) => c.key === sort.key);
  rows.sort((a, b) => {
    const va = col.value(a), vb = col.value(b);
    const cmp = typeof va === "string" ? va.localeCompare(vb) : va - vb;
    return sort.dir === "asc" ? cmp : -cmp;
  });

  function sortBy(key) {
    setSort((prev) =>
      prev.key === key
        ? { key, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { key, dir: COLUMNS.find((c) => c.key === key).defaultDir }
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Policy Debate Rankings</h1>
        <nav className="season-nav">
          {Object.entries(SEASONS).map(([key, s]) => (
            <NavLink key={key} to={`/${key}`}>
              {s.label}
            </NavLink>
          ))}
        </nav>
        <p className="subtitle">
          TrueSkill Through Time ratings · {SEASONS[season].label} season · {tournaments.join(", ")}
        </p>
        {tournaments.length < 2 && (
          <p className="provisional">
            Provisional — based on one tournament. Ratings and σ will settle as more
            tournaments are added.
          </p>
        )}
      </header>

      {unranked.length > 0 && (
        <label className="table-toggle">
          <input
            type="checkbox"
            checked={showAll}
            onChange={(e) => setShowAll(e.target.checked)}
          />
          Show unranked teams
          <span className="dim">
            {" "}({unranked.length} with too few tournaments)
          </span>
        </label>
      )}

      <div className="table-wrap">
        <table className="leaderboard-table">
          <thead>
            <tr>
              {COLUMNS.map((c) => {
                const active = sort.key === c.key;
                return (
                  <th
                    key={c.key}
                    className={`${c.className ?? ""}${c.numeric ? " align-right" : ""}`}
                    aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
                    title={c.title}
                  >
                    <button
                      type="button"
                      className={`sort-header${active ? " is-active" : ""}`}
                      onClick={() => sortBy(c.key)}
                    >
                      {c.label}
                      <span className="sort-arrow" aria-hidden="true">
                        {active ? (sort.dir === "asc" ? "↑" : "↓") : ""}
                      </span>
                    </button>
                  </th>
                );
              })}
              <th>
                <span className="visually-hidden">Details</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ team, rank }) => {
              const isExpanded = expanded.has(team.Team);
              const top5 = isExpanded
                ? getTeamMatches(rawHistory, team.Team)
                    .sort((a, b) => b.absDelta - a.absDelta)
                    .slice(0, 5)
                : [];

              return (
                <React.Fragment key={team.Team}>
                  <tr
                    className={`team-row${isExpanded ? " is-expanded" : ""}${rank ? "" : " is-unranked"}`}
                    onClick={() => toggle(team.Team)}
                  >
                    <td className="rank" title={rank ? undefined : `Unranked: ${team.Tournaments} tournament${team.Tournaments === 1 ? "" : "s"}`}>
                      {rank ?? "–"}
                    </td>
                    <td className="team-name">
                      <Link
                        to={`/${season}/team/${encodeURIComponent(team.Team)}`}
                        onClick={(e) => e.stopPropagation()}
                      >
                        {team.Team}
                      </Link>
                    </td>
                    <td className="num">{team.Mu.toFixed(3)}</td>
                    <td className="num dim col-sigma">{team.Sigma.toFixed(3)}</td>
                    <td className="num col-rounds">{team.Aff_Rounds + team.Neg_Rounds}</td>
                    <td className="num">{team.Conservative.toFixed(3)}</td>
                    <td className="chevron">
                      <button
                        type="button"
                        aria-expanded={isExpanded}
                        aria-label={`${isExpanded ? "Hide" : "Show"} top rounds for ${team.Team}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          toggle(team.Team);
                        }}
                      >
                        {isExpanded ? "▲" : "▼"}
                      </button>
                    </td>
                  </tr>

                  {isExpanded && (
                    <tr className="expanded-row">
                      <td colSpan={7}>
                        <div className="expanded-content">
                          <p className="exp-label">
                            Top 5 most consequential rounds
                          </p>
                          <table className="mini-table">
                            <thead>
                              <tr>
                                <th>Round</th>
                                <th>Opponent</th>
                                <th>Side</th>
                                <th>Result</th>
                                <th className="align-right">Δ Rating</th>
                              </tr>
                            </thead>
                            <tbody>
                              {top5.map((m, j) => (
                                <tr key={j}>
                                  <td>{m.roundDisplay}</td>
                                  <td>
                                    <Link
                                      to={`/${season}/team/${encodeURIComponent(m.opponent)}`}
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      {m.opponent}
                                    </Link>
                                  </td>
                                  <td>{m.side}</td>
                                  <td className={m.win ? "win" : "loss"}>
                                    {m.win ? "Win" : "Loss"}
                                  </td>
                                  <td
                                    className={`num ${m.delta > 0 ? "positive" : "negative"}`}
                                  >
                                    {m.delta > 0 ? "+" : ""}
                                    {m.delta.toFixed(3)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
