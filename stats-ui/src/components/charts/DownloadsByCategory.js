import { useEffect, useRef, useState } from "react";
import Plotly from "plotly.js-dist";

const DownloadsByCategory = () => {
  const chartRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch("http://127.0.0.1:8080/api/get_data?model=hourly&group_by=category") // Change for production
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok " + response.statusText);
        }
        return response.json();
      })
      .then((data) => {
        const extractArchive = (category) => category.split(".")[0];

        const categories = data.map((d) => d.category);
        const totals = data.map((d) => d.data);
        const archives = categories.map(extractArchive);

        const archiveColors = {
          "astro-ph": "#1f77b4",
          "cond-mat": "#ff7f0e",
          cs: "#2ca02c",
          econ: "#d62728",
          eess: "#9467bd",
          "gr-qc": "#8c564b",
          hep: "#e377c2",
          math: "#7f7f7f",
          nlin: "#bcbd22",
          nucl: "#17becf",
          physics: "#ff6699",
          "q-bio": "#33cc33",
          "q-fin": "#ffcc00",
          "quant-ph": "#0099cc",
          stat: "#9933ff",
        };

        const colors = archives.map((a) => archiveColors[a] || "#cccccc");

        const trace = {
          type: "bar",
          x: categories,
          y: totals,
          text: categories.map(
            (cat, i) =>
              `Archive: ${archives[i]}<br>Category: ${cat}<br>${totals[i]} Downloads`,
          ),
          hoverinfo: "text",
          marker: { color: colors },
        };

        const layout = {
          title: "Total Downloads by Category since March 2023",
          xaxis: { title: "Category", tickangle: -45, automargin: true },
          yaxis: { title: "Downloads" },
          showlegend: false,
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
        <strong>Downloads By Category</strong>
      </div>
      {loading && <div>Fetching data...</div>}
      {error && <div>Failed to fetch data :(</div>}
      <div ref={chartRef} id="chart" />
    </div>
  );
};

export default DownloadsByCategory;
