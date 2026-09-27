// NYC 311 · When does New York complain?
// p5.js interactive prototype — Assignment 5
//
// Needs p5_data.js loaded first (it defines TYPES, TOTALS, DATA).
//
// The interaction: click a complaint type to swap the heatmap.
// Percentages are per-type, so the shapes stay comparable even
// though volumes differ by an order of magnitude.

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const W = 960;
const H = 660;

const GRID_LEFT = 116;
const GRID_TOP = 258;
const GRID_RIGHT = 36;
const CELL_H = 34;

let cellW;
let selected = "All complaints";
let buttons = [];
let hovered = null;

// colours
const INK = "#1c2026";
const MUTED = "#6e7580";
const FAINT = "#b5aea4";
const PAPER = "#fbfaf8";
const COOL = "#eef1f2";
const WARM = "#c2481f";

function setup() {
  createCanvas(W, H);
  cellW = (W - GRID_LEFT - GRID_RIGHT) / 24;
  textFont("Helvetica, Arial, sans-serif");
  layoutButtons();
  noLoop();
}

// ---------------------------------------------------------------
// buttons
// ---------------------------------------------------------------

function layoutButtons() {
  buttons = [];
  const padX = 13;
  const gap = 8;
  const rowH = 30;
  const top = 168;
  const maxRight = W - 36;

  let x = 36;
  let y = top;

  textSize(13);
  for (const name of TYPES) {
    const w = textWidth(shorten(name)) + padX * 2;
    if (x + w > maxRight) {
      x = 36;
      y += rowH + gap;
    }
    buttons.push({ name: name, x: x, y: y, w: w, h: rowH });
    x += w + gap;
  }
}

function shorten(name) {
  return name.replace("Noise - ", "Noise: ");
}

// ---------------------------------------------------------------
// draw
// ---------------------------------------------------------------

function draw() {
  background(PAPER);
  drawHeader();
  drawButtons();
  drawGrid();
  drawLegend();
  drawReadout();
}

function drawHeader() {
  noStroke();

  fill(WARM);
  textSize(12);
  textStyle(NORMAL);
  textAlign(LEFT, TOP);
  text("NYC 311 · MARCH 2024 · 266,388 REQUESTS", 36, 34);

  fill(INK);
  textSize(30);
  textStyle(BOLD);
  text("New York complains on a schedule", 36, 58);

  fill(MUTED);
  textSize(15);
  textStyle(NORMAL);
 
  text("pick one below and watch the bright block move.", 36, 124);
}

function drawButtons() {
  textSize(13);
  textAlign(CENTER, CENTER);
  for (const b of buttons) {
    const on = b.name === selected;
    const over = inside(mouseX, mouseY, b);

    noStroke();
    if (on) {
      fill(INK);
    } else if (over) {
      fill("#e6e2db");
    } else {
      fill("#f0ece6");
    }
    rect(b.x, b.y, b.w, b.h, 15);

    fill(on ? PAPER : INK);
    text(shorten(b.name), b.x + b.w / 2, b.y + b.h / 2 + 1);
  }
}

function drawGrid() {
  const g = DATA[selected];
  const peak = gridMax(g);

  // hour labels
  noStroke();
  fill(FAINT);
  textSize(11);
  textAlign(CENTER, BOTTOM);
  for (let h = 0; h < 24; h += 3) {
    const label = h === 0 ? "12a" : h === 12 ? "12p" : h < 12 ? h + "a" : h - 12 + "p";
    text(label, GRID_LEFT + h * cellW + cellW / 2, GRID_TOP - 8);
  }

  hovered = null;

  for (let w = 0; w < 7; w++) {
    // weekday label
    noStroke();
    fill(w >= 5 ? INK : MUTED);
    textSize(13);
    textAlign(RIGHT, CENTER);
    text(WEEKDAYS[w], GRID_LEFT - 14, GRID_TOP + w * CELL_H + CELL_H / 2);

    for (let h = 0; h < 24; h++) {
      const v = g[w][h];
      const x = GRID_LEFT + h * cellW;
      const y = GRID_TOP + w * CELL_H;

      const t = peak > 0 ? v / peak : 0;
      // ease so the middle of the range stays readable
      const eased = pow(t, 1.4);

      noStroke();
      fill(lerpColor(color(COOL), color(WARM), eased));
      rect(x + 1, y + 1, cellW - 2, CELL_H - 2, 2);

      if (
        mouseX >= x &&
        mouseX < x + cellW &&
        mouseY >= y &&
        mouseY < y + CELL_H
      ) {
        hovered = { w: w, h: h, v: v, x: x, y: y };
      }
    }
  }

  if (hovered) {
    noFill();
    stroke(INK);
    strokeWeight(2);
    rect(hovered.x + 1, hovered.y + 1, cellW - 2, CELL_H - 2, 2);
    noStroke();
  }
}

function drawLegend() {
  const y = GRID_TOP + 7 * CELL_H + 30;
  const w = 168;
  const h = 10;

  noStroke();
  for (let i = 0; i < w; i++) {
    const eased = pow(i / w, 1.4);
    fill(lerpColor(color(COOL), color(WARM), eased));
    rect(GRID_LEFT + i, y, 1.4, h);
  }

  fill(FAINT);
  textSize(11);
  textAlign(LEFT, TOP);
  text("quiet", GRID_LEFT, y + h + 7);
  textAlign(RIGHT, TOP);
  text("busiest hour for this type", GRID_LEFT + w, y + h + 7);

  fill(MUTED);
  textSize(12);
  textAlign(LEFT, CENTER);
  text(
    "Colour is share of this complaint type's own month, so shapes compare across types.",
    GRID_LEFT + w + 26,
    y + h / 2 + 2
  );
}

function drawReadout() {
  const y = GRID_TOP + 7 * CELL_H + 84;
  const g = DATA[selected];
  const p = peakCell(g);

  noStroke();
  fill(INK);
  textSize(15);
  textStyle(BOLD);
  textAlign(LEFT, TOP);

  if (hovered) {
    const day = fullDay(hovered.w);
    const hr = hourLabel(hovered.h);
    text(day + ", " + hr, 36, y);
    fill(MUTED);
    textStyle(NORMAL);
    textSize(14);
    text(
      hovered.v.toFixed(2) +
        "% of all " +
        selected.toLowerCase() +
        " this month  ·  roughly " +
        round((hovered.v / 100) * TOTALS[selected]).toLocaleString() +
        " requests",
      36,
      y + 24
    );
  } else {
    text(
      selected +
        " peaks " +
        fullDay(p.w) +
        " at " +
        hourLabel(p.h) +
        "  (" +
        p.v.toFixed(2) +
        "%)",
      36,
      y
    );
    fill(MUTED);
    textStyle(NORMAL);
    textSize(14);
    text(
      TOTALS[selected].toLocaleString() +
        " requests in March 2024  ·  hover any cell for detail",
      36,
      y + 24
    );
  }

  fill(FAINT);
  textSize(11);
  textStyle(NORMAL);
}

// ---------------------------------------------------------------
// interaction
// ---------------------------------------------------------------

function mousePressed() {
  for (const b of buttons) {
    if (inside(mouseX, mouseY, b)) {
      selected = b.name;
      redraw();
      return;
    }
  }
}

function mouseMoved() {
  redraw();
}

function keyPressed() {
  const i = TYPES.indexOf(selected);
  if (keyCode === LEFT_ARROW) {
    selected = TYPES[(i - 1 + TYPES.length) % TYPES.length];
    redraw();
  } else if (keyCode === RIGHT_ARROW) {
    selected = TYPES[(i + 1) % TYPES.length];
    redraw();
  }
}

// ---------------------------------------------------------------
// helpers
// ---------------------------------------------------------------

function inside(px, py, b) {
  return px >= b.x && px <= b.x + b.w && py >= b.y && py <= b.y + b.h;
}

function gridMax(g) {
  let m = 0;
  for (let w = 0; w < 7; w++) {
    for (let h = 0; h < 24; h++) {
      if (g[w][h] > m) m = g[w][h];
    }
  }
  return m;
}

function peakCell(g) {
  let best = { w: 0, h: 0, v: -1 };
  for (let w = 0; w < 7; w++) {
    for (let h = 0; h < 24; h++) {
      if (g[w][h] > best.v) best = { w: w, h: h, v: g[w][h] };
    }
  }
  return best;
}

function fullDay(w) {
  return [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
  ][w];
}

function hourLabel(h) {
  if (h === 0) return "midnight";
  if (h === 12) return "noon";
  return h < 12 ? h + "am" : h - 12 + "pm";
}
