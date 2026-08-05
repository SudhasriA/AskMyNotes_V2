import { useState } from "react";

function App() {
  const [lang, setLang] = useState("english");

  const messages = {
    english: "Welcome",
    telugu: "స్వాగతం",
  };

  return (
    <div>
      <h2>{messages[lang]}</h2>
      <button onClick={() => setLang("english")}>English</button>
      <button onClick={() => setLang("telugu")}>Telugu</button>
    </div>
  );
}

export default App;
