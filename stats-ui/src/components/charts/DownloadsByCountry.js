import { useEffect, useRef, useState } from "react";
import Plotly from "plotly.js-dist";

const DownloadsByCountry = () => {
  const chartRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch("http://127.0.0.1:8080/api/get_data?model=hourly&group_by=country") // Update this in production
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((data) => {
        const countries = data.map((d) => d.country);
        const totals = data.map((d) => d.data);

        const trace = {
          type: "choropleth",
          locations: countries,
          locationmode: "country names",
          z: totals,
          text: countries.map(
            (country, i) => `${country}: ${totals[i]} Downloads`,
          ),
          hoverinfo: "text",
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
          colorbar: {
            title: "Downloads",
          },
        };

        const layout = {
          title: "Total Downloads by Country Since March 2023",
          geo: {
            showocean: true,
            oceancolor: "rgb(6,100,115)",
            showframe: false,
            projection: {
              type: "robinson",
            },
          },
        };

        Plotly.react(chartRef.current, [trace], layout, {
          showLink: false,
          responsive: true,
        });
        setLoading(false);
      })
      .catch((error) => {
        console.error("Fetch error:", error);
        setError(true);
        setLoading(false);
      });
  }, []);

  return (
    <div>
      <div style={{ marginBottom: 10, fontFamily: "Arial, sans-serif" }}>
        <strong>Downloads By Country</strong>
      </div>
      {loading && <div>Fetching data...</div>}
      {error && <div>Failed to fetch data :(</div>}

      <div ref={chartRef} id="chart" />
    </div>
  );
};

export default DownloadsByCountry;
