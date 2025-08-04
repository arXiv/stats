import React from "react";
import "./Button.css";

function ActionButton({ onClick, text }) {
  return (
    <button className="back-button" onClick={onClick}>
      {text}
    </button>
  );
}

export default ActionButton;
