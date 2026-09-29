import React, { useState, useEffect } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { SEASONS, loadData, getTeamMatches } from "../utils/data";
import SeasonHeader from "../components/SeasonHeader";

const COLUMNS = [
  { key: "rank", label: "#", value: (r) => r.order, defaultDir: "asc", className: "rank" },
  { key: "team", label: "Team", value: (r) => r.team.Team, defaultDir: "asc" },
  { key: "mu", label: "Rating", value: (r) => r.team.Mu, defaultDir: "desc", numeric: true,
    tip: "μ: the model's best estimate of team strength, fitted on the whole season" },
  { key: "sigma", label: <span className="greek">σ</span>, value: (r) => r.team.Sigma, defaultDir: "asc", numeric: true,
    className: "col-sigma", tip: "σ: uncertainty in the rating. It shrinks as a team debates more" },
  { key: "rounds", label: "Rounds", value: (r) => r.team.Aff_Rounds + r.team.Neg_Rounds,
    defaultDir: "desc", numeric: true, className: "col-rounds", tip: "Decisive rounds this season, prelims and elims" },
  { key: "conservative", label: "Conservative", value: (r) => r.team.Conservative,
    defaultDir: "desc", numeric: true, tip: "μ − 3σ: a rating the team very likely exceeds. Ranks new teams more cautiously" },
];

export default function Leaderboard() {
  const { season } = useParams();
  const [data, setData] = useState(null);
  const [expanded, setExpanded] = useState(new Set());
  const [sort, setSort] = useState({ key: "rank", dir: "asc" });
  const [showAll, setShowAll] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!SEASONS[season]) return;
    setExpanded(new Set());
    setQuery("");
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

  // Rank stays the μ rank among ranked teams whatever column the table is sorted by.
  // Unranked teams (too few tournaments) get no rank and sort after ranked ones.
  // A search looks through unranked teams too, so any team can be found.
  const ranked = teams.filter((t) => t.Ranked);
  const unranked = teams.filter((t) => !t.Ranked);
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
  const matches = (t) => {
    const text = `${t.Team} ${t.Debaters ?? ""}`.toLowerCase();
    return terms.every((term) => text.includes(term));
  };
  let rows = ranked.map((team, i) => ({ team, rank: i + 1, order: i }));
  if (showAll || terms.length) {
    unranked.forEach((team, i) => rows.push({ team, rank: null, order: ranked.length + i }));
  }
  if (terms.length) rows = rows.filter((r) => matches(r.team));
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
      <SeasonHeader season={season} rawHistory={rawHistory} view="" />

      <details className="explainer">
        <summary>How ratings work</summary>
        <p>
          Each team's <strong>rating (μ)</strong> estimates its strength. A team rated 5
          points higher wins about 80% of the time. <strong>σ</strong> is the uncertainty:
          a team starts wide and narrows as it debates. <strong>Conservative</strong> is
          μ − 3σ, a rating the team very likely exceeds.
        </p>
        <p>
          Ratings use TrueSkill Through Time, which fits the whole season at once, so a
          result at a later tournament also informs the earlier estimates. A team page's
          match history instead shows the rating as it stood before each round, using
          earlier rounds only, so the leaderboard μ can differ from the last After.
        </p>
        <p>
          From 2025–26 on, teams start from their debaters' ratings the season before,
          widened for change over the summer. A team is ranked once it has debated at two
          tournaments.
        </p>
      </details>

      <div className="table-controls">
        <input
          type="search"
          className="search-box"
          placeholder="Search teams or debaters"
          aria-label="Search teams or debaters"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
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
      </div>

      <div className="table-wrap">
        <table className="data-table leaderboard-table">
          <thead>
            <tr>
              {COLUMNS.map((c) => {
                const active = sort.key === c.key;
                return (
                  <th
                    key={c.key}
                    className={`${c.className ?? ""}${c.numeric ? " align-right" : ""}${c.tip ? " has-tip" : ""}`}
                    aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
                    data-tip={c.tip}
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
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} className="empty">No teams match “{query}”</td>
              </tr>
            )}
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
                          <table className="data-table compact">
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
                                    {m.delta.toFixed(2)}
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
