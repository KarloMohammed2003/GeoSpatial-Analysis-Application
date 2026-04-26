import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { api } from "../api";
import { Spinner }      from "../components/Spinner";
import { ErrorMessage } from "../components/ErrorMessage";

const METRICS = [
  { key: "median_income", label: "Median income",      rankKey: "best_income",        fmt: (v) => v ? `$${v.toLocaleString()}` : "—" },
  { key: "rpp",           label: "Price parity index", rankKey: "best_rpp",           fmt: (v) => v ?? "—" },
  { key: "walk_score",    label: "Walk score",         rankKey: "best_walk_score",    fmt: (v) => v ?? "—" },
  { key: "transit_score", label: "Transit score",      rankKey: "best_transit_score", fmt: (v) => v ?? "—" },
  { key: "bike_score",    label: "Bike score",         rankKey: "best_bike_score",    fmt: (v) => v ?? "—" },
];

export default function Compare() {
  const [searchParams]    = useSearchParams();
  const navigate          = useNavigate();
  const ids               = searchParams.get("ids") || "";
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  useEffect(() => {
    if (!ids) return;
    setLoading(true);
    api.compare.get(ids.split(","))
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [ids]);

  if (loading) return <Spinner />;
  if (error)   return <ErrorMessage message={error} />;
  if (!data)   return null;

  const { cities, rankings } = data;

  return (
    <div>
      <button className="back-btn" onClick={() => navigate("/")}>← Back</button>
      <div className="page-header">
        <h1>City comparison</h1>
        <p className="subtitle">Highlighted cells indicate the best value in each category.</p>
      </div>
      <div className="compare-table-wrapper">
        <table className="compare-table">
          <thead>
            <tr>
              <th>Metric</th>
              {cities.map((c) => <th key={c.metro_fips}><button className="city-link" onClick={() => navigate(`/cities/${c.metro_fips}`)}>{c.name}</button></th>)}
            </tr>
          </thead>
          <tbody>
            {METRICS.map((m) => (
              <tr key={m.key}>
                <td className="metric-label">{m.label}</td>
                {cities.map((city) => {
                  const winner = rankings[m.rankKey] === city.metro_fips;
                  return (
                    <td key={city.metro_fips} className={`metric-value${winner ? " winner" : ""}`}>
                      {m.fmt(city[m.key])}
                      {winner && <span className="winner-badge">best</span>}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="compare-notes">
        <p>Price parity: lower is better — 95 means 5% cheaper than the US average.</p>
        <p>Walk/transit/bike scores are 0–100. Source: OpenStreetMap.</p>
      </div>
    </div>
  );
}
