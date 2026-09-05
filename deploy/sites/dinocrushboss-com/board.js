(function () {
  const DINOS = [
    "trex",
    "ankylosaurus",
    "parasaurolophus",
    "spinosaurus",
    "carnotaurus",
    "dilophosaurus",
  ];
  const SIZE = 6;
  const boardEl = document.getElementById("crush-board");
  const scoreEl = document.getElementById("score-label");
  const comboEl = document.getElementById("combo-label");
  if (!boardEl) return;

  let cells = [];
  let score = 0;
  let combo = 1;
  let busy = false;

  function pick(exclude) {
    let d;
    do {
      d = DINOS[(Math.random() * DINOS.length) | 0];
    } while (exclude && d === exclude && DINOS.length > 1);
    return d;
  }

  function idx(r, c) {
    return r * SIZE + c;
  }

  function render() {
    boardEl.innerHTML = "";
    cells.forEach((name, i) => {
      const tile = document.createElement("div");
      tile.className = "tile";
      tile.dataset.i = String(i);
      const img = document.createElement("img");
      img.src = "/assets/dinos/" + name + ".png";
      img.alt = name;
      tile.appendChild(img);
      boardEl.appendChild(tile);
    });
  }

  function seed() {
    cells = [];
    for (let r = 0; r < SIZE; r++) {
      for (let c = 0; c < SIZE; c++) {
        let name = pick();
        const left = c >= 2 && cells[idx(r, c - 1)] === name && cells[idx(r, c - 2)] === name;
        const up = r >= 2 && cells[idx(r - 1, c)] === name && cells[idx(r - 2, c)] === name;
        if (left || up) name = pick(name);
        cells.push(name);
      }
    }
    render();
  }

  function tileAt(i) {
    return boardEl.children[i];
  }

  function findMatch() {
    for (let r = 0; r < SIZE; r++) {
      for (let c = 0; c < SIZE - 2; c++) {
        const a = cells[idx(r, c)];
        if (a && a === cells[idx(r, c + 1)] && a === cells[idx(r, c + 2)]) {
          return [idx(r, c), idx(r, c + 1), idx(r, c + 2)];
        }
      }
    }
    for (let c = 0; c < SIZE; c++) {
      for (let r = 0; r < SIZE - 2; r++) {
        const a = cells[idx(r, c)];
        if (a && a === cells[idx(r + 1, c)] && a === cells[idx(r + 2, c)]) {
          return [idx(r, c), idx(r + 1, c), idx(r + 2, c)];
        }
      }
    }
    return null;
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function crush(match) {
    match.forEach((i) => tileAt(i).classList.add("match"));
    comboEl.textContent = "Combo ×" + combo;
    await sleep(420);
    match.forEach((i) => {
      tileAt(i).classList.remove("match");
      tileAt(i).classList.add("crush");
    });
    score += 60 * combo;
    scoreEl.textContent = String(score);
    await sleep(280);
    match.forEach((i) => {
      cells[i] = null;
    });
    for (let c = 0; c < SIZE; c++) {
      const col = [];
      for (let r = SIZE - 1; r >= 0; r--) {
        const v = cells[idx(r, c)];
        if (v) col.push(v);
      }
      while (col.length < SIZE) col.push(pick());
      for (let r = SIZE - 1, k = 0; r >= 0; r--, k++) {
        cells[idx(r, c)] = col[k];
      }
    }
    render();
    Array.from(boardEl.children).forEach((el) => el.classList.add("drop"));
  }

  async function makeSwap() {
    if (busy) return;
    busy = true;
    const r = (Math.random() * SIZE) | 0;
    const c = (Math.random() * (SIZE - 1)) | 0;
    const a = idx(r, c);
    const b = idx(r, c + 1);
    const tmp = cells[a];
    cells[a] = cells[b];
    cells[b] = tmp;
    render();
    tileAt(a).classList.add("match");
    tileAt(b).classList.add("match");
    await sleep(260);
    let match = findMatch();
    if (!match) {
      cells[b] = cells[a];
      cells[a] = tmp;
      const forced = cells[a];
      cells[idx(r, Math.min(c + 2, SIZE - 1))] = forced;
      cells[idx(r, Math.max(c - 1, 0))] = forced;
      render();
      match = findMatch() || [a, b, idx(r, Math.min(c + 2, SIZE - 1))];
    }
    combo = ((combo % 4) + 1);
    await crush(match);
    busy = false;
  }

  seed();
  setInterval(makeSwap, 1800);
})();
