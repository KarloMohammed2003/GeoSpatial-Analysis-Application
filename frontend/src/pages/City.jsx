import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { api } from "../api";
import { MetricBadge }  from "../components/MetricBadge";
import { Spinner }      from "../components/Spinner";
import { ErrorMessage } from "../components/ErrorMessage";

export default function City() {
  const { fips } = useParams();
  const navigate  = useNavigate();
  const [city,    setCity]    = useState(null);
  const [trends,  setTrends]  = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [months,  setMonths]  = useState(24);

  useEffect(() => {
    setLoading(true);
    Promise.all([api.cities.get(fips), api.trends.get(fips, months)])
      .then(([c, t]) => { setCity(c); setTrends(t); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [fips, months]);

  if (loading) return <Spinner />;
  if (error)   return <ErrorMessage message={error} />;
  if (!city)   return null;

  const s = trends?.summary;

  return (
    <div>
      <button className="back-btn" onClick={() => navigate(-1)}>← Back</button>
      <div className="page-header">
        <h1>{city.name}</h1>
        <p className="subtitle">Census ({city.income_year}) · BLS ({city.rpp_year}) · Zillow · OSM</p>
      </div>
      <section className="metrics-section">
        <h2>Key metrics</h2>
        <div className="metrics-grid">
          <MetricBadge large label="Median income"  value={city.median_income ? `$${city.median_income.toLocaleString()}` : "—"} />
          <MetricBadge large label="Price parity"   value={city.rpp ?? "—"} hint="100 = US average" />
          <MetricBadge large label="Walk score"     value={city.walk_score    ?? "—"} />
          <MetricBadge large label="Transit score"  value={city.transit_score ?? "—"} />
          <MetricBadge large label="Bike score"     value={city.bike_score    ?? "—"} />
          {s && <MetricBadge large label="Rent to income" value={s.current_rent_to_income ? `${s.current_rent_to_income}%` : "—"} hint="% of monthly gross income" />}
        </div>
      </section>
      {s && (
        <section className="summary-section">
          <h2>Year over year</h2>
          <div className="yoy-grid">
            <div className="yoy-card">
              <span className="yoy-label">Median rent</span>
              <span className="yoy-value">{s.current_rent ? `$${s.current_rent.toLocaleString()}` : "—"}</span>
              {s.yoy_rent_change_pct != null && <span className={`yoy-change ${s.yoy_rent_change_pct >= 0 ? "up" : "down"}`}>{s.yoy_rent_change_pct >= 0 ? "+" : ""}{s.yoy_rent_change_pct}% YoY</span>}
            </div>
            <div className="yoy-card">
              <span className="yoy-label">Median home value</span>
              <span className="yoy-value">{s.current_home_value ? `$${s.current_home_value.toLocaleString()}` : "—"}</span>
              {s.yoy_home_change_pct != null && <span className={`yoy-change ${s.yoy_home_change_pct >= 0 ? "up" : "down"}`}>{s.yoy_home_change_pct >= 0 ? "+" : ""}{s.yoy_home_change_pct}% YoY</span>}
            </div>
          </div>
        </section>
      )}
      {trends?.series?.length > 0 && (
        <section className="chart-section">
          <div className="chart-header">
            <h2>Rent and home value trends</h2>
            <div className="months-toggle">
              {[12,24,60].map((m) => (
                <button key={m} className={`months-btn${months === m ? " active" : ""}`} onClick={() => setMonths(m)}>
                  {m === 60 ? "5yr" : `${m/12}yr`}
                </button>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={trends.series} margin={{ top:8, right:16, left:16, bottom:8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="date" tick={{ fontSize:12 }} tickLine={false} />
              <YAxis yAxisId="rent" orientation="left"  tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`} tick={{ fontSize:12 }} tickLine={false} axisLine={false} />
              <YAxis yAxisId="home" orientation="right" tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`} tick={{ fontSize:12 }} tickLine={false} axisLine={false} />
              <Tooltip formatter={(v, n) => [`$${v.toLocaleString()}`, n]} contentStyle={{ fontSize:13 }} />
              <Legend />
              <Line yAxisId="rent" type="monotone" dataKey="median_rent"       name="Median rent"       stroke="var(--accent)"   strokeWidth={2} dot={false} activeDot={{ r:4 }} />
              <Line yAxisId="home" type="monotone" dataKey="median_home_value" name="Median home value" stroke="var(--accent-2)" strokeWidth={2} dot={false} activeDot={{ r:4 }} />
            </LineChart>
          </ResponsiveContainer>
        </section>
      )}
    </div>
  );
}
