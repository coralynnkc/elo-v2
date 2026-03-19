import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { loadData, getTeamMatches } from "../utils/data";

export default function Leaderboard() {
  const [data, setData] = useState(null);
  const [expanded, setExpanded] = useState(new Set());

  useEffect(() => {
    loadData().then(setData);
  }, []);

  function toggle(teamName) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(teamName) ? next.delete(teamName) : next.add(teamName);
      return next;
    });
  }

  if (!data) return <div className="loading">Loading…</div>;

  const { teams, rawHistory } = data;

  return (
    <div className="page">
      <header className="page-header">
        <h1>Policy Debate Rankings</h1>
        <p className="subtitle">
          TrueSkill ratings · 2025–26 season · Northwestern, UK, Gonzaga, Wake,
          Georgetown, Texas, ADA
        </p>
      </header>

      <div className="table-wrap">
        <table className="leaderboard-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Team</th>
              <th className="align-right">Rating</th>
              <th className="align-right">σ</th>
              <th className="align-right">Rounds</th>
              <th className="align-right">Conservative</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {teams.map((team, i) => {
              const isExpanded = expanded.has(team.Team);
              const top5 = isExpanded
                ? getTeamMatches(rawHistory, team.Team)
                    .sort((a, b) => b.absDelta - a.absDelta)
                    .slice(0, 5)
                : [];

              return (
                <React.Fragment key={team.Team}>
                  <tr
                    className={`team-row${isExpanded ? " is-expanded" : ""}`}
                    onClick={() => toggle(team.Team)}
                  >
                    <td className="rank">{i + 1}</td>
                    <td className="team-name">
                      <Link
                        to={`/team/${encodeURIComponent(team.Team)}`}
                        onClick={(e) => e.stopPropagation()}
                      >
                        {team.Team}
                      </Link>
                    </td>
                    <td className="num">{team.Mu}</td>
                    <td className="num dim">{team.Sigma}</td>
                    <td className="num">{team.Aff_Rounds + team.Neg_Rounds}</td>
                    <td className="num">{team.Conservative}</td>
                    <td className="chevron">{isExpanded ? "▲" : "▼"}</td>
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
                                      to={`/team/${encodeURIComponent(m.opponent)}`}
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
