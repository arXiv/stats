import { useEffect, useRef, useState } from "react";
import Plotly from "plotly.js-dist";

const DownloadsByArchive = () => {
  const chartRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch("http://127.0.0.1:8080/api/get_data?model=hourly&group_by=archive") // Change me for production!
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok " + response.statusText);
        }
        return response.json();
      })
      .then((data) => {
        const archives = data.map((d) => d.archive);
        const totals = data.map((d) => d.data);

        const getColorMap = (archives) => {
          const colors = [
            "#1f77b4",
            "#ff7f0e",
            "#2ca02c",
            "#d62728",
            "#9467bd",
            "#8c564b",
            "#e377c2",
            "#7f7f7f",
            "#bcbd22",
            "#17becf",
          ];
          const archiveSet = [...new Set(archives)];
          const colorMap = {};
          archiveSet.forEach((archive, i) => {
            colorMap[archive] = colors[i % colors.length];
          });
          return colorMap;
        };

        const colorMap = getColorMap(archives);
        const colors = archives.map((archive) => colorMap[archive]);

        const trace = {
          type: "bar",
          x: totals,
          y: archives,
          text: archives.map(
            (archive, i) => `${archive}: ${totals[i]} Downloads`,
          ),
          hoverinfo: "text",
          orientation: "h",
          marker: { color: colors },
        };

        const layout = {
          title: "Total Downloads by Archive since March 2023",
          xaxis: { title: "Downloads" },
          yaxis: { title: "Archive", automargin: true },
        };

        Plotly.newPlot(chartRef.current, [trace], layout, { responsive: true });
        setLoading(false);
      })
      .catch((error) => {
        console.error("There was a problem with the fetch operation:", error);
        setError(true);
        setLoading(false);
      });
  }, []);

  return (
    <div>
      <div style={{ marginBottom: 10, fontFamily: "Arial, sans-serif" }}>
        <strong>Downloads By Archive</strong>
      </div>
      {loading && <div>Fetching data...</div>}
      {error && <div>Failed to fetch data :(</div>}
      <div ref={chartRef} id="chart" />
    </div>
  );
};

export default DownloadsByArchive;
