// src/HelmetConfig.js
import React from "react";
import { Helmet } from "react-helmet";

const HelmetConfig = () => {
  const environment = process.env.REACT_APP_ENV;
  const cssurl =
    environment === "LOCAL"
      ? "/static/css/arxivstyle.css"
      : "./static/css/arxivstyle.css";
  // console.log("loading css:",cssurl)

  // const cssurl = "/static/css/arxivstyle.css"
  return (
    <Helmet>
      <title>ArXiv Statistics</title>
      <link rel="stylesheet" href={cssurl} />
    </Helmet>
  );
};

export default HelmetConfig;
