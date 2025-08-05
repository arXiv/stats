import { useParams } from "react-router-dom";
import DownloadsByCountry from "../components/charts/DownloadsByCountry";
import MonthlyDownloads from "../components/charts/MonthlyDownloads";
import DownloadsByCategory from "../components/charts/DownloadsByCategory";
import DownloadsByArchive from "../components/charts/DownloadsByArchive";
import HourlyUsage from "../components/charts/HourlyUsageRates";

const chartComponents = {
  hourly: HourlyUsage,
  monthly: MonthlyDownloads,
  "downloads-by-country": DownloadsByCountry,
  "downloads-by-category": DownloadsByCategory,
  "downloads-by-archive": DownloadsByArchive,
};

function ChartDetail() {
  const { chart } = useParams();
  const ChartComponent = chartComponents[chart];

  if (!ChartComponent) {
    return <div>Chart not found</div>;
  }

  return (
    <div>
      <ChartComponent />
    </div>
  );
}

export default ChartDetail;
