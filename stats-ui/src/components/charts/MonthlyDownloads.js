import { useEffect, useRef, useState } from "react";
import Plotly from "plotly.js-dist";

const MonthlyDownloads = () => {
  const chartRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(
      `http://127.0.0.1:8080/api/get_global_sum?model=hourly&time_group=month`,
    )
      .then((response) => {
        if (!response.ok) throw new Error("Network response was not ok");
        return response.json();
      })
      .then((data) => {
        const formatISOToMonthYear = (isoString) => {
          const date = new Date(isoString);
          const options = { year: "numeric", month: "long" };
          return date.toLocaleDateString("en-US", options);
        };

        const formattedDates = data.map((d) =>
          formatISOToMonthYear(d.time_group),
        );
        const totalSums = data.map((d) => d.total_sum);

        const trace = {
          x: formattedDates,
          y: totalSums,
          type: "bar",
          hovertemplate:
            "<b>Month: %{x}</b><br>Total Downloads: %{y:,}<extra></extra>",
          marker: {
            color: totalSums,
            colorscale: [
              [0, "#FFD700"],
              [0.125, "#FFC300"],
              [0.25, "#FFB700"],
              [0.375, "#FFAD00"],
              [0.5, "#FFA000"],
              [0.625, "#FF9900"],
              [0.75, "#FF8C00"],
              [0.875, "#FF8400"],
              [1, "#FF7900"],
            ],
            showscale: true,
          },
        };

        const layout = {
          automargin: true,
          title: "Monthly Downloads",
          xaxis: {
            title: "Month",
            tickmode: "auto",
            nticks: 8,
            tickvals: formattedDates,
            rangeslider: { visible: true },
            type: "category",
          },
          yaxis: {
            title: { text: "Total Downloads", automargin: true },
            ticks: "outside",
            tickformat: ",",
            automargin: true,
          },
          showlegend: false,
        };

        Plotly.newPlot(chartRef.current, [trace], layout, { responsive: true });
        setLoading(false);
        console.log("Plotly chart rendered successfully");
      })
      .catch((err) => {
        console.error("Fetch error:", err);
        setError(true);
        setLoading(false);
      });
  }, []);

  return (
    <div>
      <div style={{ marginBottom: 10, fontFamily: "Arial, sans-serif" }}>
        <strong>Downloads By Month</strong>
      </div>
      {loading && <div>Fetching data...</div>}
      {error && <div>Failed to fetch data :(</div>}
      <div ref={chartRef} id="chart" />
    </div>
  );
};

export default MonthlyDownloads;
