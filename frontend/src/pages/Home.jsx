import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { api } from "../api";
import { Spinner }      from "../components/Spinner";
import { ErrorMessage } from "../components/ErrorMessage";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl:       "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl:     "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const SORT_OPTIONS = [
  { value: "median_income", label: "Income" },
  { value: "rpp",           label: "Price parity" },
  { value: "name",          label: "Name" },
];

function MapFlyTo({ city }) {
  const map = useMap();
  useEffect(() => { if (city) map.flyTo([city.lat, city.lon], 10, { duration: 1.2 }); }, [city, map]);
  return null;
}

function fmtPrice(n, isRent) {
  if (!n) return "—";
  return n >= 1000 ? `$${(n / 1000).toFixed(0)}k${isRent ? "/mo" : ""}` : `$${n}${isRent ? "/mo" : ""}`;
}

export default function Home() {
  const navigate = useNavigate();
  const [cities,        setCities]        = useState([]);
  const [loading,       setLoading]       = useState(true);
  const [error,         setError]         = useState(null);
  const [sortBy,        setSortBy]        = useState("median_income");
  const [order,         setOrder]         = useState("desc");
  const [selected,      setSelected]      = useState([]);
  const [activeCity,    setActiveCity]    = useState(null);
  const [showListings,  setShowListings]  = useState(false);
  const [listings,      setListings]      = useState([]);
  const [listingsLoad,  setListingsLoad]  = useState(false);
  const [listingsErr,   setListingsErr]   = useState(null);
  const [propType,      setPropType]      = useState("residential");
  const [status,        setStatus]        = useState("For Rent");

  useEffect(() => {
    setLoading(true);
    api.cities.list(sortBy, order)
      .then((data) => { setCities(data); if (data.length > 0 && !activeCity) setActiveCity(data[0]); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [sortBy, order]);

  useEffect(() => {
    if (!showListings || !activeCity) return;
    setListingsLoad(true); setListingsErr(null);
    api.listings.get(activeCity.metro_fips, propType, status)
      .then((d) => setListings(d.listings || []))
      .catch((e) => setListingsErr(e.message))
      .finally(() => setListingsLoad(false));
  }, [showListings, activeCity, propType, status]);

  function toggleSelect(city) {
    setActiveCity(city);
    setSelected((prev) =>
      prev.find((c) => c.metro_fips === city.metro_fips)
        ? prev.filter((c) => c.metro_fips !== city.metro_fips)
        : prev.length < 4 ? [...prev, city] : prev
    );
  }

  function openListings(city) { setActiveCity(city); setShowListings(true); }

  if (loading) return <Spinner />;
  if (error)   return <ErrorMessage message={error} />;

  return (
    <div className="app-layout">
      <div className="map-pane">
        <MapContainer center={[39.5, -98.35]} zoom={4} style={{ width:"100%", height:"100%" }} zoomControl={false}>
          <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" attribution='&copy; <a href="https://carto.com/">CARTO</a>' />
          {activeCity && <MapFlyTo city={activeCity} />}
          {cities.map((city) => (
            <Marker key={city.metro_fips} position={[city.lat, city.lon]} eventHandlers={{ click: () => setActiveCity(city) }}>
              <Popup className="map-popup">
                <strong>{city.name}</strong>
                <div className="popup-metrics">
                  <span>Income: {city.median_income ? `$${city.median_income.toLocaleString()}` : "—"}</span>
                  <span>RPP: {city.rpp ?? "—"}</span>
                </div>
                <div className="popup-actions">
                  <button className="popup-btn" onClick={() => navigate(`/cities/${city.metro_fips}`)}>View profile →</button>
                  <button className="popup-btn secondary" onClick={() => openListings(city)}>View listings →</button>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      <div className="side-panel">
        {showListings ? (
          <>
            <div className="panel-header">
              <div className="panel-header-row">
                <button className="back-btn inline" onClick={() => setShowListings(false)}>← Back</button>
                <h1>{activeCity?.name}</h1>
              </div>
              <p className="panel-subtitle">Property listings</p>
            </div>
            <div className="listings-controls">
              <div className="toggle-row">
                <button className={`toggle-btn${propType === "residential" ? " active" : ""}`} onClick={() => setPropType("residential")}>Homes</button>
                <button className={`toggle-btn${propType === "commercial"  ? " active" : ""}`} onClick={() => setPropType("commercial")}>Commercial</button>
              </div>
              <div className="toggle-row">
                <button className={`toggle-btn${status === "For Rent" ? " active" : ""}`} onClick={() => setStatus("For Rent")}>For Rent</button>
                <button className={`toggle-btn${status === "For Sale" ? " active" : ""}`} onClick={() => setStatus("For Sale")}>For Sale</button>
              </div>
            </div>
            <div className="listings-list">
              {listingsLoad && <div className="listings-loading"><Spinner /></div>}
              {listingsErr  && <ErrorMessage message={listingsErr} />}
              {!listingsLoad && !listingsErr && listings.length === 0 && <p className="no-listings">No listings found.</p>}
              {!listingsLoad && listings.map((l, i) => (
                <div key={l.id || i} className="listing-card">
                  <div className="listing-price">{fmtPrice(l.price, status === "For Rent")}</div>
                  <div className="listing-address">{l.address}</div>
                  <div className="listing-details">
                    {l.bedrooms      && <span>{l.bedrooms} bd</span>}
                    {l.bathrooms     && <span>{l.bathrooms} ba</span>}
                    {l.sqft          && <span>{l.sqft.toLocaleString()} sqft</span>}
                    {l.property_type && <span>{l.property_type}</span>}
                  </div>
                  {l.days_on_market && <div className="listing-dom">{l.days_on_market} days on market</div>}
                  {l.url && <a className="listing-link" href={l.url} target="_blank" rel="noopener noreferrer">View listing →</a>}
                </div>
              ))}
            </div>
          </>
        ) : (
          <>
            <div className="panel-header">
              <h1>LiveIndex</h1>
              <p className="panel-subtitle">US cost of living — updated weekly</p>
            </div>
            {activeCity && (
              <div className="active-city-card">
                <div className="active-city-name">{activeCity.name}</div>
                <div className="active-city-metrics">
                  <div className="acm-item"><span className="acm-label">Median income</span><span className="acm-value">{activeCity.median_income ? `$${activeCity.median_income.toLocaleString()}` : "—"}</span></div>
                  <div className="acm-item"><span className="acm-label">Price parity</span><span className="acm-value">{activeCity.rpp ?? "—"}</span></div>
                  {activeCity.walk_score != null && <div className="acm-item"><span className="acm-label">Walk score</span><span className="acm-value">{activeCity.walk_score}</span></div>}
                </div>
                <div className="active-city-actions">
                  <button className="btn-primary"   onClick={() => navigate(`/cities/${activeCity.metro_fips}`)}>Full profile →</button>
                  <button className="btn-secondary"  onClick={() => openListings(activeCity)}>Listings →</button>
                  <button className={`btn-secondary${selected.find((c) => c.metro_fips === activeCity.metro_fips) ? " active" : ""}`} onClick={() => toggleSelect(activeCity)}>
                    {selected.find((c) => c.metro_fips === activeCity.metro_fips) ? "✓ Selected" : "+ Compare"}
                  </button>
                </div>
              </div>
            )}
            <div className="panel-section-label">
              Sort cities
            </div>
            <div className="sort-controls">
              {SORT_OPTIONS.map((opt) => (
                <button key={opt.value} className={`sort-btn${sortBy === opt.value ? " active" : ""}`}
                  onClick={() => { if (sortBy === opt.value) setOrder((o) => o === "desc" ? "asc" : "desc"); else { setSortBy(opt.value); setOrder("desc"); } }}>
                  {opt.label}{sortBy === opt.value && <span>{order === "desc" ? " ↓" : " ↑"}</span>}
                </button>
              ))}
            </div>
            <div className="panel-section-label">
              All cities
              {selected.length >= 2 && (
                <button className="compare-trigger" onClick={() => navigate(`/compare?ids=${selected.map((c) => c.metro_fips).join(",")}`)}>
                  Compare {selected.length} →
                </button>
              )}
            </div>
            {selected.length === 1 && <p className="hint">Select one more to compare</p>}
            <div className="city-list">
              {cities.map((city) => {
                const isActive   = activeCity?.metro_fips === city.metro_fips;
                const isSelected = selected.find((c) => c.metro_fips === city.metro_fips);
                return (
                  <div key={city.metro_fips} className={`city-row${isActive ? " active" : ""}${isSelected ? " selected" : ""}`} onClick={() => setActiveCity(city)}>
                    <div className="city-row-left">
                      <span className="city-row-name">{city.name}</span>
                      <span className="city-row-income">{city.median_income ? `$${city.median_income.toLocaleString()}` : "—"}</span>
                    </div>
                    <div className="city-row-right">
                      <button className="listings-btn" onClick={(e) => { e.stopPropagation(); openListings(city); }}>Listings</button>
                      <button className={`select-btn${isSelected ? " on" : ""}`} onClick={(e) => { e.stopPropagation(); toggleSelect(city); }}>
                        {isSelected ? "✓" : "+"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
