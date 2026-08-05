import { useState } from "react";
import "./App.css";

function App() {
  const [language, setLanguage] = useState("english");

  const messages = {
    english: "Welcome to React",
    telugu: "రియాక్ట్కు స్వాగతం",
  };

  return (
    <div className="App">
      <h1>Language Switcher</h1>
      <button onClick={() => setLanguage("english")}>English</button>
      <button onClick={() => setLanguage("telugu")}>Telugu</button>
      <h2>{messages[language]}</h2>
    </div>
  );
}

export default App;
