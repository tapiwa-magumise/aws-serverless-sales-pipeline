import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

// ---------------------------------------------------------------- timing (30 fps)
// Each scene leaves room for a spoken line; see VOICEOVER.md for the script.
export const SCENES = {
  problem: [0, 240],
  built: [240, 420],
  upload: [420, 660],
  queue: [660, 870],
  validate: [870, 1260],
  store: [1260, 1500],
  duplicate: [1500, 1680],
  query: [1680, 1860],
  failure: [1860, 2130],
  deliver: [2130, 2340],
  close: [2340, 2490],
} as const;
export const TOTAL = 2490;
type Scene = keyof typeof SCENES;

// ---------------------------------------------------------------- style
const INK = "#16191F";
const MUTED = "#545B64";
const NAVY = "#1F3B63";
const BLUE = "#1F4E9C";
const GREEN = "#1D8102";
const RED = "#D13212";
const LINE = "#8D96A3";
const FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif";
const MONO = "Menlo, 'SF Mono', monospace";

const ease = Easing.bezier(0.25, 0.1, 0.25, 1);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const ramp = (f: number, a: number, b: number) => interpolate(f, [a, b], [0, 1], { ...clamp, easing: ease });

// ---------------------------------------------------------------- diagram layout
const A = 205, B = 505, C = 790;
const R0 = 470, R1 = 650, R2 = 830, R3 = 985;
const ICON = 96;

type NodeId = "raw" | "queue" | "dlq" | "lambda" | "alarm" | "curated" | "audit" | "sns" | "athena";
const NODES: Record<NodeId, { x: number; y: number; icon: string; label: string; pos: "below" | "above" | "right"; size?: number }> = {
  raw: { x: A, y: R0, icon: "s3.png", label: "Raw files\n(S3)", pos: "below" },
  queue: { x: B, y: R0, icon: "sqs.png", label: "Queue (SQS)", pos: "above" },
  dlq: { x: C, y: R0, icon: "sqs.png", label: "Dead-letter\nqueue (SQS)", pos: "right" },
  lambda: { x: B, y: R1, icon: "lambda.png", label: "Validate\nevery row\n(Lambda)", pos: "right" },
  alarm: { x: C, y: R1, icon: "cloudwatch.png", label: "Alarm\n(CloudWatch)", pos: "right" },
  curated: { x: A, y: R2, icon: "s3.png", label: "Clean and\nrejected rows\n(S3)", pos: "right" },
  audit: { x: B, y: R2, icon: "dynamodb.png", label: "Audit trail\n(DynamoDB)", pos: "right" },
  sns: { x: C, y: R2, icon: "sns.png", label: "Email alert\n(SNS)", pos: "right" },
  athena: { x: A, y: R3, icon: "athena.png", label: "SQL reports\n(Athena)", pos: "right", size: 76 },
};
const h = ICON / 2;
type Pt = [number, number];
const EDGES: Record<string, { pts: Pt[]; fail?: boolean }> = {
  "raw-queue": { pts: [[A + h, R0], [B - h, R0]] },
  "queue-lambda": { pts: [[B, R0 + h], [B, R1 - h]] },
  "lambda-curated": { pts: [[B - h, R1], [A, R1], [A, R2 - h]] },
  "lambda-audit": { pts: [[B, R1 + h], [B, R2 - h]] },
  "curated-athena": { pts: [[A, R2 + h], [A, R3 - 38]] },
  "queue-dlq": { pts: [[B + h, R0], [C - h, R0]], fail: true },
  "dlq-alarm": { pts: [[C, R0 + h], [C, R1 - h]], fail: true },
  "alarm-sns": { pts: [[C, R1 + h], [C, R2 - h]], fail: true },
};

function along(pts: Pt[], t: number): Pt {
  const segs = pts.slice(1).map((p, i) => Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]));
  let d = segs.reduce((a, b) => a + b, 0) * Math.min(Math.max(t, 0), 1);
  for (let i = 0; i < segs.length; i++) {
    if (d <= segs[i] || i === segs.length - 1) {
      const k = segs[i] ? d / segs[i] : 0;
      return [pts[i][0] + (pts[i + 1][0] - pts[i][0]) * k, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * k];
    }
    d -= segs[i];
  }
  return pts[pts.length - 1];
}

// ---------------------------------------------------------------- scene captions
const CAPTIONS: Record<Scene, { n?: number; title: string; sub: string }> = {
  problem: { title: "The problem", sub: "Branch sales arrive as spreadsheets and are merged by hand." },
  built: { title: "What we built", sub: "A serverless pipeline on AWS, defined entirely in Terraform." },
  upload: { n: 1, title: "A file lands in S3", sub: "Branches upload a weekly sales CSV to the raw bucket." },
  queue: { n: 2, title: "It is queued in SQS", sub: "The queue buffers bursts and retries anything that fails." },
  validate: { n: 3, title: "Lambda checks every row", sub: "Each row is tested against the rules. Every failure gets a reason." },
  store: { n: 4, title: "Results are saved and audited", sub: "Clean rows and rejects go to S3. Each file gets one audit record." },
  duplicate: { n: 4, title: "Duplicates are ignored", sub: "A conditional write means the same file can never count twice." },
  query: { n: 5, title: "Analysts query with SQL", sub: "Athena reads the clean data straight from S3." },
  failure: { n: 6, title: "Failures reach a person", sub: "3 retries, then the dead-letter queue, an alarm and an email." },
  deliver: { title: "How it ships", sub: "GitHub Actions tests, scans and deploys. No stored AWS keys." },
  close: { title: "", sub: "" },
};

function sceneAt(f: number): Scene {
  return (Object.keys(SCENES) as Scene[]).find((s) => f >= SCENES[s][0] && f < SCENES[s][1]) ?? "close";
}

// ---------------------------------------------------------------- drawn icons (no unicode glyphs)
const Tick: React.FC<{ size?: number; color?: string }> = ({ size = 20, color = GREEN }) => (
  <svg width={size} height={size} viewBox="0 0 20 20" fill="none" stroke={color} strokeWidth={2.6} strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 10.5l4 4 8-9" />
  </svg>
);
const Cross: React.FC<{ size?: number; color?: string }> = ({ size = 20, color = RED }) => (
  <svg width={size} height={size} viewBox="0 0 20 20" fill="none" stroke={color} strokeWidth={2.6} strokeLinecap="round">
    <path d="M5 5l10 10M15 5L5 15" />
  </svg>
);
const Flag: React.FC = () => (
  <svg width={22} height={22} viewBox="0 0 22 22" fill="none" stroke="#fff" strokeWidth={2} strokeLinejoin="round">
    <path d="M5 20V3M5 4h11l-2.5 4L16 12H5" />
  </svg>
);

// ---------------------------------------------------------------- building blocks
const Badge: React.FC<{ n: number; size?: number; color?: string }> = ({ n, size = 44, color = INK }) => (
  <div style={{ width: size, height: size, borderRadius: size, background: color, color: "#fff", display: "flex",
    alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: size * 0.5, fontFamily: FONT, flexShrink: 0 }}>{n}</div>
);

const Header: React.FC<{ f: number }> = ({ f }) => {
  const s = sceneAt(f);
  const [a] = SCENES[s];
  const cap = CAPTIONS[s];
  const t = ramp(f, a, a + 14);
  if (s === "close") return null;
  return (
    <div style={{ position: "absolute", left: 60, right: 60, top: 70, opacity: t, transform: `translateY(${(1 - t) * 14}px)` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
        {cap.n ? <Badge n={cap.n} size={52} /> : null}
        <div style={{ fontSize: 54, fontWeight: 700, color: INK, letterSpacing: -0.5 }}>{cap.title}</div>
      </div>
      <div style={{ fontSize: 30, color: MUTED, marginTop: 14, lineHeight: 1.3, maxWidth: 900 }}>{cap.sub}</div>
    </div>
  );
};

const Node: React.FC<{ id: NodeId; f: number; appear: number; glow?: number; tint?: string }> = ({ id, f, appear, glow = 0, tint = BLUE }) => {
  const n = NODES[id];
  const size = n.size ?? ICON;
  const t = ramp(f, appear, appear + 12);
  const lab: React.CSSProperties =
    n.pos === "below" ? { left: n.x - 120, width: 240, top: n.y + size / 2 + 18, textAlign: "center" }
    : n.pos === "above" ? { left: n.x - 120, width: 240, top: n.y - size / 2 - 50, textAlign: "center" }
    : { left: n.x + size / 2 + 20, width: 186, top: n.y - 38, textAlign: "left" };
  return (
    <>
      <div style={{ position: "absolute", left: n.x - size / 2, top: n.y - size / 2, width: size, height: size, opacity: t,
        transform: `scale(${0.85 + 0.15 * t + glow * 0.06})`, borderRadius: 10 }}>
        <div style={{ position: "absolute", inset: -9, border: `3px solid ${tint}`, borderRadius: 14, opacity: glow }} />
        <Img src={staticFile(n.icon)} style={{ width: size, height: size, borderRadius: 8 }} />
      </div>
      <div style={{ position: "absolute", ...lab, opacity: t, fontSize: 21, lineHeight: 1.22, color: INK, fontWeight: 600, whiteSpace: "pre-line" }}>
        {n.label}
      </div>
    </>
  );
};

const Edge: React.FC<{ id: string; f: number; appear: number }> = ({ id, f, appear }) => {
  const e = EDGES[id];
  const t = ramp(f, appear, appear + 15);
  const d = "M" + e.pts.map((p) => p.join(" ")).join(" L");
  const len = e.pts.slice(1).reduce((a, p, i) => a + Math.hypot(p[0] - e.pts[i][0], p[1] - e.pts[i][1]), 0);
  const end = e.pts[e.pts.length - 1], prev = e.pts[e.pts.length - 2];
  const ang = Math.atan2(end[1] - prev[1], end[0] - prev[0]);
  const color = e.fail ? RED : LINE;
  const head = [[0, 0], [-16, -9], [-16, 9]].map(([x, y]) => [end[0] + x * Math.cos(ang) - y * Math.sin(ang), end[1] + x * Math.sin(ang) + y * Math.cos(ang)]);
  return (
    <g opacity={t > 0 ? 1 : 0}>
      <path d={d} fill="none" stroke={color} strokeWidth={4} strokeDasharray={e.fail ? "14 10" : `${len}`}
        strokeDashoffset={e.fail ? 0 : len * (1 - t)} opacity={e.fail ? t : 1} />
      <polygon points={head.map((p) => p.join(",")).join(" ")} fill={color} opacity={t >= 1 ? 1 : 0} />
    </g>
  );
};

const Packet: React.FC<{ edge: string; f: number; start: number; dur?: number; color?: string; label?: string }> = ({ edge, f, start, dur = 24, color = BLUE, label }) => {
  if (f < start || f > start + dur + 6) return null;
  const t = ramp(f, start, start + dur);
  const [x, y] = along(EDGES[edge].pts, t);
  const fade = 1 - ramp(f, start + dur, start + dur + 6);
  return (
    <div style={{ position: "absolute", left: x - 15, top: y - 15, width: 30, height: 30, borderRadius: 30, background: color,
      opacity: fade, display: "flex", alignItems: "center", justifyContent: "center",
      color: "#fff", fontSize: 13, fontWeight: 700 }}>{label}</div>
  );
};

const Panel: React.FC<{ f: number; from: number; to: number; children: React.ReactNode; top?: number }> = ({ f, from, to, children, top = 1075 }) => {
  if (f < from || f >= to) return null;
  const t = ramp(f, from, from + 12) * (1 - ramp(f, to - 10, to));
  return (
    <div style={{ position: "absolute", left: 60, right: 60, top, opacity: t, transform: `translateY(${(1 - t) * 20}px)` }}>{children}</div>
  );
};

const Card: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <div style={{ background: "#FFFFFF", border: "1px solid #D5DBE3", borderRadius: 10, padding: "18px 22px", ...style }}>{children}</div>
);

// ---------------------------------------------------------------- data (from the real test run, 16 Oct 2026)
const ROWS: [string, string, string, string | null][] = [
  ["LON01", "TEA-101", "12", null],
  ["LON02", "COF-204", "8", null],
  ["MAN01", "MUG-310", "5", null],
  ["DUB01", "TEA-101", "9", null],
  ["AMS01", "COF-204", "0", "units must be above zero"],
  ["BER01", "COF-2O4", "4", "sku must look like ABC-123"],
  ["PAR01", "MUG-310", "3", "unknown branch_code"],
  ["LON01", "TEA-101", "12", null],
  ["LON01", "TEA-101", "12", "duplicate of an earlier row"],
  ["MAN01", "KET-402", "2", "revenue is negative"],
];
const RESULTS = [
  ["2026-10-12", "LON01", "12", "59.88", "28.68"],
  ["2026-10-12", "LON02", "8", "71.60", "33.20"],
  ["2026-10-13", "DUB01", "9", "44.91", "21.51"],
  ["2026-10-13", "MAN01", "5", "49.75", "27.25"],
  ["2026-10-15", "LON01", "12", "59.88", "28.68"],
];

// ---------------------------------------------------------------- scenes
const Problem: React.FC<{ f: number }> = ({ f }) => {
  const [a, b] = SCENES.problem;
  if (f >= b) return null;
  const branches = ["LON01", "LON02", "MAN01", "DUB01", "AMS01", "BER01"];
  const merge = ramp(f, a + 90, a + 140);
  const err = ramp(f, a + 150, a + 165);
  const out = 1 - ramp(f, b - 15, b);
  return (
    <AbsoluteFill style={{ opacity: out }}>
      {branches.map((br, i) => {
        const appear = ramp(f, a + 15 + i * 9, a + 30 + i * 9);
        const x0 = 110 + (i % 3) * 300, y0 = 420 + Math.floor(i / 3) * 230;
        const x = x0 + (390 - x0) * merge + i * 6 * merge, y = y0 + (640 - y0) * merge + i * 6 * merge;
        return (
          <div key={br} style={{ position: "absolute", left: x, top: y, width: 250, opacity: appear, transform: `rotate(${(i - 2.5) * 2 * merge}deg)` }}>
            <Card style={{ background: "#fff", boxShadow: "0 6px 18px #0000001a" }}>
              <div style={{ fontFamily: MONO, fontSize: 22, color: GREEN, fontWeight: 700 }}>{br}.xlsx</div>
              {[0, 1, 2].map((k) => <div key={k} style={{ height: 10, background: "#E3E7EE", borderRadius: 4, marginTop: 10, width: `${90 - k * 20}%` }} />)}
            </Card>
          </div>
        );
      })}
      <div style={{ position: "absolute", left: 60, right: 60, top: 980, opacity: err, textAlign: "center" }}>
        <div style={{ color: RED, fontSize: 34, fontWeight: 700 }}>Errors found after the report goes out</div>
        <div style={{ fontSize: 28, color: MUTED, marginTop: 22 }}>No record of which file a number came from.</div>
      </div>
    </AbsoluteFill>
  );
};

const Diagram: React.FC<{ f: number }> = ({ f }) => {
  const [a] = SCENES.built;
  if (f < a) return null;
  const s = sceneAt(f);
  const box = ramp(f, a + 5, a + 40);
  const dim = s === "deliver" || s === "close" ? 0 : 1;
  const app = (k: number) => a + 40 + k * 8;
  const glowAt = (from: number, to: number) => ramp(f, from, from + 8) * (1 - ramp(f, to - 8, to));
  const S_ = SCENES;
  const lambdaFlash = s === "failure" ? Math.max(...[0, 1, 2].map((k) => glowAt(S_.failure[0] + 40 + k * 32, S_.failure[0] + 62 + k * 32))) : 0;
  return (
    <AbsoluteFill style={{ opacity: dim }}>
      {/* AWS Cloud and Region groups */}
      <div style={{ position: "absolute", left: 40, top: 300, width: 1000, height: 740, border: `2.5px solid #232F3E`, opacity: box }}>
        <div style={{ position: "absolute", left: 0, top: 0, background: "#232F3E", color: "#fff", fontSize: 18, fontWeight: 700, padding: "6px 12px" }}>aws</div>
        <div style={{ position: "absolute", left: 70, top: 6, fontSize: 22, fontWeight: 700, color: "#232F3E" }}>AWS Cloud</div>
        <div style={{ position: "absolute", left: 24, top: 56, right: 24, bottom: 24, border: "2.5px dashed #00A4A6" }}>
          <div style={{ position: "absolute", left: 0, top: 0, background: "#00A4A6", width: 40, height: 40, display: "flex", alignItems: "center", justifyContent: "center" }}><Flag /></div>
          <div style={{ position: "absolute", left: 52, top: 8, fontSize: 21, fontWeight: 700, color: "#147EBA" }}>eu-west-2 (London)</div>
        </div>
      </div>
      <svg width={1080} height={1350} style={{ position: "absolute", left: 0, top: 0 }}>
        <Edge id="raw-queue" f={f} appear={app(2)} />
        <Edge id="queue-lambda" f={f} appear={app(3)} />
        <Edge id="lambda-curated" f={f} appear={app(5)} />
        <Edge id="lambda-audit" f={f} appear={app(6)} />
        <Edge id="curated-athena" f={f} appear={app(7)} />
        <Edge id="queue-dlq" f={f} appear={app(9)} />
        <Edge id="dlq-alarm" f={f} appear={app(10)} />
        <Edge id="alarm-sns" f={f} appear={app(11)} />
      </svg>
      <Node id="raw" f={f} appear={app(1)} glow={glowAt(S_.upload[0] + 60, S_.upload[1]) + glowAt(S_.duplicate[0] + 10, S_.duplicate[0] + 50)} />
      <Node id="queue" f={f} appear={app(2)} glow={glowAt(S_.queue[0] + 30, S_.queue[1])} />
      <Node id="lambda" f={f} appear={app(3)} glow={Math.max(glowAt(S_.validate[0] + 25, S_.validate[1]), glowAt(S_.duplicate[0] + 70, S_.duplicate[1]))}
        tint={BLUE} />
      {lambdaFlash ? <Node id="lambda" f={f} appear={app(3)} glow={lambdaFlash} tint={RED} /> : null}
      <Node id="curated" f={f} appear={app(5)} glow={glowAt(S_.store[0] + 25, S_.store[1])} tint={GREEN} />
      <Node id="audit" f={f} appear={app(6)} glow={glowAt(S_.store[0] + 25, S_.store[1]) + glowAt(S_.duplicate[0] + 90, S_.duplicate[1])} />
      <Node id="athena" f={f} appear={app(7)} glow={glowAt(S_.query[0] + 30, S_.query[1])} />
      <Node id="dlq" f={f} appear={app(9)} glow={glowAt(S_.failure[0] + 150, S_.failure[1])} tint={RED} />
      <Node id="alarm" f={f} appear={app(10)} glow={glowAt(S_.failure[0] + 175, S_.failure[1])} tint={RED} />
      <Node id="sns" f={f} appear={app(11)} glow={glowAt(S_.failure[0] + 200, S_.failure[1])} tint={RED} />

      {/* moving data */}
      <Packet edge="raw-queue" f={f} start={S_.queue[0] + 5} />
      <Packet edge="queue-lambda" f={f} start={S_.validate[0] + 2} dur={20} />
      <Packet edge="lambda-curated" f={f} start={S_.store[0] + 5} color={GREEN} label="5" />
      <Packet edge="lambda-curated" f={f} start={S_.store[0] + 14} color={RED} label="5" />
      <Packet edge="lambda-audit" f={f} start={S_.store[0] + 8} />
      <Packet edge="raw-queue" f={f} start={S_.duplicate[0] + 30} />
      <Packet edge="queue-lambda" f={f} start={S_.duplicate[0] + 52} dur={18} />
      <Packet edge="curated-athena" f={f} start={S_.query[0] + 8} color="#8C4FFF" />
      <Packet edge="raw-queue" f={f} start={S_.failure[0] + 8} color={RED} />
      {[0, 1, 2].map((k) => <Packet key={k} edge="queue-lambda" f={f} start={S_.failure[0] + 36 + k * 32} dur={14} color={RED} label={`${k + 1}`} />)}
      <Packet edge="queue-dlq" f={f} start={S_.failure[0] + 135} color={RED} />
      <Packet edge="dlq-alarm" f={f} start={S_.failure[0] + 160} color={RED} />
      <Packet edge="alarm-sns" f={f} start={S_.failure[0] + 185} color={RED} />

      {/* the CSV dropping into the raw bucket */}
      {[[S_.upload[0] + 20, "weekly-sales-w41.csv"], [S_.duplicate[0] + 0, "weekly-sales-w41.csv"], [S_.failure[0] - 30, "corrupt-w42.csv"]].map(([st, name]) => {
        const st_ = st as number;
        if (f < st_ || f > st_ + 60) return null;
        const t = ramp(f, st_, st_ + 30);
        const gone = ramp(f, st_ + 40, st_ + 55);
        return (
          <div key={st_} style={{ position: "absolute", left: A - 110, top: 330 + (R0 - 70 - 330) * t, width: 220, opacity: (1 - gone) * Math.min(1, t * 3),
            transform: `scale(${1 - gone * 0.6})` }}>
            <Card style={{ background: "#fff", padding: "10px 14px", boxShadow: "0 8px 20px #0000002a", textAlign: "center" }}>
              <div style={{ fontFamily: MONO, fontSize: 17, color: (name as string).startsWith("corrupt") ? RED : GREEN, fontWeight: 700 }}>{name as string}</div>
            </Card>
          </div>
        );
      })}

      {/* duplicate bounce */}
      {(() => {
        const st = S_.duplicate[0] + 74;
        if (f < st || f > S_.duplicate[1]) return null;
        const t = spring({ frame: f - st, fps: 30, config: { damping: 12 } });
        return (
          <div style={{ position: "absolute", left: B + 60, top: R1 - 110, transform: `scale(${t}) rotate(-6deg)`, background: RED, color: "#fff",
            fontFamily: MONO, fontSize: 22, fontWeight: 700, padding: "8px 14px", borderRadius: 8 }}>skipped_duplicate</div>
        );
      })()}
    </AbsoluteFill>
  );
};

const ValidatePanel: React.FC<{ f: number }> = ({ f }) => {
  const [a, b] = SCENES.validate;
  return (
    <Panel f={f} from={a + 20} to={b} top={1062}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px 26px" }}>
        {ROWS.map(([br, sku, units, reason], i) => {
          const t = ramp(f, a + 40 + i * 24, a + 52 + i * 24);
          const ok = !reason;
          return (
            <div key={i} style={{ opacity: t, transform: `translateX(${(1 - t) * 20}px)`, display: "flex", gap: 10, alignItems: "baseline",
              fontSize: 19, lineHeight: 1.25 }}>
              <span style={{ width: 20, alignSelf: "center", display: "flex" }}>{ok ? <Tick /> : <Cross />}</span>
              <span style={{ fontFamily: MONO, color: INK }}>{br} {sku.includes("2O") ? <>COF-2<u style={{ color: RED, fontWeight: 700 }}>O</u>4</> : sku} ×{units}</span>
              {reason ? <span style={{ color: RED, fontSize: 16 }}>{reason}</span> : null}
            </div>
          );
        })}
      </div>
    </Panel>
  );
};

const StorePanel: React.FC<{ f: number }> = ({ f }) => {
  const [a, b] = SCENES.store;
  return (
    <Panel f={f} from={a + 40} to={b}>
      <Card style={{ fontFamily: MONO, fontSize: 23, lineHeight: 1.6 }}>
        <div style={{ color: MUTED, fontFamily: FONT, fontSize: 20, fontWeight: 700, marginBottom: 4 }}>Audit record · DynamoDB</div>
        <div>file&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;weekly-sales-w41.csv</div>
        <div>status&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>LOADED_WITH_REJECTS</b></div>
        <div>rows_loaded&nbsp;&nbsp;<b style={{ color: GREEN }}>5</b>&nbsp;&nbsp;&nbsp;rows_rejected&nbsp;&nbsp;<b style={{ color: RED }}>5</b></div>
        <div>processed in 0.4 s</div>
      </Card>
    </Panel>
  );
};

const DuplicatePanel: React.FC<{ f: number }> = ({ f }) => {
  const [a, b] = SCENES.duplicate;
  return (
    <Panel f={f} from={a + 90} to={b}>
      <Card style={{ fontSize: 26, lineHeight: 1.5 }}>
        Same file uploaded twice → <b>skipped</b>. Audit records: <b style={{ fontFamily: MONO }}>1</b>.
        <div style={{ color: MUTED, fontSize: 21, marginTop: 6 }}>Key = file name + content fingerprint (ETag), written only if new.</div>
      </Card>
    </Panel>
  );
};

const QueryPanel: React.FC<{ f: number }> = ({ f }) => {
  const [a, b] = SCENES.query;
  const cols = ["date", "branch", "units", "revenue", "margin"];
  return (
    <Panel f={f} from={a + 30} to={b} top={1060}>
      <Card style={{ padding: "12px 18px" }}>
        <div style={{ fontFamily: MONO, fontSize: 17, color: "#8C4FFF", marginBottom: 6 }}>SELECT date, branch_code, SUM(revenue - cost) AS margin …</div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: MONO, fontSize: 19 }}>
          <thead><tr>{cols.map((c) => <th key={c} style={{ textAlign: "left", color: MUTED, fontWeight: 600, paddingBottom: 3 }}>{c}</th>)}</tr></thead>
          <tbody>
            {RESULTS.map((r, i) => (
              <tr key={i} style={{ opacity: ramp(f, a + 50 + i * 10, a + 58 + i * 10) }}>
                {r.map((c, j) => <td key={j} style={{ padding: "1px 0", color: INK }}>{c}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </Panel>
  );
};

const FailurePanel: React.FC<{ f: number }> = ({ f }) => {
  const [a, b] = SCENES.failure;
  const retries = [0, 1, 2].filter((k) => f >= a + 50 + k * 32).length;
  return (
    <>
      <Panel f={f} from={a + 40} to={a + 200}>
        <Card style={{ fontSize: 28, display: "flex", alignItems: "center", gap: 18 }}>
          <span style={{ color: RED, fontWeight: 700 }}>Processing failed</span>
          <span style={{ fontFamily: MONO, color: INK }}>attempt {Math.max(retries, 1)} of 3</span>
        </Card>
      </Panel>
      <Panel f={f} from={a + 205} to={b}>
        <Card style={{ background: "#fff", boxShadow: "0 10px 30px #00000022" }}>
          <div style={{ fontSize: 18, color: MUTED }}>AWS Notifications · to: operations</div>
          <div style={{ fontSize: 25, fontWeight: 700, color: INK, marginTop: 4 }}>ALARM: "ssp-file-in-dead-letter-queue"</div>
          <div style={{ fontSize: 20, color: MUTED, marginTop: 4 }}>A sales file failed processing 3 times. See the runbook.</div>
        </Card>
      </Panel>
    </>
  );
};

const Deliver: React.FC<{ f: number }> = ({ f }) => {
  const [a, b] = SCENES.deliver;
  if (f < a || f >= b) return null;
  const t = ramp(f, a, a + 15) * (1 - ramp(f, b - 10, b));
  const jobs = [["test", "4 unit tests"], ["checks", "fmt · validate · Checkov"], ["deploy", "plan · apply"]];
  const tok = ramp(f, a + 110, a + 150);
  return (
    <AbsoluteFill style={{ opacity: t }}>
      <div style={{ position: "absolute", left: 80, right: 80, top: 330 }}>
        <Card style={{ background: "#24292F", border: "none", color: "#fff", fontFamily: MONO, fontSize: 24 }}>
          <span style={{ color: "#7EE787" }}>$</span> git push origin main
        </Card>
        <div style={{ marginTop: 30, fontSize: 26, fontWeight: 700, color: INK }}>GitHub Actions</div>
        {jobs.map(([name, what], i) => {
          const done = ramp(f, a + 30 + i * 22, a + 40 + i * 22);
          return (
            <div key={name} style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 16, fontSize: 26 }}>
              <div style={{ width: 40, height: 40, borderRadius: 40, background: done >= 1 ? GREEN : "#D0D7DE", color: "#fff", display: "flex",
                alignItems: "center", justifyContent: "center", transform: `scale(${0.8 + 0.2 * done})` }}>{done >= 1 ? <Tick size={24} color="#fff" /> : null}</div>
              <span style={{ fontFamily: MONO, fontWeight: 700, width: 130 }}>{name}</span>
              <span style={{ color: MUTED }}>{what}</span>
            </div>
          );
        })}
        <div style={{ marginTop: 60, display: "flex", alignItems: "center", justifyContent: "space-between", opacity: ramp(f, a + 95, a + 110) }}>
          <Card style={{ width: 300, textAlign: "center", fontSize: 24, fontWeight: 700 }}>GitHub Actions</Card>
          <div style={{ flex: 1, position: "relative", height: 40 }}>
            <div style={{ position: "absolute", left: 10, right: 10, top: 19, borderTop: "3px dashed #DD344C" }} />
            <div style={{ position: "absolute", left: `${8 + tok * 70}%`, top: 0, background: "#DD344C", color: "#fff", fontSize: 17, fontWeight: 700,
              padding: "8px 12px", borderRadius: 8, fontFamily: MONO }}>OIDC token</div>
          </div>
          <Card style={{ width: 300, textAlign: "center", fontSize: 24, fontWeight: 700 }}>AWS deploy role</Card>
        </div>
        <div style={{ textAlign: "center", marginTop: 26, fontSize: 25, color: MUTED, opacity: ramp(f, a + 150, a + 165) }}>
          Short-lived credentials. Trusted for this repo's IDs only.
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Close: React.FC<{ f: number }> = ({ f }) => {
  const [a] = SCENES.close;
  if (f < a) return null;
  const t = ramp(f, a, a + 18);
  return (
    <AbsoluteFill style={{ opacity: t, alignItems: "center", justifyContent: "center", textAlign: "center", padding: 80 }}>
      <div style={{ fontSize: 64, fontWeight: 700, color: INK, lineHeight: 1.1 }}>Serverless sales<br />data pipeline</div>
      <div style={{ fontSize: 32, color: MUTED, marginTop: 18 }}>On AWS, built with Terraform</div>
      <div style={{ fontSize: 30, color: INK, lineHeight: 1.5, marginTop: 50, maxWidth: 820, opacity: ramp(f, a + 15, a + 30) }}>
        Deployed by GitHub Actions with no stored keys.<br />Runs at $0.
      </div>
      <div style={{ fontSize: 26, color: MUTED, marginTop: 60, opacity: ramp(f, a + 50, a + 65) }}>github.com/tapiwa-magumise/aws-serverless-sales-pipeline</div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- composition
export const Pipeline: React.FC = () => {
  const f = useCurrentFrame();
  useVideoConfig();
  return (
    <AbsoluteFill style={{ background: "#FFFFFF", fontFamily: FONT, color: INK }}>
      <Header f={f} />
      <Problem f={f} />
      <Diagram f={f} />
      <ValidatePanel f={f} />
      <StorePanel f={f} />
      <DuplicatePanel f={f} />
      <QueryPanel f={f} />
      <FailurePanel f={f} />
      <Deliver f={f} />
      <Close f={f} />
    </AbsoluteFill>
  );
};
