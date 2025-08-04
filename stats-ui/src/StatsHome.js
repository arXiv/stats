import { useNavigate } from "react-router-dom";

const styles = {
  container: {
    maxWidth: "800px",
    margin: "0 auto",
    padding: "20px",
    fontFamily: "Arial, sans-serif",
  },
  title: {
    color: "#1a1a1a",
    borderBottom: "1px solid #eee",
    paddingBottom: "10px",
  },
  introText: {
    lineHeight: "1.6",
    marginBottom: "30px",
  },
  categorySelection: {
    display: "flex",
    justifyContent: "space-between",
    marginBottom: "40px",
    gap: "20px",
  },
  categoryCard: {
    flex: "1",
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
  categoryTitle: {
    color: "#b31b1b",
    marginTop: "0",
  },
  disclaimer: {
    fontSize: "0.9em",
    color: "#666",
    fontStyle: "italic",
    borderTop: "1px solid #eee",
    paddingTop: "20px",
  },
};

// displays the home page for the statistics section of the arXiv website
// it provides an overview of the available statistics and allows users to navigate to specific categories
function StatsHome() {
  const navigate = useNavigate();

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>arXiv Usage Statistics</h1>
      <p style={styles.introText}>
        arXiv tracks and publishes the following statistical breakdowns: arXiv's
        hourly usage for any given day, monthly submissions or downloads going
        back to the beginning of arXiv, a breakdown of submissions by subject
        area over time, and institutional download rankings.
      </p>

      <div style={styles.categorySelection}>
        <div
          style={styles.categoryCard}
          onClick={() => navigate("/stats/downloads")}
        >
          <h2 style={styles.categoryTitle}>Download Statistics</h2>
          <p>
            View data about paper downloads including hourly rates, monthly
            totals, and institutional rankings.
          </p>
        </div>

        <div
          style={styles.categoryCard}
          onClick={() => navigate("/stats/submissions")}
        >
          <h2 style={styles.categoryTitle}>Submission Statistics</h2>
          <p>
            View data about paper submissions including monthly totals and
            breakdowns by subject area.
          </p>
        </div>
      </div>

      <div style={styles.disclaimer}>
        <p>
          While we have taken considerable effort to extract reliable data for
          all charts there are many factors which affect results. These may
          include our counting methodology, excluding legitimate robot activity,
          and excluding data from the arXiv mirrors, among other factors.
        </p>
        <p>
          For best viewing results view charts on a tablet size or larger
          screen.
        </p>
      </div>
    </div>
  );
}

export default StatsHome;
