import { deflateSync } from "node:zlib";
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";

function crc32(buf) {
  let crc = 0xffffffff;
  for (let i = 0; i < buf.length; i++) {
    crc ^= buf[i];
    for (let j = 0; j < 8; j++) {
      const mask = -(crc & 1);
      crc = (crc >>> 1) ^ (0xedb88320 & mask);
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function pngChunk(type, data) {
  const typeBuf = Buffer.from(type, "ascii");
  const lenBuf = Buffer.alloc(4);
  lenBuf.writeUInt32BE(data.length, 0);
  const crcBuf = Buffer.alloc(4);
  const crc = crc32(Buffer.concat([typeBuf, data]));
  crcBuf.writeUInt32BE(crc, 0);
  return Buffer.concat([lenBuf, typeBuf, data, crcBuf]);
}

function encodePngRGBA(width, height, rgba) {
  const signature = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 6; // color type RGBA
  ihdr[10] = 0; // compression
  ihdr[11] = 0; // filter
  ihdr[12] = 0; // interlace

  const stride = width * 4;
  const raw = Buffer.alloc((stride + 1) * height);
  for (let y = 0; y < height; y++) {
    raw[y * (stride + 1)] = 0; // no filter
    rgba.copy(raw, y * (stride + 1) + 1, y * stride, y * stride + stride);
  }

  const compressed = deflateSync(raw, { level: 9 });
  return Buffer.concat([
    signature,
    pngChunk("IHDR", ihdr),
    pngChunk("IDAT", compressed),
    pngChunk("IEND", Buffer.alloc(0)),
  ]);
}

function makeCanvas(width, height) {
  const rgba = Buffer.alloc(width * height * 4);
  function idx(x, y) {
    return (y * width + x) * 4;
  }
  function setPixel(x, y, r, g, b, a = 255) {
    if (x < 0 || y < 0 || x >= width || y >= height) return;
    const i = idx(x, y);
    rgba[i] = r;
    rgba[i + 1] = g;
    rgba[i + 2] = b;
    rgba[i + 3] = a;
  }
  function fillRect(x0, y0, w, h, r, g, b, a = 255) {
    const x1 = Math.min(width, Math.max(0, x0 + w));
    const y1 = Math.min(height, Math.max(0, y0 + h));
    for (let y = Math.max(0, y0); y < y1; y++) {
      for (let x = Math.max(0, x0); x < x1; x++) setPixel(x, y, r, g, b, a);
    }
  }
  function fillCircle(cx, cy, radius, r, g, b, a = 255) {
    const r2 = radius * radius;
    const minX = Math.max(0, Math.floor(cx - radius));
    const maxX = Math.min(width - 1, Math.ceil(cx + radius));
    const minY = Math.max(0, Math.floor(cy - radius));
    const maxY = Math.min(height - 1, Math.ceil(cy + radius));
    for (let y = minY; y <= maxY; y++) {
      for (let x = minX; x <= maxX; x++) {
        const dx = x - cx;
        const dy = y - cy;
        if (dx * dx + dy * dy <= r2) setPixel(x, y, r, g, b, a);
      }
    }
  }
  function fillRoundedRect(x, y, w, h, rad, r, g, b, a = 255) {
    fillRect(x + rad, y, w - 2 * rad, h, r, g, b, a);
    fillRect(x, y + rad, rad, h - 2 * rad, r, g, b, a);
    fillRect(x + w - rad, y + rad, rad, h - 2 * rad, r, g, b, a);
    fillCircle(x + rad, y + rad, rad, r, g, b, a);
    fillCircle(x + w - rad - 1, y + rad, rad, r, g, b, a);
    fillCircle(x + rad, y + h - rad - 1, rad, r, g, b, a);
    fillCircle(x + w - rad - 1, y + h - rad - 1, rad, r, g, b, a);
  }
  function fillLine(x0, y0, x1, y1, thickness, r, g, b, a = 255) {
    const dx = x1 - x0;
    const dy = y1 - y0;
    const steps = Math.max(Math.abs(dx), Math.abs(dy));
    for (let s = 0; s <= steps; s++) {
      const t = steps === 0 ? 0 : s / steps;
      const x = Math.round(x0 + dx * t);
      const y = Math.round(y0 + dy * t);
      fillCircle(x, y, thickness, r, g, b, a);
    }
  }
  return { width, height, rgba, setPixel, fillRect, fillCircle, fillRoundedRect, fillLine };
}

function drawIcon(canvas) {
  const { width, height } = canvas;

  const bg = [11, 15, 25];
  canvas.fillRect(0, 0, width, height, ...bg, 255);

  // scale-friendly coordinates based on a 64x64 design
  const sx = width / 64;
  const sy = height / 64;
  const s = Math.min(sx, sy);

  function X(v) {
    return Math.round(v * sx);
  }
  function Y(v) {
    return Math.round(v * sy);
  }
  function R(v) {
    return Math.max(1, Math.round(v * s));
  }

  const bone = [245, 247, 255];
  const skull = [255, 255, 255];
  const ink = [11, 18, 32];
  const cake = [255, 79, 169];
  const frosting = [245, 247, 255];
  const candle = [255, 209, 220];
  const flameTop = [255, 209, 102];
  const flameBottom = [255, 107, 107];

  // Crossbones (two thick diagonals)
  const thick = R(3.6);
  canvas.fillLine(X(14), Y(26), X(50), Y(38), thick, ...bone, 240);
  canvas.fillLine(X(14), Y(38), X(50), Y(26), thick, ...bone, 240);

  // Skull head + jaw
  canvas.fillCircle(X(32), Y(26), R(15), ...skull, 255);
  canvas.fillRoundedRect(X(20), Y(29), X(24), Y(19), R(6), ...skull, 255);

  // Eye sockets
  canvas.fillCircle(X(26.5), Y(27), R(5.2), ...ink, 255);
  canvas.fillCircle(X(37.5), Y(27), R(5.2), ...ink, 255);

  // Nose
  canvas.fillCircle(X(32), Y(34), R(2.2), ...ink, 255);
  canvas.fillCircle(X(30.5), Y(35.8), R(1.8), ...ink, 255);
  canvas.fillCircle(X(33.5), Y(35.8), R(1.8), ...ink, 255);

  // Teeth line
  canvas.fillRect(X(25), Y(40), X(14), R(1.8), ...ink, 230);
  for (const tx of [28, 32, 36]) {
    canvas.fillRect(X(tx), Y(40), R(1.5), Y(6), ...ink, 210);
  }

  // Cake base
  canvas.fillRoundedRect(X(18), Y(45), X(28), Y(14), R(4), ...cake, 255);

  // Frosting stripe
  canvas.fillRoundedRect(X(18), Y(46), X(28), Y(5), R(4), ...frosting, 245);
  // Frost drips
  for (const cx of [22, 28, 34, 40]) {
    canvas.fillCircle(X(cx), Y(51), R(2.1), ...frosting, 245);
  }

  // Candle
  canvas.fillRoundedRect(X(31), Y(37), X(2), Y(9), R(1), ...candle, 255);
  // Flame (simple gradient-ish)
  canvas.fillCircle(X(32), Y(35), R(2.6), ...flameBottom, 255);
  canvas.fillCircle(X(32), Y(33.8), R(2.0), ...flameTop, 255);
}

function writePng(path, width, height) {
  const canvas = makeCanvas(width, height);
  drawIcon(canvas);
  const png = encodePngRGBA(width, height, canvas.rgba);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, png);
}

// OG image: 1200x630 (recommended)
writePng(join(process.cwd(), "frontend/public/og-image.png"), 1200, 630);

// iOS home screen / fallback icon
writePng(join(process.cwd(), "frontend/public/apple-touch-icon.png"), 180, 180);

// PNG favicon fallback (some clients won’t use SVG)
writePng(join(process.cwd(), "frontend/public/favicon-32.png"), 32, 32);

console.log("Wrote share images to frontend/public/");

