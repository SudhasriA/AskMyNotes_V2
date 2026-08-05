import { useState } from "react";

function App() {

  const [count, setCount] = useState(0);

  return (

    <div>
      <title>Like Button Application</title>
      <h1>Like Button Application</h1>

      <h2>❤️ Likes:{count}</h2>

      <button
        onClick={() => setCount(count + 1)}
      >
        Like
      </button>

      {/* <button
        onClick={() => setCount(count - 1)}
      >
        Decrease
      </button> */}

      <button
        onClick={() => setCount(0)}
      >
        Reset
      </button>

    </div>

  );
}

export default App;