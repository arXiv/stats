import { useEffect, useRef, useState } from "react";
import Plotly from "plotly.js-dist";

const HourlyUsage = () => {
  const chartRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [noData, setNoData] = useState(false);
  const [timezone, setTimezone] = useState("");

  useEffect(() => {
    const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    setTimezone(userTimezone);

    fetch(
      `http://127.0.0.1:8080/api/get_todays_downloads?model=hourly&timezone=${encodeURIComponent(userTimezone)}`,
    )
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((data) => {
        if (data.length === 0) {
          throw new Error("No data available");
        }

        const hours = data.map((d) => d.hour);
        const totalPrimary = data.map((d) => d.total_primary);

        const trace = {
          x: hours,
          y: totalPrimary,
          type: "bar",
          hovertemplate:
            "<b>Hour: %{x}</b><br>Usage/Downloads: %{y}<extra></extra>",
          marker: {
            color: totalPrimary,
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
            showscale: false,
          },
        };

        const layout = {
          automargin: true,
          title: `Today's Downloads by the Hour (${userTimezone})`,
          xaxis: {
            title: "Hour",
            tickmode: "array",
            tickvals: hours,
            nticks: 12,
          },
          yaxis: {
            title: { text: "Usage", automargin: true },
            ticks: "outside",
            tickformat: ",",
            automargin: true,
          },
          showlegend: false,
        };

        Plotly.newPlot(chartRef.current, [trace], layout, { responsive: true });
        setLoading(false);
      })
      .catch((err) => {
        console.error("Fetch error:", err);
        if (err.message === "No data available") {
          setNoData(true);
        } else {
          setError("Failed to fetch data :(");
        }
        setLoading(false);
      });
  }, []);

  return (
    <div>
      <div style={{ marginBottom: 10, fontFamily: "Arial, sans-serif" }}>
        <strong>Today's Downloads</strong>
      </div>
      {loading && <div>Fetching data...</div>}
      {error && <div>{error}</div>}
      {noData && (
        <div
          style={{
            position: "fixed",
            top: "40%",
            left: "50%",
            transform: "translateX(-50%)",
            fontSize: 20,
            fontFamily: "Arial, sans-serif",
            zIndex: 999,
          }}
        >
          Looks like it's a new day! Come back in an hour when we've picked up
          the data for its first hour.
        </div>
      )}
      {!loading && !error && !noData && (
        <div style={{ marginBottom: 10, fontFamily: "Arial, sans-serif" }}>
          Timezone: <strong>{timezone}</strong>
        </div>
      )}
      <div ref={chartRef} id="chart" />
    </div>
  );
};

export default HourlyUsage;
