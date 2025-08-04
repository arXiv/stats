import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import HelmetConfig from "./HelmetConfig";
import StatsHome from "./StatsHome";
import StatsCategory from "./StatsCategory";
import ChartDetail from "./pages/ChartDetail";

function App() {
  return (
    <Router>
      <HelmetConfig />
      <Routes>
        <Route path="/stats" element={<StatsHome />} />
        <Route path="/stats/:category" element={<StatsCategory />} />
        <Route path="/stats/:category/:chart" element={<ChartDetail />} />
        <Route path="*" element={<Navigate to="/stats" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
