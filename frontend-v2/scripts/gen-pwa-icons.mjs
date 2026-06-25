// Generates flat PWA icons with no external deps (hand-rolled PNG via zlib).
// MVP brand mark: a green dot on the dark Atlas background. Replaceable later
// (#106 kraken/leviathan brand pass). Run: node scripts/gen-pwa-icons.mjs
import { deflateSync } from 'node:zlib'
import { writeFileSync } from 'node:fs'

const BG = [0x0b, 0x0e, 0x13, 0xff]   // #0b0e13
const FG = [0x1d, 0x9e, 0x75, 0xff]   // #1D9E75

const crcTable = (() => {
  const t = new Uint32Array(256)
  for (let n = 0; n < 256; n++) {
    let c = n
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
    t[n] = c >>> 0
  }
  return t
})()
function crc32(buf) {
  let c = 0xffffffff
  for (let i = 0; i < buf.length; i++) c = crcTable[(c ^ buf[i]) & 0xff] ^ (c >>> 8)
  return (c ^ 0xffffffff) >>> 0
}
function chunk(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length, 0)
  const typeBuf = Buffer.from(type, 'ascii')
  const body = Buffer.concat([typeBuf, data])
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(body), 0)
  return Buffer.concat([len, body, crc])
}

function makePng(size, { dot = true } = {}) {
  const cx = size / 2, cy = size / 2, r = size * 0.32
  const raw = Buffer.alloc(size * (size * 4 + 1))
  let p = 0
  for (let y = 0; y < size; y++) {
    raw[p++] = 0 // filter: none
    for (let x = 0; x < size; x++) {
      const inDot = dot && (x - cx) ** 2 + (y - cy) ** 2 <= r * r
      const c = inDot ? FG : BG
      raw[p++] = c[0]; raw[p++] = c[1]; raw[p++] = c[2]; raw[p++] = c[3]
    }
  }
  const ihdr = Buffer.alloc(13)
  ihdr.writeUInt32BE(size, 0); ihdr.writeUInt32BE(size, 4)
  ihdr[8] = 8; ihdr[9] = 6; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0
  const sig = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
  return Buffer.concat([
    sig,
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(raw, { level: 9 })),
    chunk('IEND', Buffer.alloc(0)),
  ])
}

const out = new URL('../public/', import.meta.url)
writeFileSync(new URL('icon-192.png', out), makePng(192))
writeFileSync(new URL('icon-512.png', out), makePng(512))
// maskable: same flat fill, the dot sits inside the safe zone
writeFileSync(new URL('icon-maskable-512.png', out), makePng(512))
console.log('wrote icon-192.png, icon-512.png, icon-maskable-512.png')
