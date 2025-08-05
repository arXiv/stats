import { useState, useEffect } from "react";

const ChartContainer = ({ fetchData, renderChart, onDataLoaded }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const result = await fetchData();
        setData(result);
        setLoading(false);
        if (onDataLoaded) {
          onDataLoaded(result);
        }
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    loadData();

    return () => {
      // Cleanup if needed
    };
  }, [fetchData, onDataLoaded]);

  if (loading)
    return (
      <div>
        <div>Fetching data...</div>
      </div>
    );

  if (error) return <div>Failed to fetch data :(</div>;

  return renderChart(data);
};

export default ChartContainer;
