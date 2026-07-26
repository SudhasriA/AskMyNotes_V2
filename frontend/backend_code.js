const readline = require("readline");

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

const lines = [];

rl.on("line", (line) => {
  lines.push(line.trim());
});

rl.on("close", () => {

  // ── Read Input ──
  const size   = Number(lines[0]);
  const nums   = lines[1].split(" ").map(Number);
  const target = Number(lines[2]);

  // ── Two Sum Logic ──
  let result = -1;
  let found  = false;

  for (let i = 0; i < size; i++) {
    for (let j = i + 1; j < size; j++) {

      if (nums[i] + nums[j] === target) {
        result = `${i} ${j}`;
        found  = true;
        break;
      }

    }
    if (found) break;
  }

  // ── Print Output ──
  console.log(result);

});