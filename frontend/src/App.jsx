import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Nav }  from "./components/Nav";
import Home     from "./pages/Home";
import City     from "./pages/City";
import Compare  from "./pages/Compare";
import "./styles.css";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/cities/:fips" element={<div className="page-layout"><Nav /><div className="main"><City /></div></div>} />
        <Route path="/compare"      element={<div className="page-layout"><Nav /><div className="main"><Compare /></div></div>} />
      </Routes>
    </BrowserRouter>
  );
}
