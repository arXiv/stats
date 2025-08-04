import { useParams, useNavigate } from "react-router-dom";

// some basic styles for the component
const styles = {
  container: {
    maxWidth: "1200px",
    margin: "0 auto",
    padding: "20px",
    fontFamily: "Arial, sans-serif",
  },
  title: {
    color: "#1a1a1a",
    borderBottom: "1px solid #eee",
    paddingBottom: "10px",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(250px, 1fr))",
    gap: "20px",
    margin: "30px 0",
  },
  card: {
    border: "1px solid #ddd",
    borderRadius: "8px",
    padding: "20px",
    cursor: "pointer",
    transition: "all 0.3s ease",
    ":hover": {
      boxShadow: "0 5px 15px rgba(0,0,0,0.1)",
      transform: "translateY(-5px)",
    },
  },
  cardTitle: {
    color: "#b31b1b",
    marginTop: "0",
  },
  backButton: {
    display: "inline-block",
    marginBottom: "20px",
    color: "#b31b1b",
    textDecoration: "none",
    fontWeight: "bold",
    cursor: "pointer",
  },
};

// This component displays a list of charts based on the selected category (downloads or submissions).
// It uses React Router's useParams to get the category from the URL and useNavigate to navigate to different chart pages.
const chartOptions = {
  downloads: [
    {
      id: "hourly",
      title: "Hourly Usage Rates",
      description: "View download rates by hour for any given day",
    },
    {
      id: "monthly",
      title: "Monthly Downloads",
      description: "View total downloads by month over time",
    },
    {
      id: "downloads-by-country",
      title: "Downloads by Country",
      description: "See download statistics by country",
    },
    {
      id: "downloads-by-category",
      title: "Downloads by Category",
      description: "Breakdown of downloads by subject category",
    },
    {
      id: "downloads-by-archive",
      title: "Downloads by Archive",
      description: "Breakdown of downloads by archive",
    },
  ],
  submissions: [
    {
      id: "monthly",
      title: "Monthly Submissions",
      description: "View submission totals by month over time. TBD!",
    },
    {
      id: "subject",
      title: "Submissions by Subject",
      description: "Breakdown of submissions by subject area. TBD!",
    },
  ],
};

// The StatsCategory component renders a list of charts based on the selected category.
// It uses the useParams hook to get the category from the URL and the useNavigate hook to navigate to different chart pages.
function StatsCategory() {
  const { category } = useParams();
  const navigate = useNavigate();
  const charts = chartOptions[category] || [];

  return (
    <div style={styles.container}>
      <div style={styles.backButton} onClick={() => navigate("/stats")}>
        ← Back to Statistics Home
      </div>

      <h1 style={styles.title}>
        {category === "downloads" ? "Download" : "Submission"} Statistics
      </h1>

      <div style={styles.grid}>
        {charts.map((chart) => (
          <div
            key={chart.id}
            style={styles.card}
            onClick={() => navigate(`/stats/${category}/${chart.id}`)}
          >
            <h2 style={styles.cardTitle}>{chart.title}</h2>
            <p>{chart.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default StatsCategory;
